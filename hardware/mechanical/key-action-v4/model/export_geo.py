"""geometry.json writer for Toccata v4 W1+ round 4 (called by run_all.py).  Every number is taken from the model
(P, solved geometry g, results R) - drawings and DESIGN.md cite the ids of `dims`."""
import json, math, os, re
from decimal import Decimal, ROUND_HALF_UP
import model_v4 as m


def hu(v, n):
    """THE rounding rule of every generated number (r4.4 doc: geometry.json dims, DESIGN.md tables): half away from zero
    at n decimals, with Decimal, on the value first rounded at 6 decimals (strips binary noise: 0.955 -> 0.96, 13.525 -> 13.53,
    -0.955 -> -0.96; '%.2f' gives 0.95 / 13.52 from the binary value).  The drawings use the same rule (r3 drafter issue)."""
    d6 = Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-6), rounding=ROUND_HALF_UP)   # strip binary noise first
    return float(d6.quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


_PSPEC = re.compile(r"%(?:\(([^)]*)\))?([-+ 0#]*)(\*|\d+)?(?:\.(\*|\d*))?[hlL]?([diouxXeEfFgGcrsa%])")


def _hr(v, n):
    if isinstance(v, bool) or not isinstance(v, (float, int)) and not hasattr(v, "item"):
        return v
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, int) or not math.isfinite(v):
        return v
    return hu(v, n)


def _den(o):
    """r4.4 doc retry 2: floats printed by %s / %r (bare or inside lists / tuples / dicts) lose their binary noise: hu(v, 6)
    (6.319999999999999 -> 6.32).  Everything else is returned unchanged."""
    if isinstance(o, bool):
        return o
    if hasattr(o, "item") and not isinstance(o, (list, tuple, dict)):
        try:
            o = o.item()
        except (TypeError, ValueError):
            return o
    if isinstance(o, float):
        return hu(o, 6) if math.isfinite(o) else o
    if isinstance(o, list):
        return [_den(x) for x in o]
    if isinstance(o, tuple):
        return tuple(_den(x) for x in o)
    if isinstance(o, dict):
        return {k: _den(x) for k, x in o.items()}
    return o


def pf(fmt, args):
    """fmt % args with every %f / %F float first rounded by hu at the shown precision (r4.4 doc: the one rounding helper;
    every '<literal>' % args of export_geo.py and make_design_md.py goes through here).  r4.4 doc retry 2: a float given to
    %s / %r (bare or inside a list / tuple / dict) is first cut to 6 decimals by hu (no binary noise in the text)."""
    specs = [s_ for s_ in _PSPEC.finditer(fmt) if s_.group(5) != "%"]
    if isinstance(args, dict) and any(s_.group(1) is not None for s_ in specs):
        a2 = dict(args)
        for s_ in specs:
            if s_.group(5) in "fF" and s_.group(1) is not None and s_.group(4) != "*":
                a2[s_.group(1)] = _hr(a2[s_.group(1)], 6 if s_.group(4) is None else int(s_.group(4) or 0))
            elif s_.group(5) in "sr" and s_.group(1) is not None:
                a2[s_.group(1)] = _den(a2[s_.group(1)])
        return fmt % a2
    single = not isinstance(args, tuple)
    seq = [args] if single else list(args)
    i = 0
    for s_ in specs:
        if s_.group(3) == "*":
            i += 1
        if s_.group(4) == "*":
            p_ = seq[i] if i < len(seq) else 6
            i += 1
        else:
            p_ = 6 if s_.group(4) is None else int(s_.group(4) or 0)
        if i < len(seq) and s_.group(5) in "fF":
            seq[i] = _hr(seq[i], p_)
        elif i < len(seq) and s_.group(5) in "sr":
            seq[i] = _den(seq[i])
        i += 1
    return fmt % (seq[0] if single else tuple(seq))


def rr(v, n=3):
    if isinstance(v, (list, tuple)):
        return [rr(x, n) for x in v]
    if isinstance(v, dict):
        return {k: rr(x, n) for k, x in v.items()}
    if isinstance(v, float):
        return hu(v, n)
    if hasattr(v, "item"):
        return rr(v.item(), n)
    return v


def _end_sb_txt(P, R, side):
    """r4.4 (circuit cross-check 4): the end part's sensor board, its support, rear-rib gap, lead lane and rear-wall notch."""
    q = R["c44"]["ends"][side]
    nm = "EL" if side == "left" else "ER"
    return (pf("%s 기판 x%.1f~%.1f(센서 바 안), 받침 기둥 x%.1f~%.1f + 앞·뒤 리브 x%.1f~%.1f(z%.1f까지), 뒤 리브 틈 x%.0f~%.0f(리드 패드 x%.2f~%.2f ±0.9: %.2f / %.2f, 아랫면 선이 리브 띠에 드는 곳 %.2f / %.2f); "
            "리드 %d심 %.2f(x%s~%s, 패드 줄에서 기판 뒤끝 + %.1f = y%.2f까지 모음)가 레일 밑 차선 x%s~%s z%.0f~%.0f(폭 %.2f = 리드 + 양옆 %.1f)와 뒷벽 홈 z%.0f~%.0f(같은 x)로 뒤 통로의 %s까지; "
            "리드 길 ↔ 바닥 부품 최소 %.2f%s%s", (nm, q["board"][0], q["board"][1], P["sb_post"][0], P["sb_post"][1], q["rib_x"][0], q["rib_x"][1], P["sb_board"][4], q["gap"][0], q["gap"][1], q["pads"][0], q["pads"][1],
               q["pad_margins"][0], q["pad_margins"][1], q["wire_margins"][0], q["wire_margins"][1], q["cores"], q["lead_w"], m.fh(q["lead"][0]), m.fh(q["lead"][1]), P["lead_fan"], q["fan_y"],
               m.fh(q["lane"][0]), m.fh(q["lane"][1]), q["lane_z"][0], q["lane_z"][1], q["lane_w"], P["lead_margin"], q["notch_z"][0], q["notch_z"][1], "X401" if side == "left" else "X411",
               q["path_min"][0], "(레일·뒷벽 = 차선 여유)" if q["path_min"][1].startswith(("balance rail", "rear wall")) else pf("(%s)", q["path_min"][1]),
               (pf("; A#0 흑 탭 받침(x22.93~30.93, y79~93)을 왼쪽으로 %.2f 비껴 감", q["tab_gap"])) if q["tab_gap"] is not None else
               (pf("; C8 밸런스 핀 밑 레일 %.1f (모듈 E·F 핀과 같음)", q["pins_over_lane"][0][2])) if q["pins_over_lane"] else "")))


def _tools_geo():
    try:
        return json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "tools_geometry.json")))
    except Exception:
        return dict(dummy_lever=dict(per_colour=dict(white=dict(per8=float("nan")), black=dict(per8=float("nan")))))


_TG = _tools_geo()


def dims_table(P, g, R, ep):
    keys, lay, caps = g["keys"], g["lay"], g["caps"]
    Aw, Ab = g["Aw"], g["Ab"]
    H = R["heights"]
    D = []

    def d(i, item, value, unit, ref, note=""):
        D.append(dict(id=i, group=i[0], item=item, value=rr(value, 3) if isinstance(value, float) else value, unit=unit, ref=ref, note=note))
    # ------------------------------------------------------------------ P plan
    d("P01", "옥타브 모듈 폭", P["module_w"], "mm", "x=0 C 왼쪽 명목 경계 → 164.5", "v3 P01 유지")
    d("P02", "백건 피치", P["white_pitch"], "mm", "백건 경계 x=0/23.5/…/164.5", "v3 유지")
    d("P03", "백건 헤드 폭", hu(23.5 - P["head_gap"], 2), "mm", "y0~50", pf("틈 %.2f: 공차 0.3 + 핀 요 ±%.2f + 탭 옆 놀음 ±%.2f 뒤 1.0", (P["head_gap"], P["yaw_pin"], P["tab_play"])))
    d("P04", "백건-백건 틈 (헤드 / E-F·B-C 꼬리)", pf("%.2f / %.2f", (P["head_gap"], P["tail_gap_ww"])), "mm", "헤드 사이 / 꼬리 사이", "")
    d("P05", "흑건 밑폭 / 윗면 폭", pf("%.1f / %.1f", (P["black_w"], P["black_top_w"])), "mm", "흑건 슬롯 13.708 가운데", "")
    d("P07", "흑건-백건 꼬리 틈", hu((164.5 / 12 - P["black_w"]) / 2, 3), "mm", "흑건 옆면 ~ 이웃 백건 꼬리", "v3 1.354")
    for nm in m.ORDER:
        kd = keys[nm]
        bx = m.block_x(P, kd)
        xl = lay["levers"][nm]
        yc = caps["black" if kd["black"] else "white"]
        h2 = lambda v: hu(v, 2)
        if not kd["black"]:
            txt = pf("헤드 x%.2f~%.2f(y0~50), 꼬리 x%.3f~%.3f(y50~146), 밸런스 블록 x%.2f~%.2f(y%.0f~%.0f, 핀 홈 가운데 x%.2f), 빔·캡스턴·레버 중심 x%.3f(빔 x%.2f~%.2f), 가이드 탭 중심 x%.2f, 자석 x%.3f", (
                h2(kd["head"][0]), h2(kd["head"][1]), kd["tail"][0], kd["tail"][1], h2(bx[0]), h2(bx[1]), P["block_y"][0], P["block_y"][1], h2((bx[0] + bx[1]) / 2), xl, h2(xl - 4), h2(xl + 4), h2(kd["guide_c"]), kd["xc"]))
        else:
            txt = pf("밑면 x%.3f~%.3f(y%.1f~146), 윗면 x%.3f~%.3f, 밸런스 블록 x%.2f~%.2f(핀 홈 가운데 x%.2f), 빔·캡스턴·레버 중심 x%.3f(빔 x%.2f~%.2f), 탭(%.1f)·자석 x%.3f, 자석 보스 x%.2f~%.2f(옆벽과 붙음)", (
                kd["head"][0], kd["head"][1], P["y_black_front"], kd["top"][0], kd["top"][1], h2(bx[0]), h2(bx[1]), h2((bx[0] + bx[1]) / 2), xl, h2(xl - 4), h2(xl + 4), P["tab_w_b"], kd["xc"],
                h2(kd["xc"] - (P["black_w"] / 2 - P["wall"])), h2(kd["xc"] + (P["black_w"] / 2 - P["wall"]))))
        rl_ = P.get("tail_relief", {}).get(nm)
        txt += pf("; r4.4 고침 2·2b: 빔·얇은 꼬리 밑면 y%.1f~%.1f을 %.2f 올림 (최악 재료까지의 복귀 넘침에서 제어 기판 부품 구역 z20과 1.3)", rl_) if rl_ else ""
        d("K" + nm, pf("%s 건반 평면 x", nm), xl, "mm", "레버 중심 x", txt + pf("; 캡스턴 y%.2f; 레버 허브 칼라 왼/오 %.2f/%.2f", ((yc,) + g["collars"][nm])))
    d("P10", "레버 중심 오프셋 최대", pf("%.2f (실제 꼬리 중심 기준) / %.2f (v3 센서 중심 기준)", (R["layout"]["max_offset_tail"], lay["max_offset"])), "mm", "레버 중심 − 건반 꼬리 중심", "빔·블록이 레버를 따라감, 꼬리 안 (r3 P10은 v3 중심 기준이었음)")
    d("P11", "레버(캐리어) 폭", P["lever_w"], "mm", pf("레버 중심 ±%.1f", (P["lever_w"] / 2)), pf("강철 9 + 접착층 %.2f×2 + 옆벽 %.1f×2 (r4.4 고침 2b: 주머니 %.1f; 앞·뒷벽 %.1f), 단면은 백·흑 공통; 허브 칼라 길이가 위치마다 달라(P14) 캐리어는 위치별(옆벽에 음 이름)", (P["bond_t"], P["carrier_side_wall"], P["lever_w"] - 2 * P["carrier_side_wall"], P["carrier_wall"])))
    d("P12", "핀(지느러미) 5장 x", "; ".join(pf("x%.2f~%.2f", f) for f in lay["fins"]), "mm", pf("끝 %.1f, 안쪽 %.1f, y%.0f~%.0f (y%.0f~%.0f은 양쪽 %.1f 얇은 앞 연장), 윗판 밑까지", (P["fin_end_t"], P["fin_t"], P["fin_main_y0"], P["fin_y"][1], P["fin_y"][0], P["fin_main_y0"], P["fin_ext_inset"])),
      pf("B-C 이음(양 끝)·%s; 레버 봉 스팬 %s; F|F# 핀은 y%.1f~%.1f에서 기판 앞 홈을 지나 내려감(r4.1: 바닥 z5까지; r4.4 고침 2b: 기판 밑 바닥이 뚫려 z%.0f까지, 킬 y%.1f~%.1f z%.0f~%.1f로 밸런스 레일 뒷면에 붙음; r4.5 고침 2: 이 핀만 앞끝 y152 → y%.1f, 바닥부터 윗판까지), r4.3: 그 뒤 y%.1f~209는 뒷벽까지 z%.1f부터 매달림(USB 플러그 위 포함; r4.2는 y196.8부터 얇은 선반 z18.55까지)", ("·".join(a + "-" + m.ORDER[m.ORDER.index(a) + 1] for a in P["fins_after"]), " / ".join(pf("%.1f", s_) for s_ in R["layout"]["spans"]), m.keel_front(P), P["fin_slot_y"][1], P["z_floor"][0], P["fin_keel"][0], m.keel_front(P), P["fin_keel"][1], P["fin_keel"][2], m.keel_front(P), P["fin_slot_y"][1], P["comp_zmax"] + 1.5)))
    G2 = R.get("r42", {}).get("gaps_module", {})
    zs_, bt_ = g["z_seat"], P["pad_bar_t"]
    d("P13", "패드 바 x (핀 칸마다 1개)", "; ".join(pf("x%.2f~%.2f", (a + P["bar_rail"][0] + P["pad_bar_clear"], b - P["bar_rail"][0] - P["pad_bar_clear"])) for a, b in R["layout"]["bays"]), "mm",
      pf("y%.1f~%.1f (뒤끝이 윗판 계단 y%.1f에 닿음); 앞부분 z%.2f~%.2f는 y%.1f까지, 아래 계단 y%.1f부터 z%.2f~%.2f (계단 y%.1f~%.1f는 두께 3.0)", (P["pad_bar_y"] + (P["plate_step_y"], zs_, zs_ + bt_, g["y_bar_joggle"], g["y_bar_joggle"] - bt_, zs_ - bt_, zs_, g["y_bar_joggle"] - bt_, g["y_bar_joggle"]))),
      pf("r4.2: 윗 계단이 윗판 홈 끝(y%.1f)보다 %.1f 앞 (r4.1은 y169.5까지라 윗판과 1.5×1.5 겹침). 양쪽 L 레일 = 웹 폭 %.1f(y%.0f~%.1f, 윗판 밑에서 z%.2f까지; 홈 구간 y%.0f~%.0f은 홈 천장 z%.2f부터) + 립 %.1f×%.1f(z%.2f~%.2f, y%.1f~%.1f; 바 가장자리 밑 %.1f 겹침, 바 밑면과 %.1f 띄움). "
      "바 가장자리마다 출력 잎 혀 %.1f×%.1f×%.0f(y%.0f~%.0f, 뿌리는 뒤, 앞 끝 돌기 %.1f가 립 위에 얹힘; 주위 %.1f 틈으로 잘림) %.1f 눌림 = 잎마다 %.2f N, 바를 윗판 자리에 밀어 올림 (상시 굽힘 %.1f MPa); 앞으로 밀어 뺌 (%.1f mm부터 윗판에 밀어 올림)", (g["y_bar_step"], P["bar_joggle_clear"], P["bar_rail"][0], P["rail_y0"], P["pad_bar_y"][1], zs_ - P["bar_rail"][1], P["rail_y0"], g["y_bar_step"], zs_ + bt_,
         P["rail_lip"], P["rail_lip_t"], zs_ - P["bar_rail"][1], zs_ - bt_ - P["bar_leaf_gap"], P["rail_lip_y0"], P["pad_bar_y"][1], P["rail_lip"] - P["pad_bar_clear"], P["bar_leaf_gap"],
         P["bar_leaf"][0], P["bar_leaf"][1], P["bar_leaf"][2], P["bar_leaf_y"][0], P["bar_leaf_y"][1], P["bar_leaf_bump"], P["bar_leaf_slot"], P["bar_leaf"][3], G2.get("leaf_F", 0.0),
         G2.get("leaf_sigma", 0.0), P["bar_raise_pull"])) + pf("; r4.4: 웹 앞 아래 모서리(y%.1f, z%.2f)를 %.1f×45° 모따기 (칸 가장자리 캐리어 옆벽이 ff에서 지나감)", (P["rail_y0"], zs_ - P["bar_rail"][1], P["rail_front_chamfer"])))
    d("P14", "레버 허브 칼라 (r3 C-링 대신)", "; ".join(pf("%s %.2f/%.2f", ((n,) + g["collars"][n])) for n in m.ORDER), "mm", "허브 옆면에서 왼/오",
      pf("레버-레버 링(≥ %.2f + 축 놀음 몫)을 양쪽 허브에 반씩에서 %.2f씩 짧게, 단 r4.4 고침 2: 한 칼라 %.2f 이상(짝 합 %.2f 이상, 짝 사이 빈 틈 0.04 이상) — 칸마다 축 놀음 %s; Ø6; 레버-핀 링은 핀 보스(+%.2f); 레버가 제 무게로 자유롭게 돌지 않으면 칼라 면을 사포질",
         (P["ring_min"], P["collar_short"], P["collar_min"], 2 * P["collar_min"], " / ".join(pf("%.2f", q_) for q_ in R.get("axial_play", [])), P["boss_extra"])))
    d("P15", "윗판 (r3 브리지 + 앞 받침판)", pf("x0.2~164.3, y%.1f~%.0f", (P["ledge_y0"], P["rear_wall"][1])), "mm", "핀 5장·뒷벽과 한 몸",
      pf("앞 홈(패드 바 앞부분) 밑면 z%.2f (y%.1f~%.1f, 끝은 수직 면), 패드 구간 z%.2f (y%.1f~%.1f), 계단 y%.1f(수직 면, 패드 바 뒤 멈춤) 뒤 z%.2f (두께 최대 %.0f; 레버 봉 위는 스프링 다리 홈 위 1.3); 가림판 걸이 턱 %.1f×%.1f", (g["z_seat"] + P["pad_bar_t"], P["ledge_y0"], g["y_bar_step"], g["z_seat"], g["y_bar_step"], P["plate_step_y"], P["plate_step_y"], H["plate_rear"], P["plate_rear_max"], P["curtain_hook"][0], P["curtain_hook"][1])))
    d("P16", "업스톱 패드", pf("y%.0f~%.0f(면의 y 폭), 레버마다 폭 %.0f (윗 립 사이 7.4); 재단 %.0f × %.1f (면을 따라 잰 길이 백 %.2f / 흑 %.2f)", (P["pad_y"] + (P["pad_w"], P["pad_w"], R["pad_cut_len"], (P["pad_y"][1] - P["pad_y"][0]) / math.cos(math.radians(H["held_b_w"])), (P["pad_y"][1] - P["pad_y"][0]) / math.cos(math.radians(H["held_b_b"]))))),
      "mm", "강철 윗면 위", pf("미세셀 우레탄 %.0fT + 펠트 %.0fT, 면은 1 N 정착 바닥의 강철 윗면과 평행 (면 기울기 %.2f° / %.2f°라 y 12.0 = 면 12.2)", (P["pad_foam"], P["pad_felt"], H["held_b_w"], H["held_b_b"])))
    ew_ = "; ".join(pf("%s %.2f~%.2f", ((nm_,) + tuple(R["end_parts"][sd_]["stat"][nm_]["wedge"]))) for sd_ in ("left", "right") for nm_ in R["end_parts"][sd_]["stat"])
    d("P17", "패드 쐐기 (패드 바에 출력)", pf("백 %.2f~%.2f, 흑 %.2f~%.2f; 끝 부속 %s", (g["wedge_range"]["w"] + g["wedge_range"]["b"] + (ew_,))), "mm", "패드 뒷면 ~ 패드 바 밑면",
      pf("r3 패드 홀더·흑 스페이서 17개를 대신함; r4.2: 끝 부속 건반은 자기 1 N 정착 바닥에 평행한 자기 면(동역학과 같은 면)으로 쐐기를 출력 — 쐐기 뒤끝 ↔ 윗판 계단 %.2f, 쐐기·패드 ↔ 레일 립 %.2f", (G2.get("pad wedge to plate step", (0.0,))[0], G2.get("pad wedge", (0.0,))[0])))
    sg_ = P["spring_groove"]
    SL_ = R.get("r42", {}).get("spring_slot", {})
    SR_ = R.get("r42", {}).get("spring_rest", {})
    NT_ = SL_.get("notch", {})
    IN_ = R.get("r45", {}).get("insert", {})
    CP_ = R.get("spring", {}).get("capture", {})
    KX_ = R.get("assembly", {}).get("keyless_x", {})
    d("P18", "비틀림 보조 스프링 자리", pf("허브 가운데 주머니 Ø%.1f×%.1f (레버 x ±%.1f) + r4.5 고침 2: 짧은 다리 가둠 홈 폭 %.2f (레버 기준 %.2f° 방향, 축에서 %.3f~%.3f 띠, 주머니 안 %.1f에서 허브 벽을 지나 웹 안 막힌 끝까지 — 다리 끝 너머 %.1f), 웹 밑면을 %.2f 깎음; 넣는 슬롯 %.2f° 방향 ±%.2f(다리를 따라); 긴 다리 창 = %.0f° 방향 윗면 +%.1f까지 뒤로 열림; 뒷벽 면의 출력 보스 y%.1f~%.1f × 폭 %.1f(레버 x %+.1f 중심 = 긴 다리 자리, ±%.1f) × z%.0f~윗판 밑, 그 안 세로 홈 y%.1f~%.1f z%.0f~%.0f (폭 %.1f, 깊이 %.1f — 뒷벽 안으로 %.1f, 뒷벽 %.1f 남음; 입구 %.1f×45° 모따기는 홈 x 면의 보스 밑면 z%.0f~%.1f, 보스 밑면에서 열림)", (P["spring_pocket"] + (P["spring_pocket"][1] / 2,
                                P["spring_d"] + P["spring_notch"][0], NT_.get("band_deg", 0.0), NT_.get("nn", (0, 0))[0], NT_.get("nn", (0, 0))[1], NT_.get("ss", (0, 0))[0], P["spring_notch"][2], NT_.get("web_cut_depth", 0.0),
                                NT_.get("slot_deg", 0.0), P["spring_slot"][2], P["spring_window"][0], P["spring_window"][1],
                                P["rear_wall"][0] - P["spring_boss"][2], P["rear_wall"][0], P["spring_boss"][0], P["spring_groove_dx"], P["spring_boss"][0] / 2,
                                P["spring_boss"][1], sg_[0], sg_[0] + sg_[4], sg_[1], sg_[2], sg_[3], sg_[4], sg_[0] + sg_[4] - P["rear_wall"][0], P["rear_wall"][1] - sg_[0] - sg_[4], P["spring_lead_in"], sg_[1], sg_[1] + P["spring_lead_in"]))),
      "mm", "레버마다 1",
      pf("r4.5 고침 2 (검증 major, 코일 뜸): r4.5의 짧은 다리 2.5가 한 면에만 기대면 다리 힘이 코일(ID 5.0)을 Ø4 봉 쪽으로 %.2f 밀어 다리가 떨어지고 스프링이 %.1f° 풀려 쉼 %.2f N·mm(설계 %.2f)가 되며 봉에 %.1f N으로 문질러짐 → 짧은 다리 %.1f를 폭 %.2f 홈에 가둬 끝(바깥 면)과 주머니 가장자리(안쪽 면) 두 점(팔 %.2f)으로 짝 힘 %.2f N을 받음: 코일은 제 다리에 매달려 봉과 틈 %.2f(쉼)·%.2f(손 25°). "
         "넣기: 봉 넣기 전, 짧은 다리 끝부터 홈을 따라 밀면 코일이 넣는 슬롯으로 주머니에 앉음 (짧은 다리 ↔ 홈 면 %.3f; 홈이 0.15 좁게 나와도 지나감). 짧은 다리는 굽히지 않고 코일 접선(레버 기준 %.2f°, y%.2f z%.2f)에서 끝 y%.2f z%.2f까지. "
         "긴 다리 %.1f(축에서 끝까지)는 코일 뒤쪽 접선(y%.2f z%.2f)에서 홈 바닥 끝(y%.2f z%.2f)까지, 레버 %.1f°~%.1f° 내내 창 안 (면까지 최소 %.2f + 선 반지름 + 0.2); "
         "보스 면 y%.1f에는 z%.2f(보스 밑 z%.0f 아래)에서 닿아 홈으로 밑에서 들어감; 긴 다리는 코일 +x 끝(x %+.1f)에서 곧게 홈으로 — 홈·보스를 그 x에 맞춤(코일 축 놀음 %.2f + 레버 놀음 %.2f ≤ 받는 폭 %.2f, 여유 %.2f). b=0이면 %.1f° 감김; 건반 빠진 레버(-31.3°)에서 풀린 다리 끝이 홈 입구 안 %.2f",
         (R.get("spring", {}).get("float", {}).get("r4.5 as built (short leg 2.5 on one face), mu 0.0", {}).get("shift", 0.0), R.get("spring", {}).get("float", {}).get("r4.5 as built (short leg 2.5 on one face), mu 0.0", {}).get("unwind", 0.0),
          R.get("spring", {}).get("float", {}).get("r4.5 as built (short leg 2.5 on one face), mu 0.0", {}).get("T_rest", 0.0), P["spring_T0"], R.get("spring", {}).get("float", {}).get("r4.5 as built (short leg 2.5 on one face), mu 0.0", {}).get("N_bottom", 0.0),
          P["spring_short_leg"], P["spring_d"] + P["spring_notch"][0], CP_.get("arm", 0.0), CP_.get("F_couple_rest", 0.0), CP_.get("gap_rest", 0.0), CP_.get("gap_hand", 0.0),
          IN_.get("short_A", (0.0,))[0], NT_.get("alpha_s", 0.0), NT_.get("Q", (0, 0))[0], NT_.get("Q", (0, 0))[1], NT_.get("T", (0, 0))[0], NT_.get("T", (0, 0))[1],
          P["spring_leg"], SR_.get("long_leg", [(0, 0)])[0][0], SR_.get("long_leg", [(0, 0)])[0][1], SR_.get("tip", (0, 0))[0], SR_.get("tip", (0, 0))[1],
          R.get("r42", {}).get("spring_b_range", (0, 0))[0], R.get("r42", {}).get("spring_b_range", (0, 0))[1], SL_.get("margin", 0.0), sg_[0], SL_.get("leg_z_at_boss_face", 0.0), P["spring_boss"][1],
          P["spring_groove_dx"], KX_.get("coil_axial", 0.0), KX_.get("lever_float", 0.0), KX_.get("catch", 0.0), KX_.get("margin", 0.0), -P["spring_free_deg"], R.get("leg_in_groove_drop", 0.0))))
    su_ = m.usb_slot(P)
    d("P19", "뒤 선반 / 리브", pf("y%.1f~%.1f / 리브 y%.1f~", (P["shelf_y"][0], P["shelf_y"][1], P["rib_y0"])), "mm", "리브 x " + ", ".join(pf("%.1f", x) for x in g["ribs"]),
      pf("두께 2.0, 윗면 z%.3f; r4.3: USB 플러그 위는 앞뒤로 뚫린 홈 x%.2f~%.2f(플러그 ±%.1f; r4.2는 x%.1f~%.1f 두께 %.1f, 밑면 z%.2f가 올라간 플러그 윗면 z%.1f와 %.2f)", (g["z_shelf"], su_[0], su_[1], P["usb_clear"], P["ribs"][5] + 0.6, P["ribs"][6] - 0.6, P["shelf_usb_t"], g["z_shelf"] - P["shelf_usb_t"], P["usb_z"][1], g["z_shelf"] - P["shelf_usb_t"] - P["usb_z"][1])))
    cr = [f for f in m.fixed_prisms(P, g) if f[0] == "balance rail cradle"]
    RP_ = g.get("rail_pocket") or {}
    pk_txt = "; ".join(pf("%s 블록 밑은 y%.1f 뒤를 z%.2f까지 더 낮춘 포켓(핀 줄 y%.1f는 z%.1f 그대로)", (("흑건" if c_ == "black" else "백건"), q_["y"], q_["z"], P["pin_y"], g["z_rail_low"])) for c_, q_ in RP_.items() if q_)
    d("P20", "밸런스 레일", pf("y%.1f~%.1f, 홈 중심 y%.0f; 블록 밑은 윗면 z%.1f로 낮춤, 블록 사이 봉 받침 %d개", (P["rail_front_y"], P["rail_y"][1], P["K"][0], g["z_rail_low"], len(cr))) + ("; r4.4 고침 2: " + pk_txt if pk_txt else ""), "mm", pf("x%.1f~%.1f", P["rail_x"]),
      "받침 x " + ", ".join(pf("%.2f~%.2f", (f[1], f[2])) for f in cr) + pf("; 핀 구멍 앞벽 %.1f, 홈 양 끝 벽 1.0; 리본 차선 x%.1f~%.1f(레일 밑면 z10, r4.3: 16심 리본 %.2f에 양옆 %.2f / %.2f, r4.2 x60~82); "
      "r4.4: 리본은 차선 안에서 SB J201 가운데 x%.2f로 곧게, 레일 뒤(y%.1f)부터 기판 밑 z%.0f~%.0f로 J301까지 — J301 쪽 끝 %.0f mm만 %+.2f 비껴 꽂음(차선 밖)", (P["pin_y"] - P["pin_d"] / 2 - P["rail_front_y"], P["ribbon_x"][0], P["ribbon_x"][1], P["ribbon_cores"] * P["ribbon_pitch"],
         (P["ribbon_xc"] - P["ribbon_cores"] * P["ribbon_pitch"] / 2) - P["ribbon_x"][0], P["ribbon_x"][1] - (P["ribbon_xc"] + P["ribbon_cores"] * P["ribbon_pitch"] / 2),
         P["ribbon_xc"], P["rail_y"][1], P["ribbon_under_z"][0], P["ribbon_under_z"][1], P["ribbon_j301"][1], R["c44"]["ribbon"]["shift"])))
    d("P21", "건반 봉 Ø4 SUS304", pf("x%.2f~%.2f (길이 %.1f ± 0.2)", (P["rod_k_x"][0], P["rod_k_x"][1], P["rod_k_x"][1] - P["rod_k_x"][0])), "mm", pf("홈 끝 벽 x%.1f / %.1f", (P["rail_x"][0] + 1.0, P["rail_x"][1] - 1.0)), "")
    d("P22", "레버 봉 Ø4 SUS304 h9", pf("x%.1f~%.1f (길이 %.1f ± 0.2)", (P["rod_L_x"][0], P["rod_L_x"][1], P["rod_L_x"][1] - P["rod_L_x"][0])), "mm",
      "핀 5장의 출력 보스(Ø3.9 → Ø4.0 드릴) 관통", pf("왼쪽 끝 핀에 출력 마개 %.1f, 오른쪽 끝 핀은 막힌 벽 %.1f; 건반 봉과 같은 4 m 봉; 최대 응력 %.0f MPa < 풀림재 항복 %.0f", (P["rod_L_plug"], P["rod_L_blind"], R["metrics"]["rod_abuse_mpa"], P["rod_L_yield"])))
    fbx = [f for f in lay["fins"] if P["board_x"][0] < 0.5 * (f[0] + f[1]) < P["board_x"][1]][0]
    d("P23", "제어 기판 (v3 만능기판)", pf("x%.2f~%.2f, y%.1f~%.1f, z%.1f~%.1f; r4.1 앞 모서리에서 연 홈 x%.2f~%.2f, y%.1f~%.1f", (P["board_x"] + P["board_y"] + P["board_z"] + (fbx[0] - P["board_slot_clear"], fbx[1] + P["board_slot_clear"], P["board_y"][0], P["board_slot_y1"]))),
      "mm", "v3 P114 외곽 그대로 (스탠드오프는 r4.4 P35)", pf("r4.3: 부품·배선 금지 x%.2f~%.2f, y%.1f~%.1f(핀 면에서 %.1f; r4.1 1.0) — BRD-01 배치는 이미 밖; 핀 발은 y%.1f에서 끝나 홈 끝 y%.1f와 %.1f, RP2040-Zero 앞 모서리 y%.1f와 %.1f. "
      "r4.4: 금지 구역은 만능기판 위 핀·패드·배선에 대한 것이고, 핀 헤더에 선 RP2040-Zero PCB(z%.1f~%.1f)만 x%.2f~%.2f × y%.1f~%.1f에 걸친다(그 안에 핀·패드·배선 없음; 헤더 열 x%.2f / x%.2f; 매달린 핀 밑면 z%.1f과 %.1f). 받침 4곳 P35", (fbx[0] - P["board_slot_keepout"], fbx[1] + P["board_slot_keepout"], P["board_y"][0], P["board_slot_y1"] + P["board_slot_keepout"], P["board_slot_keepout"],
         P["fin_slot_y"][1], P["board_slot_y1"], P["board_slot_y1"] - P["fin_slot_y"][1], P["zero_xy"][2], P["zero_xy"][2] - P["fin_slot_y"][1],
         P["zero_z"][0], P["zero_z"][1], R["c44"]["zero"]["overhang"][0], R["c44"]["zero"]["overhang"][1], R["c44"]["zero"]["overhang"][2], R["c44"]["zero"]["overhang"][3],
         R["c44"]["zero"]["lattice_x"][0], R["c44"]["zero"]["lattice_x"][-1], R["c44"]["zero"]["hung_fin_z"], R["c44"]["zero"]["to_hung_fin"])))
    d("P24", "USB-C 플러그 외곽", pf("x%.2f~%.2f, y%.1f~%.1f, z%.1f~%.1f", (P["usb_x"] + P["usb_y"] + tuple(P["usb_z"]))), "mm", "v3 S37 (폭 12.5 · 높이 7.5 · 길이 25 이하)",
      pf("r4.3: RP2040-Zero가 핀 헤더 위(+1.3)라 USB-C 중심 z%.1f(v3 z13.2, r4.2 z9.45~16.95); 선반 홈·리브 x%.1f / x%.1f·F|F# 핀(z%.1f부터)·뒷벽 개구(z%.0f까지)와 %.2f 이상; 뒤 케이블 통로(z0~22, v3) 안에서 %.1f 여유. "
      "r4.4: 리셉터클이 제로 가장자리 밖으로 약 1.3(1.0~1.5) 나와 플러그 면 y%.1f(r4.3 y195.5) — 선반 홈 양옆 %.2f / %.2f는 선반 y%.1f~%.1f 내내, 뒷벽 개구 x %.2f / 위 %.2f, 통로 y%.0f~%.0f에서 굽힘 %.0f 뒤 %.1f 남음", (0.5 * (P["usb_z"][0] + P["usb_z"][1]), P["ribs"][5], P["ribs"][6], P["comp_zmax"] + 1.5, P["usb_wall_open"][3], R["r43"]["usb"]["min"][0], 22.0 - P["usb_z"][1],
         P["usb_y"][0], R["c44"]["usb"]["slot_margins"][0], R["c44"]["usb"]["slot_margins"][1], R["c44"]["usb"]["plug_under_shelf_y"][0], R["c44"]["usb"]["plug_under_shelf_y"][1],
         min(R["c44"]["usb"]["wall_x_margins"]), R["c44"]["usb"]["wall_z_margin"], R["c44"]["usb"]["passage"][0], R["c44"]["usb"]["passage"][1], R["c44"]["usb"]["bend"], R["c44"]["usb"]["passage_spare"])))
    zx_, zz_, rc_, mx_, rp_, ex_ = P["zero_xy"], P["zero_z"], P["usb_rcpt"], P["mux_xy"], P["ribbon_pads"], P["ext_pads"]
    d("P27", pf("제어 기판 부품 (회로 BRD-01, r4.4 격자 x = %.2f + 2.54i)", R["c44"]["zero"]["lattice_x"][0]), pf("부품 한계 z%.0f(y%.1f~%.1f), 선반 앞 띠 z%.1f(y%.1f~%.1f)", (P["comp_zmax"], P["comp_front_y"], P["comp_rear"][0], P["comp_rear"][1], P["comp_rear"][0], P["board_y"][1])), "mm",
      "모듈 좌표, BRD-01 배치",
      pf("RP2040-Zero x%.2f~%.2f y%.1f~%.1f 핀 헤더 위(PCB z%.1f~%.1f, 윗면 부품 z%.1f 이하 — 핀 끝은 자름), USB-C 리셉터클 x%.2f~%.2f y%.1f~%.1f z%.1f~%.1f(제로 가장자리 밖으로 %.1f); 4067 모듈 x%.2f~%.2f y%.1f~%.2f 핀 헤더 위 z%.0f 이하; "
      "J301 리본 2×8 x%.2f~%.2f y%.2f/%.2f 아랫면 납땜(윗면은 납땜 자국 z%.1f 이하), %d심 %.2f 폭 리본은 기판 밑 z%.0f~%.0f; J302 EXT 1×6 x%.2f~%.2f y%.2f(선은 아랫면에서 납땜, 기판 밑 z%.0f~%.0f → USB 터널 플러그 밑 → 뒷벽 개구). "
      "r4.3 값: 제로 x75.0, 리셉터클 y188.2~195.5, 4067 x53.3~71.1 y152.4~193.0, J301 x61.59~79.37 y148.59/151.13 윗면, J302 x95.25~107.95 y193.04", (zx_ + zz_ + rc_ + (rc_[3] - P["board_y"][1],) + mx_ + (P["comp_zmax"],) + rp_[:2] + rp_[2:] + (P["ribbon_z"], P["ribbon_cores"], P["ribbon_cores"] * P["ribbon_pitch"])
         + tuple(P["ribbon_under_z"]) + ex_ + (P["z_floor"][1], P["board_z"][0]))))
    # r4.4 (circuit cross-check 3-5): control-board stand-offs and the v3 sensor-board support (module + end parts)
    so_ = R["c44"]["standoffs"]
    scr_ = [q for q in so_ if q["kind"] == "screw"]
    if so_ and so_[0].get("hung"):
        # r4.4 fix 2b: bosses hung above the board, screws from below, pins hanging down; the floor under the board is open
        sq_ = R["c44"]["screw"]
        d("P35", "제어 기판 보스 (프레임 출력, r4.4 고침 2b: 기판 위에 매달림) · 바닥 구멍", pf("Ø%.0f 보스 4곳(나사 %s, 위치 핀 %s), 기판 윗면 z%.1f에 닿음; 앞 2곳은 밸런스 레일 뒷면 y%.1f까지 받침(윗면 z%.1f), 뒤 2곳은 선반 리브 x%.1f·x%.1f 앞면 y%.1f와 선반 밑면 z%.2f까지; 바닥 구멍 x%.2f~%.2f y%.1f~%.1f (리셉터클 뒤 x%.2f~%.2f는 y%.1f까지)",
          (P["standoff_d"], " · ".join(pf("(%.1f, %.1f)", (q["x"], q["y"])) for q in scr_), " · ".join(pf("(%.1f, %.1f)", (q["x"], q["y"])) for q in so_ if q["kind"] == "pin"), P["board_z"][1],
           P["rail_y"][1], P["board_boss"][0], P["ribs"][3], P["ribs"][8], P["rib_y0"], g["z_shelf"] - 2.0) + tuple(P["board_hatch"]) + tuple(P["board_hatch_notch"])),
          "mm", "모듈 좌표 (회로 BRD-01 구멍 자리 그대로)",
          pf("기판은 모듈을 뒤집어 바닥 구멍으로 밑에서 넣는다(홈이 F|F# 핀 발·킬을 따라 올라감, 길 위 최소 %.2f); M3×6(v3.2 L35 ISO 7380, 머리 Ø%.1f × %.2f)을 밑에서 — 머리는 기판 밑 z%.2f~%.1f, 기판 %.1f + 보스 %.1f, Ø%.1f 막힌 구멍 z%.1f까지(끝 z%.1f); 위치 핀 Ø%.1f가 보스에서 기판 Ø%.1f 구멍으로 아래로(끝 z%.1f, 반경 놀음 %.2f). "
             "M3 머리 ↔ 밸런스 레일 뒷면 %.2f, ↔ 선반 리브 %.2f (리브 축 위 %.2f), 머리 가장자리가 기판 모서리 밖 %.2f; 가장 가까운 BRD-01 부품 %.2f; r4.4 고침 2까지의 바닥 스탠드오프(Ø6 × z5~9)는 기판이 들어갈 길이 없어 뺌",
             (R["board_insert"]["min"], P["board_screw_real"][0], P["board_screw_real"][1], sq_["head_z"][0], sq_["head_z"][1], sq_["stack"][0], sq_["stack"][1], P["standoff_bore"][0], sq_["bore_top"], sq_["tip_z"],
              P["board_pin"][0], P["board_hole"], R["c44"]["pins"]["tip_z"], R["c44"]["pins"]["play"], min(q["rail_top"] for q in scr_), min(q["rib_top"] for q in scr_),
              min(q["rib_top_axis"] for q in scr_ if q["rib_top_axis"] is not None), max(0.0, -min(q["in_board"] for q in scr_)), min(q["part_min"][0] for q in so_))))
    else:
      d("P35", "제어 기판 스탠드오프 (프레임 출력, r4.4)", pf("Ø%.0f × z%.0f~%.0f 4곳: 나사 %s, 위치 핀 %s", (P["standoff_d"], P["z_floor"][1], P["board_z"][0],
                                                                           " · ".join(pf("(%.1f, %.1f)", (q["x"], q["y"])) for q in scr_), " · ".join(pf("(%.1f, %.1f)", (q["x"], q["y"])) for q in so_ if q["kind"] == "pin"))),
        "mm", "모듈 좌표 (회로 BRD-01 △14)",
        pf("나사 받침: Ø%.1f 구멍을 바닥 속 z%.1f까지, M3×6 나사 = v3.2 L35 스텐 유두 렌치볼트(ISO 7380, 머리 Ø%.1f × %.2f; 모델 머리 외곽 Ø%.1f × %.1f = DIN 912 Ø5.5 × 3.0도 덮음) = 기판 %.1f + 받침 %.1f + %.1f, 끝 z%.1f; 위치 핀 Ø%.1f가 기판 Ø%.1f 구멍을 지나 %.1f 위로(z%.1f). "
      "M3 머리 ↔ 밸런스 레일 뒷면 %.2f, ↔ 선반 리브 %.2f (리브 축 위 %.2f); %s; 받침 Ø6은 기판 가장자리 밖으로 %.2f; 가장 가까운 BRD-01 부품 %.2f. v3 P114 자리 (49.75,148)…는 머리 ↔ 레일 0.75, 리브 1.05라 옮김", (P["standoff_bore"][0], P["standoff_bore"][1], P["board_screw_real"][0], P["board_screw_real"][1], P["board_screw"][0], P["board_screw"][1], P["board_z"][1] - P["board_z"][0], P["board_z"][0] - P["z_floor"][1], R["c44"]["screw"]["stack"][2] - R["c44"]["screw"]["bore_below_tip"],
         R["c44"]["screw"]["tip_z"], P["board_pin"][0], P["board_hole"], P["board_pin"][1], P["board_z"][1] + P["board_pin"][1],
         min(q["rail_top"] for q in scr_), min(q["rib_top"] for q in scr_), min(q["rib_top_axis"] for q in scr_ if q["rib_top_axis"] is not None),
         (pf("머리가 기판 안(%.2f)", min(q["in_board"] for q in scr_))) if min(q["in_board"] for q in scr_) >= 0 else
         (pf("머리 가장자리가 기판 모서리(x%.2f / %.2f) 밖으로 %.2f(머리 밑면은 기판 위, 회로 △14는 Ø5.5 가정)", (P["board_x"][0], P["board_x"][1], -min(q["in_board"] for q in scr_)))),
         max(q["standoff_past_board"] for q in so_), min(q["part_min"][0] for q in so_))))
    E4_ = R["c44"]["ends"]
    L8_ = R["c45"]["ledge"]
    lx0_, lx1_, px1_, zl0_, zl1_ = P["sb_ledge"]
    (fy0_, fy1_), (ry0_, ry1_) = P["sb_ledge_y"]
    d("P36", "센서 기판 받침·센서 바 고정 (v3 P111·P112·P113; r4.4 받침, r4.5 회로 2차 오른쪽 턱)",
      pf("기둥 x%.1f~%.1f y%.1f~%.1f, 앞 리브 y%.1f~%.1f, 뒤 리브 y%.1f~%.1f (x%.1f~%.1f), 윗면 z%.1f; 오른쪽 턱 y%.1f~%.1f · y%.1f~%.1f: 립 x%.1f~%.1f z%.1f~%.1f, 기둥 x%.1f~%.1f z%.1f~%.1f",
         (P["sb_post"] + P["sb_rib_front"] + P["sb_rib_rear"] + P["sb_rib_x"] + (P["sb_board"][4], fy0_, fy1_, ry0_, ry1_, lx0_, lx1_, zl0_, zl1_, lx1_, px1_, P["z_floor"][1], zl1_))),
      "mm", pf("센서 기판 SB x%.1f~%.1f y%.2f~%.2f z%.1f~%.1f (v3 P108), 센서 바 x0.5~%.1f z8.6~%.1f (v3 P107)", tuple(P["sb_board"]) + (L8_["bar_end"], P["bar_top_w"])),
      pf("r4.4: 뒤 리브 틈 x%.0f~%.0f(v3 x60~82) = 리본 차선: 리본 x%.2f~%.2f 양옆 %.2f / %.2f (v3 틈이면 %.2f), J201 패드 %.2f / %.2f. "
         "r4.5 회로 2차(8번): 바·기판의 왼쪽 끝은 M3×10 자가 탭 2개(3.0, 61.9)·(3.0, 74.6)로 기둥에, 오른쪽 끝은 프레임과 한 몸인 오른쪽 턱(v3 P112, r4 내보냄에서 빠졌던 것; 질량은 v3 프레임 175 g에 이미 있음)이 잡는다: "
         "립 밑면 z%.1f = 백 구간 바 윗면, 바 끝 x%.1f 위를 %.1f 덮음(%.1f mm²), 기둥은 바 끝과 %.1f · 기판 끝과 %.1f, 이음 면에서 %.1f 안(핀과 같은 0.2); 두 조각은 B 센서 리드 줄(y%.1f~%.1f)을 %.1f / %.1f 피하고 립은 B 리드 구멍 열 x%.2f에서 %.2f 떨어짐. "
         "바·기판은 모듈 하나를 빼 놓고(왼쪽 이웃 없이) 1.5 mm 왼쪽에 내려놓은 뒤 오른쪽으로 밀어 턱 밑에 넣고 왼쪽 나사를 조인다(v3 절차). 가장 가까운 움직이는 부품 %.2f (공차 뒤 %.2f, %s), 이음매 너머 이웃 모듈 %.2f · ER %.2f(고정끼리, 이음 면 규칙 0.4 이상). "
         "끝 부속 바(EL x0.5~%.1f, ER x0.5~%.1f)는 턱 없이 같은 왼쪽 M3×10 2개와 리브로 잡는다(46.0 / 22.5 mm로 짧고, 기판 넣기로 뒤집지 않음); 끝 부속은 A02·A03",
         (P["sb_rib_gap"][0], P["sb_rib_gap"][1], P["ribbon_xc"] - P["ribbon_cores"] * P["ribbon_pitch"] / 2, P["ribbon_xc"] + P["ribbon_cores"] * P["ribbon_pitch"] / 2,
          R["c44"]["ribbon"]["sb_gap_margins"][0], R["c44"]["ribbon"]["sb_gap_margins"][1], R["c44"]["ribbon"]["sb_gap_margins_r43"][0], R["c44"]["ribbon"]["j201_margins"][0], R["c44"]["ribbon"]["j201_margins"][1],
          zl0_, L8_["bar_end"], L8_["over_bar"], L8_["held_area"], L8_["post_to_bar"], L8_["post_to_board"], L8_["seam_inset"], L8_["lead_y"][0], L8_["lead_y"][1], L8_["lead_y_gaps"][0], L8_["lead_y_gaps"][1],
          L8_["B_lead_col"], L8_["lip_to_B_col"], L8_["sweep"]["d"], L8_["sweep_after_tol"], mtr(L8_["sweep"]["a"] + " " + L8_["sweep"]["part_a"] + " " + L8_["sweep"]["pose_a"]),
          L8_["neighbour_module"][0], L8_["end_part_ER"][0], L8_["ends"]["left"]["bar"][1], L8_["ends"]["right"]["bar"][1])))
    d("P25", "센서 바 흑 낮은 구간", P["bar_low_half"], "mm", "흑건 중심 ±", "v3 ±6.0 → ±7.0")
    d("P26", "가림판 띠", pf("y%.1f~%.1f, 걸이 립 y%.1f~%.1f", (P["curtain_y"] + (P["curtain_y"][1], P["ledge_y0"] + P["curtain_hook"][0]))), "mm", pf("흑건 자리 노치 ±%.1f", P["curtain_notch_half"]),
      "윗판 앞 턱에 얹혀 들어서 뺌 (핀·자석 없음)")
    LD_ = R["r43"]["land"]
    L43_ = R["r44"]["land43"]
    d("P28", "꼬리 쉼 패드", pf("y%.1f~%.1f", P["rest_pad_y"]), "mm", "빔 폭 8 (F·F#는 아래)", "펠트 1.5T + 종이 펀칭 0.1×2; r4.4: USB 홈에 걸리는 펠트는 홈 가장자리에서 자르고 반대쪽으로 꼬리 끝까지: " +
      ", ".join(pf("%s x%.2f~%.2f(%.0f %% 앉음, r4.3 x%.2f~%.2f 중 %.0f %%)", (k_, v_["felt"][0], v_["felt"][1], 100 * v_["frac"], L43_[k_]["felt"][0], L43_[k_]["felt"][1], 100 * L43_[k_]["frac"]))
                for k_, v_ in LD_.items() if v_["frac"] < 1 - 1e-9 or abs(v_["felt"][1] - v_["felt"][0] - P["beam_w"]) > 1e-6))
    d("P29", "자석 y (백·흑)", P["y_elem"], "mm", "소자 열 y67 바로 위", "")
    d("P30", "흑건 앞면 (밑면/윗면 앞 모서리)", pf("%.1f / %.1f", (P["y_black_front"], P["y_black_front"] + 1.0)), "mm", "y0 기준", "")
    d("P31", "가이드 탭 (백/흑)", pf("앞면 %.1f / %.1f, 폭 %.1f / %.1f", (P["w_tab_y"][0], P["b_tab_y"][0], P["tab_w"], P["tab_w_b"])), "mm", pf("크로스바 뒷면 + %.1f", (P["w_tab_y"][0] - P["w_crossbar_y"][1])),
      pf("천 0.5T 양쪽: 백 %.1f 리브 사이, 흑 %.1f 낮은 벽 사이 → 옆 놀음 ±%.2f (r3 흑 7.5는 0.25 억지끼움)", (P["rib_in"], P["b_wall_in"], P["tab_play"])))
    zpt = P["block_step_z"] + P["pin_engage"]
    d("P32", "밸런스 핀", pf("ISO 2338 Ø%.1f×%.0f, y%.1f, 꼭대기 z%.2f ± 0.1 (출력 높이 게이지)", (P["pin_d"], P["pin_len"], P["pin_y"], zpt)), "mm", "블록 가운데 x",
      pf("블록 밑 홈 출력 폭 %.1f(천 0.5T 양쪽 → %.1f), 깊이 %.1f, y%.1f~%.1f 앞이 열림; 핀 ↔ 입술 벽 %.2f (r3 0.19~0.26)", (P["slot_w_print"], P["slot_w"], P["slot_depth"], P["slot_y"][0], P["slot_y"][1], R["clear"]["pin_lip_wall"])))
    d("P34", "키퍼 훅·펠트 폭", hu(2 * P["keeper_half"], 2), "mm", pf("탭 중심 ±%.1f", P["keeper_half"]), "")
    # ------------------------------------------------------------------ S side
    d("S01", "바닥 EVA / 프레임 바닥판", "z0~3 / z3~5", "mm", "v3 S01·S02", "")
    d("S02", "백건 윗면 / 밑면 / 흑건 윗면", pf("%.1f / %.1f / %.1f", (P["key_top"], P["key_bot"], P["black_top"])), "mm", "쉼", "v3 유지")
    d("S03", "건반 봉 중심 K", pf("(%.1f, %.1f)", P["K"]), "mm", "(y, z)", "Ø4 SUS304")
    Rn = P["notch_R"] - P["cloth"]
    hop = math.sqrt(Rn ** 2 - P["block_lift"] ** 2)
    d("S04", "스냅 노치", pf("R%.2f + 천 %.1fT → 유효 R%.2f, 블록 밑면 z%.2f (봉 중심 아래 %.2f)", (P["notch_R"], P["cloth"], Rn, P["K"][1] + P["block_lift"], -P["block_lift"])), "mm", "중심 = K",
      pf("감싸는 각 %.0f°, 입구 %.2f, 쉼에서 입술 틈 %.2f; 곧게 들리면 입술은 들림 %.2f에서 닿고 %.2f에서 빠짐 (흑건은 노치가 앞뒤로 밀려 들림 0.06에서도 입술 모서리가 닿음: 판정은 들림만); 빠짐 힘 %.0f~%.0f N(단계 0 반지름 쿠폰으로 고름)", (2 * math.degrees(math.acos(P["block_lift"] / Rn)), 2 * hop, R["snap"]["lip_clear_rest"], P["lift_play"], P["lift_popout"], P["snap_F_min"], P["snap_F"])))
    lip_, hs_, _ = m.rail_saddle(P)
    d("S05", "봉 받침(크래들) 홈", pf("입술 z%.1f, 바닥 z%.2f", (lip_, P["K"][1] + 0.05 - (P["rod_k"] / 2 + 0.05))), "mm", pf("y%.2f~%.2f (R%.2f)", (P["K"][0] - hs_, P["K"][0] + hs_, P["rod_k"] / 2 + 0.05)), "")
    d("S06", "꼬리 옆벽 봉 위 도려냄", pf("y%.0f~%.0f, 밑면 z%.1f", P["wall_relief"]), "mm", "건반 옆벽", "")
    d("S07", "숨은 빔", pf("z%.1f~%.1f, 폭 %.0f", (P["beam_z"][0], P["beam_z"][1], P["beam_w"])), "mm", "y146 → 캡스턴+4", "")
    cr_ = R.get("fix2b", {}).get("crown_rest", {})
    d("S08", "캡스턴 (M3×6 ISO 7380 + 너트 트랩)", pf("백 y%.2f, 흑 y%.2f, 머리 꼭대기 z%.1f (건반 좌표 = 설계 자세) = 프레임 안 정착 쉼에서 백 z%.3f · 흑 z%.3f", (caps["white"], caps["black"], P["z_c"], cr_.get("white", float("nan")), cr_.get("black", float("nan")))), "mm", "빔 가운데",
      pf("건반을 넣기 전 벤치 지그 T1a + 가짜 레버 T2(바늘 ↔ 읽기 턱)로 맞춤 (10.1장); r4.4 고침 2b: 지그 위 건반도 노치 천·쉼 펠트에 정착하므로 T2의 밑면·영점 받침은 정착 꼭대기 z%.2f 면(고침 2까지 z%.1f는 캡스턴을 백 %.3f · 흑 %.3f 높게 맞췄음)", (R.get("fix2b", {}).get("crown_T2", float("nan")), P["z_c"], P["z_c"] - cr_.get("white", float("nan")), P["z_c"] - cr_.get("black", float("nan")))))
    d("S09", "얇은 꼬리", pf("z%.1f~%.1f, 끝 y%.1f, 모따기 %.1f", (P["beam_z"][0], P["tail_top"], P["y_tail_end"], P["tail_chamfer"])), "mm", "", pf("폭 백 %.0f / 흑 %.0f", (P["beam_w"], P.get("tail_w_b", P["beam_w"]))))
    d("S10", "뒤 선반 윗면", g["z_shelf"], "mm", pf("y%.1f~%.1f", P["shelf_y"]), "쉼 펠트 1.5T + 펀칭 0.2를 넣어 맞춘 값")
    d("S11", "레버 봉 중심 L", pf("(%.2f, %.1f)", P["L"]), "mm", "(y, z)", pf("Ø4 SUS304, 허브 R%.1f, 구멍 Ø3.9 출력 → Ø4.0 드릴", P["hub_R"]))
    d("S12", pf("강철 블록 SS400 9×%g×%g", (P["steel_h"], P["steel_len"])), pf("y%.1f~%.1f, z%.1f~%.1f, 모따기 없음", (P["y_steel_front"], P["y_steel_rear"], P["z_sb"], P["z_st"])), "mm", "쉼 (레버 0°)",
      pf("%.1f g (r3 9×50×21.5 = 75.8 g); 드러난 윗면 y%.0f~%.0f(윗 립 사이 %.1f, y%.0f~%.0f는 전폭)의 가운데가 업스톱 접점", (
          Aw.lev.mass_of(m.RHO_ST), P["y_steel_front"] + 3, P["y_steel_rear"], P["steel_w"] - 2 * P["lip_over"], P["lip_segs"][0][1], P["lip_segs"][1][0])))
    d("S13", "캐리어", pf("앞면 y%.1f, 윗면 z%.1f, 앞 윗모서리 R%.0f, 손톱 턱 %.1f×%.1f (y%.1f~, z%.1f~%.1f, R%.0f 모서리를 채워 앞벽과 한 몸)", (P["y_lever_front"], P["z_st"] + P["lip"], P["cap_R_out"], P["nail_tab"][0], P["nail_tab"][1],
                                                                                   P["y_lever_front"] - P["nail_tab"][0], P["z_st"] - P["nail_tab_below"] - P["nail_tab"][1], P["z_st"] - P["nail_tab_below"], P["cap_R_out"])), "mm",
      pf("옆벽 %.1f, 아래 립 y%.0f부터, 뒤 바닥 y%.1f~%.1f", (P["carrier_wall"], P["lip_front_y"], P["carrier_floor_y"][0], P["carrier_floor_y"][1])),
      pf("쉼 각 백 %.2f° / 흑 %.2f°", (H["b_rest_w"], H["b_rest_b"])))
    d("S14", "캐리어 밑 펠트 띠 2T", pf("y%.1f~%.1f, z%.1f~%.1f", (P["felt_c_y"][0], P["felt_c_y"][1], P["z_c"], P["z_sb"])), "mm", "폭 7", "흑연 가루")
    d("S15", "업스톱 패드 면 (백 / 흑)", pf("y%.0f z%.2f~y%.0f z%.2f / z%.2f~z%.2f", (P["pad_y"][0], H["pad_face_w"][0], P["pad_y"][1], H["pad_face_w"][1], H["pad_face_b"][0], H["pad_face_b"][1])), "mm",
      pf("면의 기울기 %.2f° / %.2f°", (H["held_b_w"], H["held_b_b"])),
      pf("패드가 없는 1 N 정착 바닥(%.2f° / %.2f°)의 강철 윗면과 평행, 법선 방향 %+.2f / %+.2f (레버가 먼저); 패드가 있는 실제 1 N 바닥은 %.2f° / %.2f°라 면이 강철에 %.2f° / %.2f° 기움 (12 mm에 %.2f / %.2f mm)", (H["held_b_w"], H["held_b_b"], P["gap_us_w"], P["gap_us_b"], H["held_pad_b_w"], H["held_pad_b_b"], H["held_b_w"] - H["held_pad_b_w"], H["held_b_b"] - H["held_pad_b_b"],
         12 * math.tan(math.radians(H["held_b_w"] - H["held_pad_b_w"])), 12 * math.tan(math.radians(H["held_b_b"] - H["held_pad_b_b"])))))
    d("S16", "패드 쌓기", pf("패드 %.0f + 쐐기 + 패드 바 %.1f", (P["pad_h"], P["pad_bar_t"])), "mm", pf("패드 면 ~ 패드 바 윗면(자리) z%.2f", g["z_seat"]), "")
    d("S17", "패드 바 자리 (패드 구간 윗판 밑면)", g["z_seat"], "mm", "z", pf("앞부분은 윗판 홈 속 z%.2f~%.2f", (g["z_seat"], g["z_seat"] + P["pad_bar_t"])))
    d("S18", "모듈 맨 위 (윗판 윗면)", g["z_top"], "mm", "z", "그 위에 아무것도 없음 (v3 z59, r3 커버 z78.0 / 손나사 머리 z80.7)")
    d("S20", "키퍼 펠트 밑면", g["z_keep"], "mm", pf("크로스바 윗면 + %.1f", P["keeper_gap"]), pf("펠트 %.0fT; 훅을 r3보다 0.3 올림", P["keeper_felt"]))
    d("S21", "백 앞 펠트 윗면 선", pf("(y%.1f, z%.2f)~(y%.1f, z%.2f)", (g["w_felt_line"][0] + g["w_felt_line"][1])), "mm", "딥에서 바닥판과 평행", pf("펠트 2T + 저반발 PU 1T (e ≈ %.2f), y%.1f~%.1f로 자름", (P["front_e"], P["w_felt_y"][0], P["w_felt_y"][1])))
    d("S22", "흑 앞 펠트 윗면 선", pf("(y%.1f, z%.2f)~(y%.1f, z%.2f)", (g["b_felt_line"][0] + g["b_felt_line"][1])), "mm", "", "같은 구성")
    d("S23", "딥 (백 y0 / 흑 앞 모서리)", pf("%.1f / %.1f", (P["dip_w"], P["dip_b"])), "mm", "", pf("v3 유지; 1 N에서 흑건 앞이 펠트 위 %.2f (레버가 패드에 먼저)", H["held_pad_front_b"]))
    DP_ = R["clear"]["dip"]
    d("S24", "건반 회전각 (백 / 흑)", pf("%.2f / %.2f", (math.degrees(Aw.a_dip), math.degrees(Ab.a_dip))), "deg", "K 기준 (강체 기구)",
      pf("1 N 정착 바닥(패드 있음) %.2f / %.2f (노치가 봉에 앉는 것까지 넣은 앞끝 기준 %.2f / %.2f) = geometry의 건반 side_dip (r4.4; r4.3은 두 색 모두 강체 값을 내보냄, 이제 side_dip_rigid), 2.5 m/s 최대 %.2f / %.2f, 복귀 넘침 %.2f / %.2f (F %.2f, F# %.2f)", (DP_["white"]["held"], DP_["black"]["held"], DP_["white"]["front_angle"], DP_["black"]["front_angle"], H["a_ff_w"], H["a_ff_b"], H["a_over_w"], H["a_over_b"], R["r44"]["over_key"]["F"][0], R["r44"]["over_key"]["F#"][0])))
    d("S25", "레버 회전각 (백 / 흑)", pf("%.2f / %.2f", (math.degrees(Aw.b_dip), math.degrees(Ab.b_dip))), "deg", "L 기준 (강체 기구)",
      pf("1 N 정착 바닥 %.2f / %.2f, 최대 %.2f / %.2f, 복귀 넘침 %.2f / %.2f (F %.2f, F# %.2f; r4.4: 화음 자리·격자 포함)", (H["held_pad_b_w"], H["held_pad_b_b"], H["b_ff_w"], H["b_ff_b"], H["b_over_w"], H["b_over_b"], R["r44"]["over_key"]["F"][1], R["r44"]["over_key"]["F#"][1])))
    d("S26", "자석 이동 (백 / 흑)", pf("%.2f / %.2f", (R["sensor"]["white"]["travel"], R["sensor"]["black"]["travel"])), "mm", "y67",
      pf("바닥 간격 %.2f / %.2f, 최대 과다 누름 %.2f / %.2f", (R["sensor"]["white"]["bottom"], R["sensor"]["black"]["bottom"], R["sensor"]["white"]["ff"], R["sensor"]["black"]["ff"])))
    d("S27", "가림판 아래끝 (백 / 흑 노치)", pf("%.1f / %.1f", (g["z_curtain_w"], g["z_curtain_b"])), "mm", "", pf("r3 z45.2 → %.1f", g["z_curtain_w"]))
    d("S28", "뒷벽", pf("y%.0f~%.0f, z5~%.2f", (P["rear_wall"][0], P["rear_wall"][1], g["z_top"])), "mm", "",
      pf("USB 개구 x%.0f~%.0f z%.0f~%.0f (v3 그대로; r4.3 플러그 윗면 z%.1f와 %.1f); 안쪽 면에 스프링 홈 보스 12 (P18, 끝 부속 왼쪽 3 / 오른쪽 1)", (tuple(P["usb_wall_open"]) + (P["usb_z"][1], P["usb_wall_open"][3] - P["usb_z"][1]))))
    d("S29", "핀 높이", pf("z5~윗판 밑 (F|F# 핀: y%.1f~%.1f은 기판 홈을 지나 z%.0f부터(기판 밑 바닥 구멍, r4.4 고침 2b; 앞끝 y%.1f은 r4.5 고침), 그 뒤 뒷벽까지 z%.1f부터 매달림 — r4.3 USB 위도)",
                           (m.keel_front(P), P["fin_slot_y"][1], P["z_floor"][0], m.keel_front(P), P["comp_zmax"] + 1.5)), "mm", pf("y%.0f~%.0f", P["fin_y"]), "끝 핀은 도브테일 홈 위 z17.9부터")
    d("S31", "흑건 윗면 뒤끝 (가림판 밑)", pf("y%.1f~%.1f에서 z%.1f → z%.1f (입술 두께 %.1f, 밑면 z%.1f 그대로)", (P["black_skin_step"][0], P["y_skin_end"], P["black_top"], P["black_skin_step"][1], P["black_skin_step"][1] - (P["black_top"] - P["skin_b"]), P["black_top"] - P["skin_b"])),
      "mm", "흑건 5 + A#0", "r4.1: 패드 바를 뺄 때 흑 패드 아래 모서리(z55.40)가 흑건 뒤끝 윗면(z55.5)을 치던 것을 없앰; 가림판에 가려 보이지 않음")
    d("S30", "센서 소자 z (백 / 흑)", pf("%.2f / %.2f", (P["z_elem_w"], P["z_elem_b"])), "mm", "v3", "")
    # ------------------------------------------------------------------ D detail
    d("D01", "노치 라이닝", pf("부싱 천 %.1fT", P["cloth"]), "mm", "노치 R2.55 안쪽", "")
    d("D02", "캡스턴 너트 트랩", "M3 육각 너트, 옆에서 끼움, 위 Ø2.8 자가 잠김 구멍", "", "빔 안", pf("1/8회전 = 캡스턴 0.0625 mm = 가짜 레버 T2 바늘 %.2f / %.2f mm (백 / 흑, 10.1장)", (_TG["dummy_lever"]["per_colour"]["white"]["per8"], _TG["dummy_lever"]["per_colour"]["black"]["per8"])))
    sp = R["spring"]
    CAT_ = P["spring_cat"]
    d("D05", "비틀림 보조 스프링 (기본) — 미스미 " + CAT_["part"], pf("한국미스미 경제형 %s: SUS304-WPB d%.2f · ID %.1f · 3권(몸통 %.2f권) · 암 각 %.0f° 오른쪽 감기 · 암 %.0f/%.0f → 두 다리를 잘라 씀: 긴 다리 %.1f (축에서 끝, 접선; 접점에서 %.2f) / 짧은 다리 %.1f (접선, 굽힘 없음)",
                                                      (CAT_["part"], P["spring_d"], P["spring_ID"], P["spring_n"], P["spring_arm_deg"], CAT_["arms"][0], CAT_["arms"][1], P["spring_leg"], sp.get("l_long", 0.0), P["spring_short_leg"])), "mm",
      pf("k_t %.2f N·mm/rad (E %.0f, N_e %.3f), 자유각 %.2f° (b=0에서 %.2f° 감김): 쉼 %.2f, 바닥 %.2f N·mm", (P["spring_kt"], P["spring_E"], sp.get("N_e", 0.0), P["spring_free_deg"], -P["spring_free_deg"], sp["states"]["rest"]["T"], sp["states"]["bottom"]["T"])),
      pf("응력 최대 %.0f MPa (Su 2150의 %.0f %%, 손 들기 25°), 바닥 ID %.2f; 카탈로그 최대 사용각 %.0f° 안(손 들기 %.1f°)이나 토크는 카탈로그 55° 토크 %.2f의 %.0f %% (잘린 다리가 짧아 강성이 큼); 긴 다리가 코일 +x 끝에 오게 넣음",
         (max(v["sigma"] for v in sp["states"].values()), 100 * max(v["sigma"] for v in sp["states"].values()) / 2150, sp["ID_bottom"], CAT_["max_deg"], sp["states"]["hand 25 deg"].get("wound", 0.0),
          sp.get("cat", {}).get("T_max", 0.0), 100 * sp.get("hand_over_cat", 0.0))))
    d("D06", "허브 칼라 / 핀 보스", pf("칼라 Ø6 (P14) / 보스 Ø%.0f, 황동 없음", (2 * P["boss_R"])), "mm", "레버 허브 사이 / 핀", pf("보스 길이 = 핀 + 레버-핀 링 + %.2f(r4.4 고침 2: 떠밀린 레버가 요와 함께 핀과 1.3; 끝 핀은 한쪽)", P["boss_extra"]))
    RT_ = R["steel_retention"]["peaks"]
    d("D07", "캐리어 스냅 립 · 옆벽 · 접착", pf("위 립 %.1f×%.1f: 앞 y%.0f~%.0f(앞 y%.0f~%.0f는 전폭 뚜껑), 뒤 y%.0f~%.0f(뒷벽까지); 옆벽 윗단 z%.1f도 이 구간만, 그 사이 y%.0f~%.0f는 z%.1f (r4.4 고침 2: 강철 윗면보다 %.1f 낮음, 패드 밑으로 지나감); 아래 립 1.0×1.0 (y%.0f~%.1f, 캡스턴 펠트 앞까지); 강철 뒤 아래는 뒤 바닥 y%.1f~%.1f (두께 %.1f); "
          "옆벽 %.1f(주머니 %.1f), 강철은 두 19×40 옆면에 MS 폴리머를 바르고 밑에서 스냅으로 끼워 접착 (접착층 한쪽 %.2f, 접착 면 %.0f mm²; r4.4 고침 2b — 고침 2의 5분 에폭시는 열팽창 차이로 떨어짐)", ((P["lip_over"], P["lip"], P["lip_segs"][0][0], P["lip_segs"][0][1], P["y_steel_front"], P["y_steel_front"] + 3.0, P["lip_segs"][1][0], P["lip_segs"][1][1], P["z_st"] + P["lip"],
          P["lip_segs"][0][1], P["lip_segs"][1][0], P["z_st"] - P["wall_drop_pad"], P["wall_drop_pad"], P["lip_front_y"], P["felt_c_y"][0]) + P["carrier_floor_y"] + (P["carrier_floor_t"], P["carrier_side_wall"], P["lever_w"] - 2 * P["carrier_side_wall"], P["bond_t"], R["steel_retention"]["bond_geo"]["area"]))), "mm", "레버 좌표 (레버 0°)",
      pf("r4.4: 앞 립을 y%.0f → %.0f로 줄임 (r4.3 립 뒤끝이 1 N 바닥·ff에서 패드 옆 %.2f, 공차 뒤 %.2f) → 립 ↔ 패드 %.2f, 패드 바·레일 %.2f; 뒤 립 %.0f → %.0f (캡스턴 힘이 강철 뒤끝을 립에 밀어 올림: 매 음 %.1f N → 뿌리 %.1f MPa, r4.3 2 mm 립이면 %.1f MPa); "
      "r4.1: 패드 옆에 립이 없어 패드 ↔ 캐리어 옆벽은 스윕에서 검사; r4.4 고침 2: 스냅만으로는 옆벽이 벌어짐(판 모델, 18장) → 접착이 하중을 받음, 립은 굳는 동안만 잡음", (P["lip_gap_y"][0], P["lip_segs"][0][1], R["clear"]["lip43"]["d"], R["clear"]["lip43"]["d"] - m.TOL, R["clear"]["lip44"]["pad"], R["clear"]["lip44"]["rail"],
         P["lip_end_y"], P["lip_segs"][1][1], RT_["play"]["T_rear"], RT_["play"]["sig_rear"], RT_["play"]["sig_rear_r43"])))
    RC_ = R["clear"]["rod"]
    d("D18", "레버 봉 끝 (r4.4 geometry)", pf("마개 x%.1f~%.1f (Ø4.0, 끝 핀 면과 같게), 막힌 끝 핀 구멍 x%.1f까지 (벽 %.1f)", (RC_["plug"][0], RC_["plug"][1], RC_["blind_end"], lay["fins"][-1][1] - RC_["blind_end"])),
      "mm", pf("핀 보스 구멍 Ø3.9 출력 → Ø4.0 드릴 (핀 %d장)", RC_["n_bores"]),
      pf("축 놀음 %.2f + %.2f (봉 ±0.2면 %.2f~%.2f); 끝 부속은 이음 쪽 핀에 마개, 볼 쪽 핀은 막힘; geometry의 fixed 'lever rod'·'fin boss bore'·'lever rod end plug'", (RC_["play_left"], RC_["play_right"], RC_["play_left"] + RC_["play_right"] - RC_["rod_len_tol"], RC_["play_left"] + RC_["play_right"] + RC_["rod_len_tol"])))
    d("D08", "캐리어 앞 모서리 / 손톱 턱", pf("R%.0f / %.1f 앞으로 × %.1f", ((P["cap_R_out"],) + P["nail_tab"])), "mm", "캐리어 앞 윗모서리",
      pf("업스톱 접점 아님 (r4); 손톱으로 레버를 들어 올리는 턱. r4.2: 턱이 밑면 z%.1f 위의 R3 모서리를 채워 앞벽에 붙음 (r4.1은 0.37 떠 있었음; 질량 모델은 이미 모서리를 채워 계산)", (P["z_st"] - P["nail_tab_below"] - P["nail_tab"][1])))
    d("D09", "도브테일 (v3 D01~D03)", "뿌리 6·끝 9·깊이 4, 앞 z3~8.5 / 뒤 z3~17", "mm", "y6.5~15.5 / y198~207",
      pf("꼬리·쉼 패드와 최소 %.2f; 끝 부속: 왼쪽 수, 오른쪽 암", R["clear"]["dovetail_min"]) if R["clear"]["dovetail_min"] else "")
    d("D10", "쉼 펠트", pf("1.5T 양모 %.1f×8 + 종이 펀칭 0.1×%d", (P["rest_pad_y"][1] - P["rest_pad_y"][0], round(P["rest_shim"] / 0.1))), "mm", "꼬리 밑", pf("펀칭 한 장 = 건반 앞 %.2f 내려감", R["adjust"]["levelling_front_per_punching"]))
    d("D11", "업스톱 패드 / 캡스턴 펠트", pf("미세셀 우레탄 %.0fT + 펠트 %.0fT / 펠트 2T", (P["pad_foam"], P["pad_felt"])), "mm", "",
      pf("패드 실효 e ≤ %.2f (단계 0 시험 1: C01 진자대로 모델 pad_e 정의대로 측정, 17·17.1장; 설계 %.2f); 25 %% 압축 %.2f MPa; 패드 자리 강성 ≥ %.0f N/mm (100 N에 %.2f mm 이하, 설계 %.0f), 6건반 화음 자리 ≥ %.0f N/mm (60 N씩 6개에 %.2f mm 이하, 설계 %.0f)", (P["pad_e_pass"], P["pad_e"], H["sigma25"], P["seat_k_req"], 100.0 / P["seat_k_req"], g["seat_k"], P["seat_k_chord_req"], 60.0 / P["seat_k_chord_req"], R["seat"]["k_chord"])))
    d("D12", "흑건 앞 펠트 자리", pf("y%.1f~%.1f (바닥판 y%.1f~%.1f)", (P["b_felt_y"] + P["b_floor_y"])), "mm", "", "")
    d("D15", "스냅 노치 빠짐 힘", pf("%.0f~%.0f (모델 입술 법칙 1.99)", (P["snap_F_min"], P["snap_F"])), "N", "노치에서 위로",
      pf("덜걱 방지일 뿐, 판정은 들림(PLAY ≤ %.2f, ABUSE ≤ %.2f); 뒤 턱 당김 %.1f N(레버를 손으로 듦)", (P["lift_play"], P["lift_abuse"], g["removal_w"]["pull_N"])))
    d("D16", "PET 심 (조정)", pf("0.1 × 6 × %.1f (OHP 필름, 패드 재단 크기와 같음)", R["pad_cut_len"]), "mm", "패드와 쐐기 사이", pf("한 장 = 레버가 %.2f° 일찍 닿음 = 건반 앞 %.2f mm", (R["adjust"]["white_shim"]["db0_deg"], R["adjust"]["white_shim"]["front_mm"])))
    # ------------------------------------------------------------------ A assembly
    d("A01", "88건반 총폭 / 전체 폭(볼 포함)", "1222 / 1254", "mm", "v3 A01·A05", "그대로")
    d("A02", "왼쪽 끝 부속 (A0·A#0·B0)", 47.0, "mm", pf("x0~47, 볼 x−16~%.2f", m.END_DEF["left"]["cheek"][1]),
      pf("레버 x %s, 핀 %s, 보스 %s (이음 핀은 안쪽으로만), 패드 바 1 (건반마다 자기 쐐기), 센서 바 x0.5~46.5, 스프링 홈 보스 3, 뒤·앞 도브테일 수", (", ".join(pf("%.2f", v) for v in ep["left"]["lay"]["levers"].values()), ep["left"]["lay"]["fins"], R["end_parts"]["left"]["boss_len"]))
      + "; r4.4 " + _end_sb_txt(P, R, "left"))
    d("A03", "오른쪽 끝 부속 (C8)", 39.5, "mm", pf("로컬 x0~23.5, 볼 %.2f~39.5", m.END_DEF["right"]["cheek"][0]),
      pf("레버 x %.2f, 핀 %s, 보스 %s, 패드 바 1 (자기 쐐기), 센서 바 x0.5~23.0, 스프링 홈 보스 1, 도브테일 암", (ep["right"]["lay"]["levers"]["C8"], ep["right"]["lay"]["fins"], R["end_parts"]["right"]["boss_len"]))
      + "; r4.4 " + _end_sb_txt(P, R, "right"))
    d("A04", "모듈 Ok 시작 x", "47 + 164.5·(k−1)", "mm", "v3 A03", "")
    d("A05", "프레임 깊이 / 전체 깊이", "212 / 410", "mm", "v3 A10", "그대로")
    d("A06", "모듈 맨 위 vs 뒷바", pf("z%.2f vs 가운데 유닛 z22~122 · 스피커 z22~232", g["z_top"]), "mm", "", "뒷바보다 낮다")
    d("A07", "모듈 무게", R["mass"]["module_mass_g"] / 1000, "kg", "출력+강철+봉+패드+전자", pf("r3 2.03; 88건반 본체 %.1f kg", R["totals"]["body_kg"]))
    d("A08", "건반 보관함 (R29) 안치수", "338.8 × 172 × 77", "mm", pf("건반 칸 %.1f + 칸막이 1.2 + 옆 칸 %.1f", (R["spare_bay"]["key_zone"], R["spare_bay"]["side_zone"])),
      "백 7 + 흑 5 + A0·A#0·B0·C8 + 강철 2 + 봉 2 + 패드·스프링·심 (레버·패드 바는 위치별이라 예비 없음, 13장)")
    d("A09", "금속 (88건반)", pf("블록 %.2f + 봉 %.2f kg", (R["totals"]["steel_kg_88"], R["totals"]["rods_kg"])), "kg", "", "r3 9.52 kg")
    return D


def mass_ripple_r44(P, g, R):
    """r4.4: the lever mass model no longer double-counts the top lips (r4.1-r4.3 counted them over y150-186 and the
    side-wall top over the whole length): the lever is lighter, so every value solved from the settled bottom / DW
    target moves by <= 0.02 (old = geometry.r4_3.json, new = this model)."""
    G3 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "geometry.r4_3.json")))
    s3 = G3["solved"]
    ep3 = G3["end_parts"]
    wr = g["wedge_range"]
    pw, pb = g["pad_w"], g["pad_b"]
    zf = lambda pt: (m.pad_face_z(pt, P["pad_y"][0]), m.pad_face_z(pt, P["pad_y"][1]))
    EPS = R["end_parts"]
    old = (pf("lever %.2f g; capstan y white %.2f / black %.2f; pad face white z%.3f~%.3f (tilt %.2f deg), black z%.3f~%.3f; wedges white %.3f~%.3f, black %.3f~%.3f; "
           "end-part wedges A0 %.3f~%.3f, A#0 %.3f~%.3f, B0 %.3f~%.3f, C8 %.3f~%.3f; rigid lever bottom white %.2f deg", (57.21, s3["caps"]["white"], s3["caps"]["black"], s3["pad_face_w"]["z"][0], s3["pad_face_w"]["z"][1], 11.33, s3["pad_face_b"]["z"][0], s3["pad_face_b"]["z"][1],
              s3["wedge"]["w"][0], s3["wedge"]["w"][1], s3["wedge"]["b"][0], s3["wedge"]["b"][1],
              ep3["left"]["pad_faces"]["A0"]["wedge"][0], ep3["left"]["pad_faces"]["A0"]["wedge"][1], ep3["left"]["pad_faces"]["A#0"]["wedge"][0], ep3["left"]["pad_faces"]["A#0"]["wedge"][1],
              ep3["left"]["pad_faces"]["B0"]["wedge"][0], ep3["left"]["pad_faces"]["B0"]["wedge"][1], ep3["right"]["pad_faces"]["C8"]["wedge"][0], ep3["right"]["pad_faces"]["C8"]["wedge"][1], 12.60)))
    new = (pf("lever %.2f g; capstan y white %.2f / black %.2f; pad face white z%.3f~%.3f (tilt %.2f deg), black z%.3f~%.3f; wedges white %.3f~%.3f, black %.3f~%.3f; "
           "end-part wedges A0 %.3f~%.3f, A#0 %.3f~%.3f, B0 %.3f~%.3f, C8 %.3f~%.3f; rigid lever bottom white %.2f deg", ((g["Aw"].mL, g["caps"]["white"], g["caps"]["black"]) + zf(pw) + (math.degrees(g["held_b_w"]),) + zf(pb) + tuple(wr["w"]) + tuple(wr["b"])
              + tuple(EPS["left"]["stat"]["A0"]["wedge"]) + tuple(EPS["left"]["stat"]["A#0"]["wedge"]) + tuple(EPS["left"]["stat"]["B0"]["wedge"]) + tuple(EPS["right"]["stat"]["C8"]["wedge"])
              + (math.degrees(g["Aw"].b_dip),))))
    return dict(part="solved values (consequence, all keys / levers / pad bars): capstans, pad faces, printed wedges", dim="S08, S15, P17, S25, A07", old=old, new=new,
                why="the lever mass model counted the top lips over y150-186 and the side-wall top at z53 over the whole carrier (0.08 g too heavy); corrected with the r4.4 lips. "
                    "Every change is <= 0.02 mm (below FDM resolution) but the drawings print these numbers")


def changes_r44(P, g, R):
    """r4 fix round 4 (r4.3 -> r4.4, R44 issues 1-3): every geometry change (old = geometry.r4_3.json)."""
    lay = g["lay"]
    L4, L3 = R["r44"]["land"], R["r44"]["land43"]
    RT = R["steel_retention"]["peaks"]
    CL = R["clear"]
    return [
        dict(part="lever carrier (all 16 positions, module + end parts): top snap lip, front segment", dim="D07, S13", old="lip 0.8 x 1.0 over y150~168 (lever frame), side-wall top z53 to y168",
             new=pf("lip 0.8 x 1.0 over y%.0f~%.0f, side-wall top z%.0f to y%.0f (z%.0f behind it to y%.0f)", (P["lip_segs"][0] + (P["z_st"] + P["lip"], P["lip_segs"][0][1], P["z_st"], P["lip_segs"][1][0]))),
             why=pf("R44 issue 1: at the settled 1 N bottom and at ff the lip's rear end (y168) swung to world y172-173 z59-60 beside the pad: %.2f (x gap 0.64 after the lever yaw), %.2f after FDM; now lip to pad %.2f, to the pad bars / rails %.2f", (CL["lip43"]["d"], CL["lip43"]["d"] - m.TOL, CL["lip44"]["pad"], CL["lip44"]["rail"]))),
        dict(part="lever carrier (all): top snap lip, rear segment", dim="D07, S13", old="lip 0.8 x 1.0 over y184~186, side-wall top z52 over y186~190",
             new=pf("lip 0.8 x 1.0 over y%.0f~%.0f (to the steel's rear end / rear wall), side-wall top z%.0f over it", (P["lip_segs"][1] + (P["z_st"] + P["lip"],))),
             why=pf("R44 issue 1 retention: the capstan pushes the steel's rear end up into these lips on every note (%.1f N peak PLAY): root bending across the layers %.1f MPa with 2 mm (limit 5), %.1f MPa with 6 mm", (RT["play"]["T_rear"], RT["play"]["sig_rear_r43"], RT["play"]["sig_rear"]))),
        dict(part="keys F and F#: rest felt (cut piece)", dim="P28, D10", old=pf("F x%.2f~%.2f, F# x%.2f~%.2f (8.0 centred; %.0f / %.0f %% on the shelf, the rest over the USB slot)", (L3["F"]["felt"] + L3["F#"]["felt"] + (100 * L3["F"]["frac"], 100 * L3["F#"]["frac"]))),
             new=pf("F x%.2f~%.2f (%.2f wide, cut at the slot edge), F# x%.2f~%.2f (%.2f wide, cut at the slot edge and run to the black thin tail's edge): %.0f / %.0f %% land, nothing over the slot", (L4["F"]["felt"][0], L4["F"]["felt"][1], L4["F"]["felt"][1] - L4["F"]["felt"][0], L4["F#"]["felt"][0], L4["F#"]["felt"][1], L4["F#"]["felt"][1] - L4["F#"]["felt"][0],
                    100 * L4["F"]["frac"], 100 * L4["F#"]["frac"])),
             why=pf("R44 issue 2: the r4.3 felts overshot on the return into the USB plug envelope and (F#) its own lever: %d pairs < 1.3 (min %.2f) at the F / F# overshoot (key %.3f / %.3f, lever %.2f / %.2f deg); "
                 "now none (the F felt no longer hangs over the plug; F# lands stiffer). No key or frame part changes; circuit interface untouched (slot x%.2f~%.2f, plug, board envelope)", ((CL["r43_felts"]["n_bad"], CL["r43_felts"]["min"], R["r44"]["over_key_r43"]["F"][0], R["r44"]["over_key_r43"]["F#"][0], R["r44"]["over_key_r43"]["F"][1], R["r44"]["over_key_r43"]["F#"][1]) + m.usb_slot(P)))),
        dict(part="frame (module, end parts): pad-bar rail webs (8 per module, 2 per end part)", dim="P13", old=pf("web front end y%.1f square (front-bottom corner y%.1f z%.2f)", (P["rail_y0"], P["rail_y0"], g["z_seat"] - P["bar_rail"][1])),
             new=pf("45 deg chamfer %.1f x %.1f on the web's front-bottom corner (y%.1f~%.1f, z%.2f~%.2f)", (P["rail_front_chamfer"], P["rail_front_chamfer"], P["rail_y0"], P["rail_y0"] + P["rail_front_chamfer"],
                                                                                             g["z_seat"] - P["bar_rail"][1], g["z_seat"] - P["bar_rail"][1] + P["rail_front_chamfer"])),
             why=pf("the bay-edge carrier side walls pass that corner at ff with 1.30 (r4.3 1.32): the r4.4 lever lost 0.08 g of lip mass the r4.3 mass model double-counted and swings 0.02 deg higher; "
                 "now lever-rail %.2f. The pad bar never touches that corner (it runs above z%.2f)", (CL["named"]["레버 ↔ 패드 바·레일"]["d"], g["z_seat"] - P["bar_rail"][1] + P["rail_front_chamfer"]))),
        dict(part="frame (module, end parts): lever-rod fin-boss bores, rod, rod-end plug", dim="D18 (new), P22, D06", old="text only ('printed D3.9 bores drilled D4.0', 'plug 1.2', 'blind wall 1.2'); not in geometry.json",
             new=pf("fixed prisms 'lever rod D4 SUS304' x%.1f~%.1f, 'fin boss bore D4.0' per fin (right end fin blind to x%.1f), 'lever rod end plug' x%.1f~%.1f flush with the end-fin face; end parts: plug at the seam fin, cheek-side fin blind", (CL["rod"]["rod"] + (CL["rod"]["blind_end"],) + CL["rod"]["plug"])),
             why=pf("R44 issue 1 (drafter): exported and swept so this class of miss cannot recur; closest moving part %.2f", (CL["rod"]["sweep_min"][0] if CL["rod"]["sweep_min"] else -1))),
        dict(part="geometry.json key poses (all keys)", dim="S24", old=pf("key side_dip = max(settled, rigid) = the rigid kinematic bottom (white %.2f, black %.2f deg)", (CL["dip"]["white"]["rigid"], CL["dip"]["black"]["rigid"])),
             new=pf("key side_dip = the truly settled 1 N bottom with the pad as the full planar key state (white %.2f, black %.2f deg + the notch settling on the rod = front point %.2f / %.2f deg about K); "
                 "side_dip_rigid added; the sweep checks both", (CL["dip"]["white"]["held"], CL["dip"]["black"]["held"], CL["dip"]["white"]["front_angle"], CL["dip"]["black"]["front_angle"])),
             why="R44 issue 3: same pose as the levers' side_dip (settled with the pad); no part changes"),
        dict(part="geometry.json overshoot poses of keys / levers F and F#", dim="S24, S25",
             old=pf("F / F# swept at their colour's overshoot (white key %.3f / lever %.2f deg, black %.3f / %.2f)", (math.degrees(R["r44"]["over_r43"]["a_w"]), math.degrees(R["r44"]["over_r43"]["b_w"]), math.degrees(R["r44"]["over_r43"]["a_b"]), math.degrees(R["r44"]["over_r43"]["b_b"]))),
             new=pf("F key %.3f / lever %.2f deg, F# %.3f / %.2f from their own landing runs (PLAY on the 6-key chord seat + ABUSE single key, nominal + pass line); the colours keep white %.3f / %.2f, "
                 "black %.3f / %.2f (the added PLAY chord seats, grids and pass line are not deeper). ABUSE 6-key chord / 2.5 m/s on the chord seat: checked for no contact (min %.2f)", (R["r44"]["over_key"]["F"][0], R["r44"]["over_key"]["F"][1], R["r44"]["over_key"]["F#"][0], R["r44"]["over_key"]["F#"][1], R["heights"]["a_over_w"], R["heights"]["b_over_w"],
                    R["heights"]["a_over_b"], R["heights"]["b_over_b"], CL["over_brief"]["d"])),
             why="R44 issue 2: the return-overshoot pose sweep of F / F#; no part changes"),
        mass_ripple_r44(P, g, R),
    ]


def ripple_f2(s0, s1, e0, e1, lev0, lev1):
    # r4.4 fix 2: solved values moved by the lighter lever (pad-zone side walls 2.6 lower): old / new from the geometry.json
    # 'solved' / 'end_parts' blocks (s0, e0 = geometry.r4_4a.json; s1, e1 = this export)
    def fmt(s_, e_, lv):
        lp = e_["left"]["pad_faces"]
        rp = e_["right"]["pad_faces"]
        return pf("lever %.2f g; capstan y white %.2f / black %.2f; pad face white z%.3f~%.3f, black z%.3f~%.3f; pad-bar seat z%.2f, top plate z%.2f (module top); "
                  "wedges white %.3f~%.3f, black %.3f~%.3f; end-part wedges A0 %.3f~%.3f, A#0 %.3f~%.3f, B0 %.3f~%.3f, C8 %.3f~%.3f",
                  (lv, s_["caps"]["white"], s_["caps"]["black"], s_["pad_face_w"]["z"][0], s_["pad_face_w"]["z"][1], s_["pad_face_b"]["z"][0], s_["pad_face_b"]["z"][1],
                   s_["z_seat"], s_["z_top"], s_["wedge"]["w"][0], s_["wedge"]["w"][1], s_["wedge"]["b"][0], s_["wedge"]["b"][1],
                   lp["A0"]["wedge"][0], lp["A0"]["wedge"][1], lp["A#0"]["wedge"][0], lp["A#0"]["wedge"][1], lp["B0"]["wedge"][0], lp["B0"]["wedge"][1],
                   rp["C8"]["wedge"][0], rp["C8"]["wedge"][1]))
    return dict(part="solved values (consequence, all modules / end parts): capstans, pad faces, pad-bar seat, top plate, printed wedges", dim="S08, S15, P17, S16, S19, A06, A07",
                old=fmt(s0, e0, lev0), new=fmt(s1, e1, lev1),
                why="fix 2 consequence: the carrier side walls are 2.6 lower over the pad zone (0.11 g lighter lever), so the settled 1 N bottom and the pad faces move up 0.006-0.008; "
                    "the pad-bar seat is rounded up to the next 0.05 (wedge >= 0.3 over the thickest-backed pad), so the seat and the whole top plate go up 0.05 and every wedge is 0.04 thicker")


def changes_f2(P, g, R, ep):
    """r4.4 fix 2 (verifier round on r4.4): every geometry / assembly change (old = geometry.r4_4a.json = fix 1 + circuit
    cross-check + documentation)."""
    G0 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "geometry.r4_4a.json")))
    s0 = G0["solved"]
    CL = R["clear"]
    SR = R["steel_retention"]
    WP = SR["wall_plate"]
    BD = SR["bond"]
    RP = g.get("rail_pocket") or {}
    col0, col1 = s0["collars"], g["collars"]
    chg = [n for n in m.ORDER if any(abs(a - b) > 1e-6 for a, b in zip(col0[n], col1[n]))]
    e0 = s0["end_parts"]
    ech = []
    for sd in ("left", "right"):
        for n, v in ep[sd]["collars"].items():
            if any(abs(a - b) > 1e-6 for a, b in zip(e0[sd]["collars"][n], v)):
                ech.append(pf("%s %.2f/%.2f -> %.2f/%.2f", ((n,) + tuple(e0[sd]["collars"][n]) + tuple(v))))
    Gm = G0.get("r44", {}).get("steel_retention", {})
    out = [
        dict(part="lever carrier (all 16 positions, module + end parts): side walls in the pad zone", dim="D07, S13",
             old=pf("side-wall top z%.1f (= the steel top) over y%.0f~%.0f (between the top-lip segments)", (P["z_st"], P["lip_segs"][0][1], P["lip_segs"][1][0])),
             new=pf("side-wall top z%.1f over y%.0f~%.0f (%.1f below the steel top: the wall passes under the pad face)", (P["z_st"] - P["wall_drop_pad"], P["lip_segs"][0][1], P["lip_segs"][1][0], P["wall_drop_pad"])),
             why=pf("verifier geometry major 4a: with the lever's axial float (up to %.2f) and the pad bar's +-%.1f the wall stood %.2f beside its own pad (fix-1 wall, same play); now %.2f", (max(max(v) for v in CL["lever_float"].values()), P["pad_bar_clear"], CL["lip_pad_fix1"], CL["lip_pad"]))),
        dict(part="lever carrier + steel block (all 90): retention", dim="D07, parts list",
             old="steel snapped past the bottom lips only (the lips carry the carrier-steel load)",
             new=pf("steel snapped in, then its two 19 x 40 side faces bonded to the side walls with 2-part epoxy (%.0f mm2); the lips only hold it while the glue cures", SR["bond_geo"]["area"]),
             why=pf("verifier physics majors 1-2 + side-wall plate model: the snap alone opens %.2f-%.2f at PLAY 1.5 m/s (overhang 1.0) and bends the wall at the lip root to %.1f MPa (in-layer limit 12), bottom lip %.1f MPa across layers (limit 5); "
                    "bonded: shear %.3f MPa every note, %.3f ABUSE (allowed %.2f / %.2f)", (WP["play_a0.50_clamped"]["spread_max"], WP["play_a0.50_pinned"]["spread_max"], WP["play_a0.50_pinned"]["s_root"], SR["peaks"]["play"]["sig_bottom"],
                                                                                            BD["play"].get("tau_mech", BD["play"]["tau"]), BD["abuse"].get("tau_mech", BD["abuse"]["tau"]), P["bond_tau_epoxy"] / P["bond_sf_play"], P["bond_tau_epoxy"] / P["bond_sf_rare"]))),
        dict(part="lever carriers %s: hub collars (module)%s" % ("/".join(chg), ("; end parts " + ", ".join(ech)) if ech else ""), dim="P14, K*",
             old="; ".join(pf("%s %.2f/%.2f", ((n,) + tuple(col0[n]))) for n in chg), new="; ".join(pf("%s %.2f/%.2f", ((n,) + tuple(col1[n]))) for n in chg),
             why=pf("verifier geometry major 4b: a lever-lever pair's collars sum to >= %.2f (A#|B was 1.40); with the pair's free gap closed and both levers yawed the carriers keep %.2f", (2 * P["collar_min"], CL["cls_min"]["lever-lever"]["d"]))),
        dict(part="frame (module + end parts): fin bosses on the lever rod", dim="D06, P22, D18",
             old="; ".join(pf("%.2f/%.2f", tuple(b)) for b in s0["boss_len"]), new="; ".join(pf("%.2f/%.2f", tuple(b)) for b in m.fin_boss_len(g["lay"], P)),
             why=pf("verifier geometry major 4 (axial float): a lever floated onto its boss and yawed was 1.30 from the fin's full-thickness front (y%.0f); every boss +%.2f -> lever-fin %s; bay play %s", (P["fin_main_y0"], P["boss_extra"],
                    pf("%.2f", min(q_["d"] for q_ in R["clear"]["closest"] if q_["b"] == "fin")) if any(q_["b"] == "fin" for q_ in R["clear"]["closest"]) else ">= 1.30", " / ".join(pf("%.2f", q_) for q_ in R["axial_play"])))),
    ]
    for c_, q_ in RP.items():
        if q_:
            out.append(dict(part=pf("frame (module + end parts): balance rail under every %s block", ("black-key" if c_ == "black" else "white-key",)), dim="P20",
                            old=pf("top z%.1f over the whole block zone", g["z_rail_low"]), new=pf("pocket top z%.2f behind y%.1f (block x +-4.0 + the key-play margin; the pin row y%.1f stays z%.1f)", (q_["z"], q_["y"], P["pin_y"], g["z_rail_low"])),
                            why=pf("verifier geometry major 3: with the notch seated / sinking on the rod the block's lip region comes to z%.3f (%s); pocket -> block-to-rail %.2f", (q_["zmin"], q_["pose"], min(qq_["d"] for qq_ in R["clear"]["closest"] if qq_["b"].startswith("balance rail")) if any(qq_["b"].startswith("balance rail") for qq_ in R["clear"]["closest"]) else CL["named"]["건반 블록 ↔ 밸런스 레일(낮춘 곳·받침)"]["d"]))))
    for nm, rl in {"F": (184.0, 195.8, 0.1), "F#": (184.0, 195.8, 0.1)}.items():       # fix-2 values (fix 2b: see changes_f2b)
        out.append(dict(part="key %s: beam / thin-tail underside" % nm, dim="K" + nm, old=pf("z%.1f", P["beam_z"][0]), new=pf("z%.1f over y%.1f~%.1f (in front of the rest felt)", (P["beam_z"][0] + rl[2], rl[0], rl[1])),
                        why=pf("the notch seating on the rod (now in the sweep) brought the %s tail at its own return overshoot to 1.24-1.25 of the control board's component envelope (<= z20, circuit interface, unchanged); now >= 1.30", nm)))
    out.append(dict(part="geometry.json key poses (all keys, module + end parts)", dim="S24",
                    old="side_dip_rigid / side_ff / side_over = rotation about K only", new="rotation about K + the notch translation on the rod as swept (r44.key_shift; side_dip was already the exact planar state)",
                    why="verifier geometry major 3: the exported dip had the notch sink but the sweep did not; now the sweep and the export use the same poses"))
    yp_ = min([q_["y"] for q_ in RP.values() if q_] + [138.1])
    out.append(dict(part="printed tool T3 (balance-pin gauge): rear foot", dim="T24 (tools_geometry.json)", old="land y136.75~138.0",
                    new=pf("land y136.75~%.2f, the body behind it 0.3 above the rail (the foot stays on the z%.1f surface in front of the rail pockets)", (yp_ - 0.1, g["z_rail_low"])),
                    why=pf("verifier geometry major 3 / printables: the rail pockets start at y%.1f (black) / y%.1f (white)", ((RP.get("black") or {}).get("y", float("nan")), (RP.get("white") or {}).get("y", float("nan"))))))
    out.append(dict(part="stage-0 coupons C03a / C03b / C03c (plate-modulus strip)", dim="stage0_geometry.json", old="strip 80 x 12 x 5.5 on a 60 span, dial on the nose plate",
                    new="strip 120 x 12 x 5.5 on a 100 span (C03b base 30 x 120), C03c nose with a D4 hole at mid-span so the dial reads the strip top directly",
                    why="verifier printables major: the 6.5 % chord-seat decision rested on 0.018 mm of dial reading through three line contacts; now ~1.2 mm of signal"))
    out.append(dict(part="stage-0 kit: carrier C16a (production carrier C, 3) + base C16b (new, test 20)", dim="stage0_geometry.json", old="no test 20 in the kit",
                    new="C16a from model_v4.lever_prisms (bore / cavity cut in 2-D), C16b slotted base 40 x 46 x 8 (slot 9.6)", why="verifier printables major: test 20 (steel retention) now in the kit"))
    return out


def changes_f2b(P, g, R, ep):
    """r4.4 fix 2b (re-verification of fix 2): every geometry / assembly change (old = geometry.r4_4b.json = fix 2)."""
    G0 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "geometry.r4_4b.json")))
    BI = R["board_insert"]
    SR = R["steel_retention"]
    BD = SR["bond"]
    H = R["heights"]
    C4 = R["c44"]
    so = C4["standoffs"]
    KE = R["plate"]
    cr = R["fix2b"]["crown_rest"]
    tr0 = {"F": (184.0, 195.8, 0.1), "F#": (184.0, 195.8, 0.1)}
    rel = []
    for nm, rl in P["tail_relief"].items():
        o_ = tr0.get(nm)
        if o_ != tuple(rl):
            rel.append((nm, o_, rl))
    out = [
        dict(part="frame (module): floor under the control board", dim="P35, frame",
             old="solid floor z3-5 (the board sat on 4 floor stand-offs D6 x z5-9)",
             new=pf("hatch x%.2f-%.2f y%.1f-%.1f (1.0 around the board) + notch x%.2f-%.2f to y%.1f (1.0 behind the USB-C receptacle); the frame is %.1f g lighter", tuple(P["board_hatch"]) + tuple(P["board_hatch_notch"]) + (-(R["mass"]["frame_parts"]["floor_board_hatch"] + R["mass"]["frame_parts"]["fin_keel"] + R["mass"]["frame_parts"]["board_bosses"]) if "frame_parts" in R.get("mass", {}) else float("nan"),)),
             why=pf("verifier geometry CRITICAL: the board could not be put into the one-piece frame (F|F# foot floor-to-plate through its front-open slot, the fin hung over its solid strip, the plate over it, 1.3 behind it); now it rises straight up from below: closest frame part along the path %.2f (%s), stops = the four hung bosses", (BI["min"], BI["pair"][1][:40]))),
        dict(part="frame (module): F|F# fin foot", dim="P12, D18",
             old=pf("foot y%.0f-%.1f standing on the floor (z5), grounded there", tuple(P["fin_slot_y"])),
             new=pf("foot down to z%.0f in the hatch + keel y%.1f-%.0f z%.0f-%.0f (the fin plate continued forward inside the board slot) joined to the balance rail's rear face", (P["z_floor"][0], P["fin_keel"][0], P["fin_y"][0], P["fin_keel"][1], P["fin_keel"][2])),
             why=pf("the floor under the foot is gone; plate FE with the keel clamped at the rail: 6-key chord seat %.0f N/mm (fix 2: 491.9 with a rigid floor), F / F# single seats %.0f / %.0f N/mm; keel bending %.2f / %.2f / %.2f MPa (single PLAY / chord PLAY / ABUSE chord)",
                    (R["seat"]["k_chord"], R["seat"]["k_keys"]["F"], R["seat"]["k_keys"]["F#"], KE["play"]["single"].get("keel_sigma", 0), KE["play"]["chord"].get("keel_sigma", 0), KE["abuse_chord20"]["chord"].get("keel_sigma", 0)))),
        dict(part="frame (module): 4 control-board stand-offs -> 4 bosses hung above the board", dim="P35",
             old="D6 x z5-9 on the floor at (50,149) screw, (114.5,149) pin, (50,192.5) pin, (114.5,192.5) screw; M3x6 from above (head on the board top); pins D2.8 up to z11.8",
             new=pf("same 4 points: D6 bosses above the board (z%.1f up), front two on brackets from the balance rail's rear face (to z%.1f), rear two on brackets from the shelf ribs x50 / x116 and the shelf underside (to z%.2f); M3x6 from BELOW (head under the board z%.2f-%.1f) into D2.5 blind bores to z%.1f; pins D2.8 hanging down through the board to z%.1f",
                    (P["board_z"][1], P["board_boss"][0], g["z_shelf"] - 2.0, C4["screw"]["head_z"][0], C4["screw"]["head_z"][1], P["board_boss"][1], C4["pins"]["tip_z"])),
             why=pf("a board coming from below cannot pass stand-offs under it; bosses: closest BRD-01 part %.2f, head to the rail %.2f / ribs %.2f (unchanged plan points), board ring %.2f", (min(q["part_min"][0] for q in so), min(q["rail_top"] for q in so if q["kind"] == "screw"), min(q["rib_top"] for q in so if q["kind"] == "screw"), min(q["edge_ring"] for q in so if q["kind"] == "screw")))),
        dict(part="lever carrier (all 16 positions): side walls and top snap lips", dim="P11, D07",
             old=pf("side walls %.1f (pocket %.1f = the steel: zero bond line), top lips %.1f wide", (P["carrier_wall"], P["lever_w"] - 2 * P["carrier_wall"], 0.8)),
             new=pf("side walls %.1f (pocket %.1f: bond line %.2f each side), top lips %.1f wide (inner edge x +-%.1f and outside width %.1f unchanged); front / rear walls %.1f", (P["carrier_side_wall"], P["lever_w"] - 2 * P["carrier_side_wall"], P["bond_t"], P["lip_over"], P["lever_w"] / 2 - P["carrier_side_wall"] - P["lip_over"], P["lever_w"], P["carrier_wall"])),
             why="verifier physics major 2: the bond had no gap to go into (10.6 - 2 x 0.8 = 9.0 = steel) and DESIGN 10 had no bonding step"),
        dict(part="steel block bond (all 90)", dim="D07, parts list, 10 step 4",
             old=pf("2-part 5-min epoxy after snapping in (thermal edge shear %.2f MPa at dT %.0f K, line %.2f - above its %.1f MPa strength)", (m.bond_thermal(P, P["bond_dT"][0], G=P["bond_G_epoxy"], t_a=P["bond_t"])["tau"], P["bond_dT"][0], P["bond_t"], P["bond_tau_epoxy"])),
             new=pf("MS-polymer (hybrid) flexible adhesive buttered on both steel faces, then snapped in; per note %.3f + thermal %.3f = %.3f MPa, rare %.3f + %.3f = %.3f (allowed %.3f / %.3f); slip at the pad peak %.4f mm",
                    (BD["play"]["tau_mech"], BD["play"]["tau_th"], BD["play"]["tau"], BD["abuse"]["tau_mech"], BD["abuse"]["tau_th"], BD["abuse"]["tau"], BD["play"]["limit"], BD["abuse"]["limit"], BD["play"]["slip"])),
             why="verifier physics major 1: thermal-mismatch shear of a rigid bond on 0.8 PETG walls over 40 mm; stage-0 test 20 now cycles 5-45 C before the push / drop"),
    ]
    for nm, o_, rl in rel:
        out.append(dict(part="key %s: beam / thin-tail underside" % nm, dim="K" + nm, old=(pf("z%.2f over y%.1f~%.1f", (P["beam_z"][0] + o_[2], o_[0], o_[1])) if o_ else pf("z%.1f", P["beam_z"][0])),
                        new=pf("z%.2f over y%.1f~%.1f (in front of the rest felt)", (P["beam_z"][0] + rl[2], rl[0], rl[1])),
                        why="verifier geometry major: with the worst material set's PLAY return overshoot in the sweep the E / G thin tails and the F beam / tail came 1.27-1.30 from the control board's component envelope (<= z20, circuit interface, unchanged); now >= 1.30"))
    ov2 = H.get("over_f2", {})
    out.append(dict(part="sweep poses (all keys / levers): return overshoot and ff", dim="S24, S25",
                    old=pf("nominal + pass line: white key %.3f / lever %.2f, black %.3f / %.2f deg; F %.3f / %.2f", (ov2.get("w", (float("nan"),) * 2)[0], ov2.get("w", (float("nan"),) * 2)[1], ov2.get("b", (float("nan"),) * 2)[0], ov2.get("b", (float("nan"),) * 2)[1],
                                                                                                          R["r44"]["over_key_f2"]["F"][0], R["r44"]["over_key_f2"]["F"][1])),
                    new=pf("+ the worst material set (PLAY): white key %.3f / lever %.2f, black %.3f / %.2f deg; F %.3f / %.2f, F# %.3f / %.2f", (H["a_over_w"], H["b_over_w"], H["a_over_b"], H["b_over_b"], R["r44"]["over_key"]["F"][0], R["r44"]["over_key"]["F"][1], R["r44"]["over_key"]["F#"][0], R["r44"]["over_key"]["F#"][1])),
                    why="verifier geometry major: the case grid's worst materials were computed but not swept"))
    out.append(dict(part="printed tool T2 (capstan bench gauge): dummy-lever floor and jig zero pads", dim="S08, T-dims (tools_geometry.json)",
                    old=pf("floor plane / calibration-rod top z%.1f (the key-frame crown)", P["z_c"]),
                    new=pf("z%.2f = the crown at the settled rest (white %.3f, black %.3f): the key on the jig sinks on its notch cloth / rest felt as in the frame", (R["fix2b"]["crown_T2"], cr["white"], cr["black"])),
                    why=pf("verifier printables major: z%.1f turned every capstan out %.3f (white) / %.3f (black) mm = %.2f / %.2f eighth-turns (up-stop gap %.2f -> about -0.73)", (P["z_c"], P["z_c"] - cr["white"], P["z_c"] - cr["black"], (P["z_c"] - cr["white"]) / 0.0625, (P["z_c"] - cr["black"]) / 0.0625, P["gap_us_w"]))))
    out.append(dict(part="stage-0 test 20 (C16a / C16b): procedure", dim="stage0_procedure.md", old="epoxy, room temperature only",
                    new="MS polymer; 3 cycles 5 C (fridge / freezer) <-> 45 C (warm water in a bag / car) before the 116 N push and the 1 m drop", why="verifier physics major 1 (thermal mismatch)"))
    return out


def changes_r45(P, g, R, ep):
    """r4.5 (user decision 2026-09-28: MISUMI C-UA90R5-3-0.5 instead of the custom D05 spring): every geometry / assembly change
    (old = geometry.r4_4.json = r4.4 fix 2b)."""
    G0 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "geometry.r4_4.json")))
    S0 = G0["solved"]["spring"]
    SL = R["r42"]["spring_slot"]
    NT = SL["notch"]
    IN = R["r45"]["insert"]
    HN = R["r45"]["hub"]["abuse"]
    sg = P["spring_groove"]
    sp = R["spring"]
    out = [
        dict(part="torsion assist spring (bought, 100 = 88 + 4 stage-0 tests + 8 spares): custom D05 -> catalogue part", dim="D05, parts list, cost",
             old=pf("custom wound SUS304-WPB d%.1f ID %.1f %.1f turns, short leg 2.5 bent %.1f deg onto the slot face, long leg %.1f; k_t %.1f N mm/rad, free %.1f deg; 100 x 200 KRW (estimate)",
                    (S0["d"], S0["ID"], S0["n"], S0["short_leg_bend_deg"], S0["leg"], S0["kt"], S0["free_deg"])),
             new=pf("MISUMI Korea %s (SUS304-WPB d%.1f ID %.1f, 3 turns = %.2f body turns, arm angle %.0f deg right-hand, arms 50/50), both arms cut: long %.1f (axis -> tip; %.2f from the tangent point), short %.1f straight; "
                    "k_t %.3f N mm/rad (catalogue E %.0f, N_e %.3f), free %.2f deg (same b = 0 torque %.2f N mm); long leg at the coil's +x end; 100 x 310 KRW (282 + VAT)",
                    (P["spring_cat"]["part"], P["spring_d"], P["spring_ID"], P["spring_n"], P["spring_arm_deg"], P["spring_leg"], sp["l_long"], P["spring_short_leg"], P["spring_kt"], P["spring_E"], sp["N_e"],
                     P["spring_free_deg"], sp["states"]["rest"]["T"])),
             why=pf("user decision 2026-09-28: buy a stock spring instead of having one wound; rest torque kept (DW / UW unchanged), bottom torque %+.0f %%, hand-lift 25 deg torque %.0f %% of the catalogue's 55-deg torque (DESIGN 18)",
                    (100 * (sp["states"]["bottom"]["T"] / (S0["kt"] * math.radians(math.degrees(R["white"]["b_dip"]) - S0["free_deg"])) - 1) if "b_dip" in R["white"] else 3.0, 100 * sp["hand_over_cat"]))),
        dict(part="lever carrier (all 16 positions, module + end parts): hub spring pocket and coil / long-leg slot", dim="P18",
             old=pf("pocket D%.1f x %.1f; slot %.0f deg, faces +%.2f / -%.2f (%.1f wide), short leg on its upper face", (S0["pocket"][0], S0["pocket"][1], S0["slot_deg_lever_frame"], S0["slot_faces"][0], -S0["slot_faces"][1], S0["slot_faces"][0] - S0["slot_faces"][1])),
             new=pf("pocket D%.1f x %.1f; slot %.0f deg, faces +%.2f / -%.2f (%.1f wide: the free coil OD %.1f passes with %.2f per side); long leg in the slot over %.1f..%.1f deg with >= %.2f to the faces",
                    (P["spring_pocket"][0], P["spring_pocket"][1], P["spring_slot"][0], P["spring_slot"][1], P["spring_slot"][2], P["spring_slot"][1] + P["spring_slot"][2], P["spring_ID"] + 2 * P["spring_d"],
                     IN["per"]["coil|A"][0], R["r42"]["spring_b_range"][0], R["r42"]["spring_b_range"][1], SL["margin"])),
             why="MISUMI coil OD 6.0 (ID 5 + 2 x 0.5): pocket radial clearance 0.30, the coil drops in through the slot"),
        dict(part="lever carrier (all 16 positions): NEW short-leg groove through the hub wall of the pocket section (x +-%.1f)" % (P["spring_pocket"][1] / 2), dim="P18",
             old="none (the short leg lay on the slot's upper face, bent 5.7 deg)",
             new=pf("band %.2f..%.2f from the axis along %.2f deg (lever frame), from ss %.1f along the leg direction %.2f deg out through the hub (inner face leaves it at y%.2f z%.2f, bearing face at y%.2f z%.2f); "
                    "bearing face = outer (rm + d/2 = %.2f); web underside cut %.2f deep over the pocket width; the pocket section is two pieces (A web side, B lower ring)",
                    (NT["nn"][0], NT["nn"][1], NT["alpha_s"], NT["ss"][0], NT["leg_dir"], NT["exit_inner"][0], NT["exit_inner"][1], NT["exit_bearing"][0], NT["exit_bearing"][1], NT["nn"][1], NT["web_cut_depth"])),
             why=pf("the catalogue part's swept angle (%.0f deg) puts its short leg at %.2f deg, %.0f deg from the r4.4 short-leg seat (slot + 90 deg): it cannot leave through the slot; the leg is straight (tip y%.2f z%.2f, r %.2f) and bears %.2f on the face, tip %.2f inside its end; "
                    "slid in along the slot axis the leg drops into the groove (short leg to the web side min %.2f, %.2f after FDM; inner clearance 0.5 would leave %.2f); ABUSE hub / web at the groove %.2f MPa in layer (x Kt 2), piece B %.2f MPa across layers",
                    (P["spring_swept_free"], NT["alpha_s"], abs(((NT["alpha_s"] - (P["spring_slot"][0] + 90.0) + 180.0) % 360.0) - 180.0), NT["T"][0], NT["T"][1], NT["tip_r"], NT["leg_on_face"], SL["short_tip_to_face_end"], IN["short_A"][0], IN["short_A"][0] - 0.3, R["r45"]["insert_lo"][0.5], HN["section"]["sigma_kt"], HN["tau_B"]))),
        dict(part="frame (module 12, end parts 3 + 1): torsion-spring groove and boss on the rear wall", dim="P18, S28",
             old=pf("boss %.1f wide; groove %.1f wide x %.1f deep from the boss face (bottom y%.1f), z%.0f~%.0f", (S0["boss"][0], S0["groove"][3], S0["groove"][4], S0["groove"][0] + S0["groove"][4], S0["groove"][1], S0["groove"][2])),
             new=pf("boss %.1f wide; groove %.1f wide x %.1f deep (bottom y%.1f: %.1f into the rear wall, %.1f of wall left behind it), z%.0f~%.0f", (P["spring_boss"][0], sg[3], sg[4], sg[0] + sg[4], sg[0] + sg[4] - P["rear_wall"][0], P["rear_wall"][1] - sg[0] - sg[4], sg[1], sg[2])),
             why=pf("the long leg leaves the coil end at x +0.8 (coil %.2f long in the %.1f pocket) and rises straight into the groove (r4.4: kinked from the coil end to a 1.2 groove); 3.2 deep keeps a keyless lever's unloaded leg %.2f inside the mouth (r4.4 1.25)",
                    ((P["spring_n"] + 1) * P["spring_d"], P["spring_pocket"][1], R["leg_in_groove_drop"]))),
        dict(part="stage-0 kit C06a / C06b (test 8 spring rig) and test 13", dim="stage0_geometry.json",
             old="C06a groove 1.2 x to y209.8 (one-sided ledge at the leg plane), C06b hub replica: pocket D6.1, slot 6.0, short leg on the slot face",
             new=pf("C06a groove %.1f wide centred on the coil, bottom y%.1f (boss %.1f); C06b hub replica from model_v4.hub_pocket_poly: pocket D%.1f, slot %.1f, short-leg groove; test 8 pass rest %.2f / bottom %.2f N mm +-15 %%, test 13 = the insertion into the short-leg groove",
                    (sg[3], sg[0] + sg[4], P["spring_boss"][0], P["spring_pocket"][0], P["spring_slot"][1] + P["spring_slot"][2], sp["states"]["rest"]["T"], sp["states"]["bottom"]["T"])),
             why="the rig must reproduce the new pocket, slot, short-leg groove and rear-wall groove"),
    ]
    return out


def mtr(x):
    """r4.5 circuit 2nd: short Korean words for a sweep record in a dims note."""
    for a_, b_ in (("(right module)", "(오른쪽 모듈)"), ("(left module)", "(왼쪽 모듈)"), ("key ", "건반 "), ("tail wall R", "꼬리 오른 옆벽"), ("tail wall L", "꼬리 왼 옆벽"),
                   ("magnet boss rib", "자석 보스 리브"), ("magnet boss", "자석 보스"), (" ff", " ff 최대"), (" dip_rigid", " 강체 바닥"), (" dip", " 바닥"), (" over", " 복귀 넘침"), (" rest", " 쉼")):
        x = x.replace(a_, b_)
    return x


def changes_r45c(P, g, R, ep):
    """r4.5 circuit 2nd cross-check (hardware/pcb README '2차 요청' 8-11): every geometry / data change (old = geometry.r4_5c.json,
    the r4.5 fix round as published)."""
    L8 = R["c45"]["ledge"]
    lx0, lx1, px1, zl0, zl1 = P["sb_ledge"]
    (fy0, fy1), (ry0, ry1) = P["sb_ledge_y"]
    GS = R["ghost_summary"]
    ef = R["c45"]["el_floor"]["now"]["left"]
    return [
        dict(part="frame (module): sensor-bar right ledge (v3 P112) - fixed prisms 'sensor-bar ledge lip / post front / rear', plan, sweep", dim="P36",
             old="not in the r4 geometry (v3 P112 x161.5-164.5 x y59.0-63.4 / y70.6-77.5, underside z13.6; the bar's right end was held by nothing)",
             new=pf("two inverted L pieces y%.1f-%.1f / y%.1f-%.1f: lip x%.1f-%.1f z%.1f-%.1f (underside = white bar top), post x%.1f-%.1f z%.1f-%.1f; over the bar end x%.1f by %.1f, post %.1f from the bar end; "
                    "closest moving part %.2f (%s %s %s), next module %.2f, ER %.2f", (fy0, fy1, ry0, ry1, lx0, lx1, zl0, zl1, lx1, px1, P["z_floor"][1], zl1, L8["bar_end"], L8["over_bar"], L8["post_to_bar"],
                                                                                    L8["sweep"]["d"], L8["sweep"]["a"], L8["sweep"]["part_a"], L8["sweep"]["pose_a"], L8["neighbour_module"][0], L8["end_part_ER"][0])),
             why="circuit 2nd request 8: BRD-02 drew the ledge dashed pending W1; the v3 frame mass (175 g) the model starts from already holds it, only the export had lost it. "
                 "x end 164.3 instead of v3 164.5 = the r4 seam inset 0.2 (fins, top plate). Thickness z13.6-15.1 chosen for >= 1.3 to key B at its ff pose; the lip stays off the B lead rows"),
        dict(part="end part left (EL): floor", dim="A02",
             old="floor 0.2-46.25 + 'in front of / behind the board hatch' 46.25-46.8 - the module's control-board hatch cut (x46.25-118.25 y144.5-196.5) leaked in: gap x46.25-46.8 x y144.5-196.5",
             new=pf("one floor piece %s, no hole (the hatch is a module feature only; end_fixed_prisms takes the module floor without board_hatch)", "; ".join("x%.2f-%.2f y%.1f-%.1f" % q_ for q_ in ef["pieces"])),
             why="circuit 2nd request 11: end_fixed_prisms clipped the module's hatched floor to the end part's x range"),
        dict(part="dynamics / firmware ghost filter (U6): model rule and long runs", dim="DESIGN 0.1, 0.2, 7.4; metrics ghost_*",
             old="gfilter: re-arm within 250 ms of the note-on, re-press speed ratio; held strikes stopped at 320 ms (v_desc 0.00 = no descent seen yet); text said 're-press within 250 ms'",
             new=pf("same rule as SCH-03 note 9 + the re-press bound: first re-press judged only if it lands within %.0f ms of the note-on; every held strike that re-arms is run on to %.0f ms after the note-on: "
                    "%d of %d land again (latest %.0f ms), all stop at their float point by %.0f ms (float %.0f-%.0f %%, creep <= %.4f m/s at the magnet)",
                    (P["ghost_rep_max"], P["ghost_long"], len(GS["relanded"]), len(GS["armed"]), GS["reland_max"], GS["settle_max"], 100 * GS["frac_end"][0], 100 * GS["frac_end"][1], GS["creep_max"])),
             why="circuit 2nd request 9: the text and the model used different windows, and ghost_reland was never inside the 320 ms runs"),
        dict(part="DESIGN 11 step 6 / 10 step 5 / 1d-2 row 7 text: landings of a lever whose key is out", dim="DESIGN 11",
             old="D#, F#, G, G# 'on the board top (z10.6, 16.8-24.0 deg)', E/F 13.3 deg",
             new="; ".join(pf("%s %.2f deg (%s)", (k_, v_["deg"], ("hung control-board boss, " + ("screw" if "screw" in v_["onto"] else "pin")) if v_["onto"].startswith("control-board boss")
                                                      else ("CD74HC4067 module top z20" if "4067" in v_["onto"] else ("board top z10.6" if v_["onto"] == "control board" else v_["onto"]))))
                           for k_, v_ in R["c45"]["drop"].items() if k_ in ("D#", "E", "F", "F#", "G", "G#")),
             why="circuit 2nd request 10: D# / G# land on the hung control-board bosses (16.75 deg), not on the board top - geometry and drawing 12 already had it"),
    ]


def changes_r45b(P, g, R, ep):
    """r4.5 fix round (verifiers of r4.4 fix 2b and of the r4.5 spring): every geometry / data change (old = geometry.r4_5a.json =
    r4.5 as published, work_r45b/metrics.r4_5a.json)."""
    D0 = os.path.dirname(os.path.abspath(__file__))
    G0 = json.load(open(os.path.join(D0, "geometry.r4_5a.json")))
    M0 = json.load(open(os.path.join(D0, "work_r45b", "metrics.r4_5a.json")))
    S0 = G0["solved"]["spring"]
    N0 = S0["short_leg_groove"]
    SL = R["r42"]["spring_slot"]
    NT = SL["notch"]
    IN = R["r45"]["insert"]
    HN = R["r45"]["hub"]["abuse"]
    sp, sp0 = R["spring"], M0["spring"]
    FL = sp["float"]
    f45 = FL["r4.5 as built (short leg 2.5 on one face), mu 0.0"]
    frot = [v for k, v in FL.items() if k.startswith("notch rotated") and k.endswith("mu 0.3")][0]
    f5 = [v for k, v in FL.items() if k.startswith("short leg 5.0") and k.endswith("mu 0.3")][0]
    CP = sp["capture"]
    KX = R["assembly"]["keyless_x"]
    KR = R["keel_rail"]
    kr = KR["rail"]
    ld0 = M0["lever_drop"]
    sg = P["spring_groove"]
    out = [
        dict(part="torsion assist spring (bought MISUMI %s): short leg cut length" % P["spring_cat"]["part"], dim="D05, parts list",
             old=pf("short leg %.1f (straight, bears on ONE groove face); k_t %.3f N mm/rad, free %.2f deg; rest / bottom / hand 25 deg %.2f / %.2f / %.2f N mm (hand %.0f %% of the catalogue 55-deg torque)",
                    (2.5, sp0["kt"], sp0["free_deg"], sp0["states"]["rest"]["T"], sp0["states"]["bottom"]["T"], sp0["states"]["hand 25 deg"]["T"], 100 * sp0["hand_over_cat"])),
             new=pf("short leg %.1f (straight, CAPTURED in its groove); k_t %.3f N mm/rad (leg bending of the captured leg: l = 2 s_E + l_s), free %.2f deg; rest / bottom / hand %.2f / %.2f / %.2f N mm (hand %.0f %%)",
                    (P["spring_short_leg"], P["spring_kt"], P["spring_free_deg"], sp["states"]["rest"]["T"], sp["states"]["bottom"]["T"], sp["states"]["hand 25 deg"]["T"], 100 * sp["hand_over_cat"])),
             why=pf("verifier spring major, re-checked (model_v4.spring_pose 'face'): the one-face short leg lets the net leg force push the coil %.2f onto the D4 rod (toward %.0f deg), the leg lifts off and the spring unwinds %.1f deg: "
                    "rest %.2f N mm (-%.0f %%), D DW %.1f, lip y0 %.1f (< 47), C# DW %.1f (< 47), C# UW at the bottom x2 friction %.1f (< 20) - three PLAY fails; notch rotated %.1f deg restores the torque but the coil rubs on the "
                    "fixed rod with %.1f N (mu 0.3: C# UW bottom x2 %.1f); short leg 5 + rotation still rubs (%.1f); the captured leg carries the couple itself: coil %.2f / %.2f off the rod (rest / hand), no hysteresis",
                    (f45["shift"], f45["dir"], f45["unwind"], f45["T_rest"], 100 * (1 - f45["T_rest"] / P["spring_T0"]), f45["keys"]["D"]["DW"], f45["keys"]["D"]["DW_lip"], f45["keys"]["C#"]["DW"], f45["keys"]["C#"]["UW_bottom_2f"],
                     frot["rot"], frot["N_bottom"], frot["keys"]["C#"]["UW_bottom_2f"], f5["keys"]["C#"]["UW_bottom_2f"], CP["gap_rest"], CP["gap_hand"]))),
        dict(part="lever carrier (all 16 positions, module + end parts): short-leg groove -> captured groove", dim="P18",
             old=pf("groove band %.2f..%.2f from the axis along %.2f deg (inner clearance 0.8 for the insertion along the %.0f deg slot); leg bears on the outer face only; web cut %.2f",
                    (N0["nn"][0], N0["nn"][1], N0["alpha_s"], S0["slot_deg_lever_frame"], N0["web_cut_depth"])),
             new=pf("groove %.2f wide (play %.2f) along %.2f deg = the loaded leg turned %.2f deg CW, faces %.3f / %.3f from the axis, from ss %.1f in the pocket through the hub wall into the web, blind %.1f past the tip "
                    "(ss %.2f); contacts: leg tip on the outer face (y%.2f z%.2f) + leg on the inner face's pocket edge (y%.2f z%.2f), arm %.2f -> %.2f N at rest, %.2f N at hand 25 deg; web underside cut %.2f",
                    (NT["width"], NT["play"], NT["band_deg"], NT["theta_c"], NT["nn"][0], NT["nn"][1], NT["ss"][0], P["spring_notch"][2], NT["ss"][1], NT["O"][0], NT["O"][1], NT["E"][0], NT["E"][1], NT["arm"],
                     CP["F_couple_rest"], CP["F_couple_hand"], NT["web_cut_depth"])),
             why=pf("coil float (above); groove printed dp: %s; 0.70 = printable slot (2 x 0.4 lines), the 0.5 wire still goes in at -0.15",
                    "; ".join(pf("%+.2f -> rest %.2f N mm, rod gap %.2f", (float(k), v["T0"], v["gap_left"])) for k, v in sp["capture_tol"].items() if k in ("-0.15", "+0.15", "+0.30")))),
        dict(part="lever carrier (all 16 positions): insertion slot and long-leg window of the pocket section", dim="P18",
             old=pf("one parallel slot %.0f deg, faces +%.2f / -%.2f: the coil in, the long leg out", (S0["slot_deg_lever_frame"], S0["slot_faces"][0], -S0["slot_faces"][1])),
             new=pf("insertion slot along the captured leg %.2f deg, faces +-%.2f (the coil comes in tip-first along its short leg); the rear opening runs from that slot's face round to the long-leg window's upper face (%.0f deg, +%.1f): "
                    "long leg in it over %.1f..%.1f deg with >= %.2f (+ wire radius + 0.2); pocket section = piece A (web side, both leg contacts) + B (lower ring)",
                    (NT["slot_deg"], P["spring_slot"][2], P["spring_window"][0], P["spring_window"][1], R["r42"]["spring_b_range"][0], R["r42"]["spring_b_range"][1], SL["margin"])),
             why=pf("a captured leg cannot drop into its groove from a slot at 35 deg: the spring goes in along the leg; insertion path to the faces %.3f (%.3f / %.3f with the groove 0.10 / 0.15 narrower); "
                    "hub / web at the groove ABUSE %.2f MPa in layer (x Kt 2), PLAY %.2f", (IN["short_A"][0], R["r45"]["insert_lo"][-0.1], R["r45"]["insert_lo"][-0.15], HN["section"]["sigma_kt"], R["r45"]["hub"]["play"]["section"]["sigma_kt"]))),
        dict(part="frame (module 12, end parts 3 + 1): rear-wall spring-groove boss and groove centred on the long leg", dim="P18",
             old=pf("boss %.1f and groove %.1f centred on the lever (x +-%.1f)", (S0["boss"][0], S0["groove"][3], S0["boss"][0] / 2)),
             new=pf("boss and groove centred on lever x %+.1f (the long leg leaves the coil's +x end there); groove + its %.1f x 45 deg entry chamfer exported as female cut parts ('spring groove cut', 'spring groove entry chamfer')",
                    (P["spring_groove_dx"], P["spring_lead_in"])),
             why=pf("verifier spring minor: with the coil sliding %.3f in the pocket and the lever floating %.3f, the leg can sit %.2f off its nominal x; the groove catches %.2f about its centre: margin %.2f (centred on the lever: %.2f)",
                    (KX["coil_axial"], KX["lever_float"], KX["x_off"], KX["catch"], KX["margin"], KX["margin_r45"]))),
        dict(part="frame (module): F|F# fin keel to the balance rail's rear face + the F|F# fin's front edge", dim="P12, S29 / plate FE",
             old=pf("keel y%.1f-%.1f z%.0f-18, F|F# fin from y%.0f (clamped to a rigid rail in the FE: chord seat %.1f N/mm)", (P["fin_keel"][0], P["fin_y"][0], P["fin_keel"][1], P["fin_y"][0], M0["seat"]["k_chord"] if "seat" in M0 and "k_chord" in M0["seat"] else 494.2)),
             new=pf("keel y%.1f-%.1f z%.0f-%.1f; the F|F# fin (floor underside z%.0f to the plate) now starts at y%.1f (was %.0f); FE root on the rail spring (rail + floor strip beam over the fin lines, kv %.0f N/mm, kr %.0f N mm/rad, face %.0f N/mm): "
                    "chord seat %.1f N/mm (r4.4 keel z18 / y152 %.1f, rigid rail %.1f); first-module dead load 6 x 60 N: E/F seats %.3f mm (pass <= %.3f)",
                    (P["fin_keel"][0], m.keel_front(P), P["fin_keel"][1], P["fin_keel"][2], P["z_floor"][0], m.keel_front(P), P["fin_y"][0], kr.get("kv", 0.0), kr.get("kr", 0.0), kr.get("k_face", 0.0), KR["k_chord"], KR["k_chord_keel18"],
                     KR["k_chord_rigid"], KR["dead"]["EF_max"] or -1, KR["dead"]["limit"])),
             why=pf("verifier fixes minor: the keel root is a free edge of the floor hatch, the rail is not a rigid ground (stage-0 test 3 cannot see it); with the rail beam the r4.4 keel gives %.1f < 460. "
                    "The first fix-2 pass raised the keel to z21 (%.1f N/mm) but that left %.2f to %s (%s, %s pose: the key's right tail wall is over the F|F# fin line); the keel stays at z%.1f "
                    "(to %s %s %.2f) and the fin itself comes forward to y%.1f (%.2f to %s %s, %s pose), so the keel is %.1f long instead of %.1f: %.1f N/mm; "
                    "bounds: rail clamped at the hatch edges %.1f, simply supported between the neighbouring fin lines only (no continuity, no EVA) %.1f -> the stage-0 test 21 measures it",
                    (KR["k_chord_keel18"], KR["k_chord_keel21"], (KR.get("keel21_clear") or {}).get("d", -1.0), (KR.get("keel21_clear") or {}).get("key", "?"), (KR.get("keel21_clear") or {}).get("part", "?"),
                     (KR.get("keel21_clear") or {}).get("pose", "?"), P["fin_keel"][2], (KR.get("keel_clear") or {}).get("key", "?"), (KR.get("keel_clear") or {}).get("part", "?"), (KR.get("keel_clear") or {}).get("d", -1.0),
                     m.keel_front(P), (KR.get("fin_clear") or {}).get("d", -1.0), (KR.get("fin_clear") or {}).get("key", "?"), (KR.get("fin_clear") or {}).get("part", "?"), (KR.get("fin_clear") or {}).get("pose", "?"),
                     m.keel_front(P) - P["fin_keel"][0], P["fin_y"][0] - P["fin_keel"][0], KR["k_chord"], KR["k_chord_hatch"], KR["k_chord_fins_span"]))),
        dict(part="stage-0 kit C06a / C06b (test 8), C17a and tests 13, 21", dim="stage0_geometry.json",
             old="C06a groove on the coil centre (x2.7); C06b hub replica with the 35 deg slot and the one-face short-leg groove, disk from x4.2; C06 rod 16",
             new=pf("C06a groove on the leg (x%.1f); C06b = model_v4.hub_pocket_poly (captured groove %.2f, insertion slot, window) on a 2.0 hub spacer (disk from x6.2, 0.5 off the boss); C06 rod 18; test 8 one-sided groove-bottom limit; "
                    "test 21 = first-module dead load (6 x 60 N, E/F <= %.2f mm) in the service direction: module on the new C17a comb (3 high, teeth under the fin lines + a bar under "
                    "the rear wall; nothing under the rail between the fin lines, hatch open), load from above (fix 3); C06b hub spacer D%.1f (fix 3: watertight STL)",
                    (2.7 + P["spring_groove_dx"], NT["width"], KR["dead"]["limit"], 2 * P["hub_R"] - 0.1)),
             why="the rig must reproduce the captured groove; the groove boss (to x5.7) would reach the r4.5 disk face (x4.2). Fix 3 (verifier major): in service the pads push "
                 "the plate up and the keel lifts the rail; loading from above on the floor EVA only measured the rigid-rail case, so even a failing rail passed; "
                 "the model is linear, so the comb support reproduces the service case. The C06b spacer at the hub radius shared a vertex with the pocket section"),
        dict(part="metrics / DESIGN text: lever drop (key out, lever let go)", dim="metrics lever_drop",
             old="; ".join(pf("%s %.2f deg onto %s", (k_, ld0[k_]["drop_deg"], (ld0[k_]["onto"] or "-")[:34])) for k_ in ("D#", "E", "F", "F#", "G", "G#") if k_ in ld0),
             new="; ".join(pf("%s %.2f deg onto %s", (k_, R["lever_drop"][k_]["drop_deg"], (R["lever_drop"][k_]["onto"] or "-").replace("board part: ", "")[:34])) for k_ in ("D#", "E", "F", "F#", "G", "G#")),
             why="drafter: metrics lever_drop used the generic z20 envelope while drawing 12 used circuit_r44.drop; now both are the real landings (lever_drop(actual=True))"),
    ]
    return out


def changes_c44(P, g, R):
    """r4.4 step 2 (circuit session cross-check, hardware/pcb README 'W1 기구 쪽에 요청한 것'): every geometry change
    (old = geometry.r4_4_pre_circuit.json = fix 1 of r4.4)."""
    C = R["c44"]
    so = C["standoffs"]
    E = C["ends"]
    rq = C["ribbon"]
    ux0, ux1 = m.ribbon_x_under_board(P)
    rows = [
        dict(part="control-board parts (circuit BRD-01 on the Zero's 2.54 lattice)", dim="P27",
             old="Zero x75.0~93.0; receptacle y188.2~195.5; 4067 x53.3~71.1 y152.4~193.0; J301 x61.59~79.37 y148.59/151.13 on top, 16-core ribbon on top (z13) centred x70.48; J302 x95.25~107.95 y193.04",
             new=pf("Zero x%.2f~%.2f; receptacle y%.1f~%.1f (1.3 proud of the edge); 4067 x%.2f~%.2f y%.1f~%.2f; J301 x%.2f~%.2f y%.2f/%.2f soldered from the underside (top joints <= z%.1f); ribbon under the board z%.0f~%.0f x%.2f~%.2f (centred x%.2f in the lane, last %.0f mm %+.2f to J301); J302 x%.2f~%.2f y%.2f", (P["zero_xy"][0], P["zero_xy"][1], P["usb_rcpt"][2], P["usb_rcpt"][3], P["mux_xy"][0], P["mux_xy"][1], P["mux_xy"][2], P["mux_xy"][3], P["ribbon_pads"][0], P["ribbon_pads"][1],
                    P["ribbon_pads"][2], P["ribbon_pads"][3], P["ribbon_z"], P["ribbon_under_z"][0], P["ribbon_under_z"][1], ux0, ux1, P["ribbon_xc"], P["ribbon_j301"][1], rq["shift"],
                    P["ext_pads"][0], P["ext_pads"][1], P["ext_pads"][2])),
             why=pf("circuit 1 (delta 15): receptacle centred on the shelf slot (x84.00); J301 on the underside so the ribbon never folds within 1.0 of the rail (verify round-1 geometry 3). "
                 "Named parts to the frame >= %.2f; ribbon lane margins %.2f / %.2f; ribbon under the board to the F|F# fin foot %.2f", (R["clear"]["fixed_fixed"]["board_parts_min"][0], rq["lane_margins"][0], rq["lane_margins"][1], rq["to_fin"]))),
        dict(part="USB-C plug envelope (purchased cable)", dim="P24", old="face y195.5, overmould y195.5~220.5", new=pf("face y%.1f, overmould y%.1f~%.1f (x, z unchanged)", (P["usb_y"][0], P["usb_y"][0], P["usb_y"][1])),
             why=pf("circuit 2: the receptacle stands 1.0~1.5 past the Zero's edge. Slot %.2f / %.2f over the whole shelf, rear-wall opening x %.2f / top %.2f, cable passage %.1f spare after a 25 bend", (C["usb"]["slot_margins"][0], C["usb"]["slot_margins"][1], min(C["usb"]["wall_x_margins"]), C["usb"]["wall_z_margin"], C["usb"]["passage_spare"]))),
        dict(part="frame (module): 4 control-board stand-offs", dim="P35 (new)", old="none in geometry (v3 P114 spots (49.75,148)(114.75,148)(49.75,193)(114.75,193) in text only)",
             new=pf("D%.0f x z%.0f~%.0f at %s; screw bosses bore D%.1f to z%.1f + M3x6 (v3.2 L35 ISO 7380 button head; head envelope D%.1f x %.1f); locating pins D%.1f to z%.1f", (P["standoff_d"], P["z_floor"][1], P["board_z"][0], ", ".join(pf("(%.1f,%.1f) %s", (q["x"], q["y"], q["kind"])) for q in so), P["standoff_bore"][0], P["standoff_bore"][1],
                    P["board_screw"][0], P["board_screw"][1], P["board_pin"][0], P["board_z"][1] + P["board_pin"][1])),
             why=pf("circuit 3 (delta 14): head (L35 D%.1f) to the rail's rear face %.2f, to the shelf ribs %.2f (%.2f on the rib axis; v3 spots with D5.5: 0.75 / 1.05); nearest BRD-01 part %.2f", (P["board_screw"][0], min(q["rail_top"] for q in so if q["kind"] == "screw"), min(q["rib_top"] for q in so if q["kind"] == "screw"),
                    min(q["rib_top_axis"] for q in so if q["kind"] == "screw" and q["rib_top_axis"] is not None), min(q["part_min"][0] for q in so)))),
        dict(part="frame (module): v3 sensor-board support + the sensor board (now in the model)", dim="P36 (new)", old="not in geometry (v3 P111 post, P113 ribs, rear-rib gap x60~82)",
             new=pf("post x%.1f~%.1f, front rib y%.1f~%.1f / rear rib y%.1f~%.1f over x%.1f~%.1f, top z%.1f; rear-rib gap x%.0f~%.0f; SB x%.1f~%.1f y%.2f~%.2f z%.1f~%.1f", ((P["sb_post"][0], P["sb_post"][1], P["sb_rib_front"][0], P["sb_rib_front"][1], P["sb_rib_rear"][0], P["sb_rib_rear"][1], P["sb_rib_x"][0], P["sb_rib_x"][1], P["sb_board"][4],
                     P["sb_rib_gap"][0], P["sb_rib_gap"][1]) + tuple(P["sb_board"]))),
             why=pf("circuit 5: the 16-core ribbon x%.2f~%.2f had %.2f on the left in the v3 gap; now %.2f / %.2f (= the lane)", (P["ribbon_xc"] - 10.16, P["ribbon_xc"] + 10.16, rq["sb_gap_margins_r43"][0], rq["sb_gap_margins"][0], rq["sb_gap_margins"][1]))),
    ]
    for side, nm, xn in (("left", "EL", "X401"), ("right", "ER", "X411")):
        q = E[side]
        rows.append(dict(part=pf("end part %s: sensor-board support, lead lane, rear-wall notch", side), dim="A02" if side == "left" else "A03",
                         old=pf("sensor bar only; no board support, no rear-rib gap, no way out for W%s", ("401" if side == "left" else "411")),
                         new=pf("%s board x%.1f~%.1f; post x%.1f~%.1f + ribs x%.1f~%.1f, rear-rib gap x%.0f~%.0f; balance rail lane x%s~%s z%.0f~%.0f; rear-wall notch x%s~%s z%.0f~%.0f", (nm, q["board"][0], q["board"][1], P["sb_post"][0], P["sb_post"][1], q["rib_x"][0], q["rib_x"][1], q["gap"][0], q["gap"][1], m.fh(q["lane"][0]), m.fh(q["lane"][1]),
                                q["lane_z"][0], q["lane_z"][1], m.fh(q["lane"][0]), m.fh(q["lane"][1]), q["notch_z"][0], q["notch_z"][1])),
                         why=pf("circuit 4: lead pads %.2f / %.2f and underside wires %.2f / %.2f inside the gap; %d-core lead %.2f + 1.3 each side, fanned in by y%.2f; lead path to floor parts >= %.2f%s; board inside the bar", (q["pad_margins"][0], q["pad_margins"][1], q["wire_margins"][0], q["wire_margins"][1], q["cores"], q["lead_w"], q["fan_y"], q["path_min"][0],
                                (pf("; passes the A#0 tab base with %.2f", q["tab_gap"])) if q["tab_gap"] is not None else (pf("; C8 pin has %.1f of rail under it", q["pins_over_lane"][0][2]) if q["pins_over_lane"] else "")))))
    rows.append(dict(part="control board keep-out (text)", dim="P23", old="keep-out x81.22~85.42 y145.5~173.2; the Zero overhang not stated",
                     new=pf("keep-out unchanged (stripboard pins / pads / traces); P23 records the RP2040-Zero PCB overhang x%.2f~%.2f y%.1f~%.1f (z%.1f~%.1f, no pins / pads / traces)", (C["zero"]["overhang"][0], C["zero"]["overhang"][1], C["zero"]["overhang"][2], C["zero"]["overhang"][3], C["zero"]["pcb_z"][0], C["zero"]["pcb_z"][1])),
                     why=pf("circuit 6: Zero front edge to the fin foot %.2f, its top parts to the hung fin %.2f", (C["zero"]["foot_gap"], C["zero"]["to_hung_fin"]))))
    return rows


def changes_r43(P, g, R):
    """r4 fix round 3 (r4.2 -> r4.3, circuit session BRD-01 against r4.1): every geometry change (old = geometry.r4_2.json)."""
    lay = g["lay"]
    fbx = [f for f in lay["fins"] if P["board_x"][0] < 0.5 * (f[0] + f[1]) < P["board_x"][1]][0]
    su = m.usb_slot(P)
    Q = R["r43"]
    LD = Q["land"]
    zh = P["comp_zmax"] + 1.5
    return [
        dict(part="USB-C plug envelope (purchased cable, module)", dim="P24", old="x77.75~90.25, y195.5~220.5, z9.45~16.95 (v3: RP2040-Zero soldered flat, USB-C centre z13.2)",
             new=pf("x%.2f~%.2f, y%.1f~%.1f, z%.1f~%.1f (RP2040-Zero on pin headers +1.3, USB-C centre z%.1f)", (P["usb_x"] + P["usb_y"] + tuple(P["usb_z"]) + (0.5 * (P["usb_z"][0] + P["usb_z"][1]),))),
             why="circuit 1: chips, crystal and LDO under the Zero; it cannot lie flat"),
        dict(part="RP2040-Zero / USB-C receptacle zone (module)", dim="P27 (new)", old="'RP2040-Zero + USB-C receptacle (<= z15.5)' over the whole board width x47.25~117.25, y190~195.5",
             new=pf("RP2040-Zero x%.1f~%.1f y%.1f~%.1f on pin headers (PCB z%.1f~%.1f, top parts <= z%.1f, pin tips trimmed); receptacle x%.2f~%.2f y%.1f~%.1f z%.1f~%.1f", (P["zero_xy"] + P["zero_z"] + P["usb_rcpt"])),
             why="circuit 1 + 2: the Zero sits at x75~93 y172~195.5 (BRD-01)"),
        dict(part="control-board component envelope (module)", dim="P27 (new), P23",
             old="<= z20 over y145.5~190 (fin keep-out +-1.0 = x81.42~85.22 to y173.0), <= z15.5 over y190~195.5",
             new=pf("<= z%.0f over y%.1f~%.1f (keep-out +-%.1f = x%.2f~%.2f to y%.1f), <= z%.1f over y%.1f~%.1f; named BRD-01 parts: 4067 x%.1f~%.1f y%.1f~%.1f <= z%.0f, J301 2x8 x%.2f~%.2f y%.2f/%.2f + %d-core ribbon, J302 1x6 x%.2f~%.2f y%.2f", ((P["comp_zmax"], P["comp_front_y"], P["comp_rear"][0], P["board_slot_keepout"], fbx[0] - P["board_slot_keepout"], fbx[1] + P["board_slot_keepout"],
                     P["board_slot_y1"] + P["board_slot_keepout"], P["comp_rear"][1], P["comp_rear"][0], P["board_y"][1]) + P["mux_xy"] + (P["comp_zmax"],) + P["ribbon_pads"] + (P["ribbon_cores"],) + P["ext_pads"])),
             why="circuit 2: the 4067 (to y193) and the Zero reach behind y190; the envelope keeps 1.3 to the rail (front), the shelf / ribs (rear) and the fin foot (keep-out; r4.1's 1.0 left 0.8 after FDM)"),
        dict(part="frame: rear shelf (module)", dim="P19", old="x75.6~92.4 between ribs 75 / 93 only 1.5 thick, underside z18.55 (0.25 above the raised plug)",
             new=pf("open slot x%.2f~%.2f over the full depth y%.1f~%.1f (plug -+ %.1f); 2.0 thick on both sides", (su + tuple(P["shelf_y"]) + (P["usb_clear"],))),
             why=pf("circuit 1: plug top z%.1f; plug to the slot edges %.2f (1.0 after FDM)", (P["usb_z"][1], Q["usb"]["each"]["rear shelf"]))),
        dict(part=pf("frame: F|F# fin (module, x%.2f~%.2f)", tuple(fbx)), dim="P12, S29",
             old="foot y152~171 on the floor through the stripboard slot; y171~196.8 hung from z21.5; y196.8~209 down to the thin shelf (z18.55) over the plug",
             new=pf("foot y%.0f~%.1f; hung from z%.1f from y%.1f all the way to the rear wall y%.0f (%.1f above the plug)", (P["fin_slot_y"][0], P["fin_slot_y"][1], zh, P["fin_slot_y"][1], P["rear_wall"][0], Q["usb"]["each"]["fin"])),
             why=pf("circuit 1 (fin stood on the cut shelf) + circuit 2 (foot rear face 1.3 from the Zero's front edge y%.1f; r4.2 1.0). Plate FE: fin hung over the tunnel, weakest seat unchanged %.0f N/mm", (P["zero_xy"][2], R["seat"]["k_min"]))),
        dict(part="control board (v3 stripboard): slot / keep-out", dim="P23", old="slot x81.92~84.72 y145.5~172.0; parts / wires / ribbon header out of x81.42~85.22, y145.5~173.0",
             new=pf("slot unchanged (x%.2f~%.2f y%.1f~%.1f); keep-out x%.2f~%.2f, y%.1f~%.1f", (fbx[0] - P["board_slot_clear"], fbx[1] + P["board_slot_clear"], P["board_y"][0], P["board_slot_y1"],
                                                                                  fbx[0] - P["board_slot_keepout"], fbx[1] + P["board_slot_keepout"], P["board_y"][0], P["board_slot_y1"] + P["board_slot_keepout"])),
             why="1.3 from the 0.1-inset fin foot; every BRD-01 part is already outside (no part moves)"),
        dict(part="frame: balance rail ribbon lane (module)", dim="P20", old="x60~82 under the rail (z5~10)", new=pf("x%.1f~%.1f (z5~10)", tuple(P["ribbon_x"])),
             why=pf("circuit 3: the ribbon uses all 16 cores (%.2f wide, centred x%.2f on J301): margins %.2f / %.2f (r4.2 lane: 0.32 / 1.36)", (Q["ribbon"]["width"], 0.5 * (P["ribbon_pads"][0] + P["ribbon_pads"][1]), Q["ribbon"]["left"], Q["ribbon"]["right"]))),
        dict(part="keys F and F#: rest-felt landing (consequence, no part change)", dim="P28", old="full 8.0 width on the shelf",
             new=", ".join(pf("%s x%.2f~%.2f (%.0f %%)", (k_, v_["segs"][0][0], v_["segs"][0][1], 100 * v_["frac"])) for k_, v_ in LD.items() if v_["frac"] < 1 - 1e-9),
             why=pf("the slot edges; dynamics re-run with the rest-felt contact scaled to %.0f %% (0.2 table)", (100 * Q["land_min"]))),
    ]


def changes_r42(P, g, R):
    """r4 fix round 2 (r4.1 -> r4.2, drafter's findings): every geometry change, part / dimension id / old -> new (old = geometry.r4_1.json)."""
    zs, t = g["z_seat"], P["pad_bar_t"]
    yj = g["y_bar_joggle"]
    G2 = R["r42"]["gaps_module"]
    SL = R["r42"]["spring_slot"]
    ew = "; ".join(pf("%s %.3f~%.3f (module %.3f~%.3f)", ((nm,) + tuple(R["end_parts"][sd]["stat"][nm]["wedge"]) + tuple(R["end_parts"][sd]["stat"][nm]["wedge_module"])))
                   for sd in ("left", "right") for nm in R["end_parts"][sd]["stat"])
    C = [
        dict(part="pad bar (all 6 kinds): joggle", dim="P13, S17", old="top step y169.5, bottom step y168.0 (high front part z67.30~68.80 over y146.5~169.5; plate channel ends y168.0 -> 1.5 x 1.5 overlap, 2.50 mm2 raster)",
             new=pf("top step y%.1f, bottom step y%.1f (front part z%.2f~%.2f over y146.5~%.1f, %.1f in front of the channel end y%.1f; lower part z%.2f~%.2f from y%.1f)", (yj, yj - t, zs, zs + t, yj, P["bar_joggle_clear"], g["y_bar_step"], zs - t, zs, yj - t)),
             why="drafter 1: the bar could not slide in (it overlapped the plate)"),
        dict(part="pad bar (all 6 kinds): length / rear stop", dim="P13, P15", old="y146.5~183.5 (37.0), plate step y183.5 (exported as a 0.5 ramp to y184.0)",
             new=pf("y146.5~%.1f (%.1f), plate step y%.1f exported as a vertical face", (P["pad_bar_y"][1], P["pad_bar_y"][1] - P["pad_bar_y"][0], P["plate_step_y"])),
             why=pf("drafter 3: wedge / pad rear edges (y183.38 white, 183.17 black) were 0.12 / 0.33 from the step face (0.24 / 0.45 to the exported ramp); now wedge %.2f, pad %.2f (to the step or the rail lips)", (G2["pad wedge"][0], G2["up-stop pad"][0]))),
        dict(part="top plate", dim="P15", old="underside z67.30 over y168~183.5, 0.5 mm ramps at the channel end (y167.5~168.0) and at the rear step (y183.5~184.0)",
             new=pf("underside z%.2f over y%.1f~%.1f; both steps vertical faces (y%.1f, y%.1f); thick rear zone z%.2f from y%.1f", (zs, g["y_bar_step"], P["plate_step_y"], g["y_bar_step"], P["plate_step_y"], R["heights"]["plate_rear"], P["plate_step_y"])),
             why=pf("drafter 1 + 3 (pad seat stiffness of the plate FE %.0f -> %.0f N/mm, 6-key chord seat %.0f N/mm)", (1550, R["seat"]["k_min"], R["seat"]["k_chord"]))),
        dict(part="pad-bar rails (8 per module, 2 per end part)", dim="P13", old="y160~183.5, web 1.0 wide z65.60~67.30 (channel zone from z68.80), lip 0.6 wide z65.60~65.80 (0.2 thick) y160~183.5, 0.3 under the bar edge",
             new=pf("web 1.0 wide y%.0f~%.1f down to z%.2f (channel zone y%.0f~%.0f from z%.2f); lip %.1f wide x %.1f thick z%.2f~%.2f over y%.1f~%.1f, %.1f under the bar edge, its top %.1f below the bar", (P["rail_y0"], P["pad_bar_y"][1], zs - P["bar_rail"][1], P["rail_y0"], g["y_bar_step"], zs + t, P["rail_lip"], P["rail_lip_t"], zs - P["bar_rail"][1], zs - t - P["bar_leaf_gap"],
                    P["rail_lip_y0"], P["pad_bar_y"][1], P["rail_lip"] - P["pad_bar_clear"], P["bar_leaf_gap"])),
             why="drafter 2: the 0.2 lip with 0.3 overlap vanishes within +-0.3 FDM; the lips start at y163.5 so the bay-edge levers keep the 15.5 deg service lift"),
        dict(part="pad bar: leaf tongues (2 per bar, printed)", dim="P13", old="'leaf 0.6 x 4 x 8' in text only, not in geometry",
             new=pf("tongue %.1f thick x %.1f wide x %.0f long at each bar edge, y%.0f~%.0f (root at the rear), bump %.1f long resting on the lip (installed tip raised %.1f), cut free by a %.1f slot and the window above it; %.2f N per leaf", (P["bar_leaf"][0], P["bar_leaf"][1], P["bar_leaf"][2], P["bar_leaf_y"][0], P["bar_leaf_y"][1], P["bar_leaf_bump"], P["bar_leaf"][3], P["bar_leaf_slot"], G2["leaf_F"])),
             why="drafter 2: what holds the bar up and against its seat is now geometry (pad bar edge strips / leaf prisms)"),
        dict(part="lever carrier (all): fingernail tab", dim="S13, D08", old="y148.2~149.2, z51.5~53.0 rectangle, 0.37 in front of the R3 corner (loose)",
             new=pf("y148.2 to the R3 arc, z51.5~53.0 (fills the corner above z51.5; one piece with the front wall, distance %.3f)", R["r42"]["tab_core"]),
             why="drafter 4"),
        dict(part="lever carrier (all): hub spring pocket", dim="P18", old="pocket D6.1 x 3.0 closed all round in the R4.3 hub (not in geometry), short-leg hole D0.7 without position",
             new=pf("pocket section x +-1.5 exported as its own outline: slot through the hub wall at %.0f deg (lever frame), faces +%.2f / -%.2f from the axis (coil in, long leg out over %.1f..%.1f deg, min %.2f to the faces); short leg %.1f long bent %.1f deg, its tip on the upper face %.2f inside its end (no hole)", (P["spring_slot"][0], P["spring_slot"][1], P["spring_slot"][2], R["r42"]["spring_b_range"][0], R["r42"]["spring_b_range"][1], SL["margin"], P["spring_short_leg"], SL["short_bend_deg"], SL["short_tip_to_face_end"])),
             why="drafter 5"),
        dict(part="frame rear wall: torsion-spring groove (module 12, end parts 3 + 1)", dim="P18", old="groove z50~58 in the boss z47~plate (the leg passed 3 mm of boss under it)",
             new=pf("groove z%.0f~%.0f, open at the boss underside; the tangent long leg reaches the boss face y207.8 at z%.2f and enters from below", (P["spring_groove"][1], P["spring_groove"][2], SL["leg_z_at_boss_face"])),
             why="drafter 5 (leg drawn tangent to the coil) - found while re-checking it"),
        dict(part="torsion spring (model)", dim="D05, P18", old="long leg radial from the axis to y209.8, z54.82; short leg 'in a hub hole'",
             new=pf("long leg tangent to the coil (rm 2.5) on the rear side, tangent point y%.2f z%.2f, tip centre y%.2f z%.2f; short leg %.1f long (r4.1: 3), tangent, bent %.1f deg", (tuple(R["r42"]["spring_rest"]["long_leg"][0]) + tuple(R["r42"]["spring_rest"]["tip"]) + (P["spring_short_leg"], SL["short_bend_deg"]))),
             why="drafter 5: how the spring is made and fitted"),
        dict(part="end parts: pad wedges", dim="P17, A02, A03", old="identical to the module wedges (A0/B0/C8 0.315~2.719, A#0 1.463~3.494)",
             new="each key's own face (parallel to its own settled 1 N bottom, design gap, as in its dynamics): " + ew, why="drafter 6 (DESIGN 14 asked for it)"),
        dict(part="end parts: sensor bars", dim="A02, A03", old="none in end_parts (parts list counted 2)", new="left x0.5~46.5 (low x19.93~33.93 at A#0), right x0.5~23.0; v3 section", why="drafter 6"),
        dict(part="end parts: spring grooves", dim="P18, S28", old="bosses only, grooves not exported", new="end_parts[side].spring_grooves + plan (left 3, right 1)", why="drafter 6"),
    ]
    return C


def changes_r41(P, g, R):
    """r4 fix round 1 (r4.0 -> r4.1): every geometry change, part / dimension id / old -> new (old = geometry.r4_0.json)."""
    lay = g["lay"]
    fbx = [f for f in lay["fins"] if P["board_x"][0] < 0.5 * (f[0] + f[1]) < P["board_x"][1]][0]
    sb = P["black_skin_step"]
    zs, t = g["z_seat"], P["pad_bar_t"]
    C = [
        dict(part=pf("F|F# fin (module, x%.2f~%.2f)", fbx), dim="P12, S29", old="y152~176 front extension hung from z21.5 (above the board parts)",
             new=pf("y%.0f~%.0f bottom z5.0 (floor) through the stripboard slot; y%.0f~196.8 hung from z21.5; y196.8~209 unchanged", (P["fin_slot_y"] + (P["fin_slot_y"][1],))),
             why=pf("physics major 2: 6-key chord seat D#~G# 196 -> %.0f N/mm", R["seat"]["k_chord"])),
        dict(part="control board (v3 stripboard)", dim="P23", old="x47.25~117.25, y145.5~195.5, no slot",
             new=pf("open slot from the front edge x%.2f~%.2f, y%.1f~%.1f; parts / wires / ribbon header out of x%.2f~%.2f, y%.1f~%.1f", (fbx[0] - P["board_slot_clear"], fbx[1] + P["board_slot_clear"], P["board_y"][0], P["fin_slot_y"][1] + 1.0,
                    fbx[0] - P["board_slot_keepout"], fbx[1] + P["board_slot_keepout"], P["board_y"][0], P["fin_slot_y"][1] + 2.0)),
             why="lets the F|F# fin reach the floor; RP2040-Zero (behind y172) and USB-C untouched"),
        dict(part="black keys C#, D#, F#, G#, A# and A#0: top skin", dim="S31 (new), S02", old="top z55.5 to y147.0 (skin 2.0 thick)",
             new=pf("top z%.1f over y%.1f~147.0 (lip %.1f thick, underside z%.1f unchanged); z55.5 in front of y%.1f", (sb[1], sb[0], sb[1] - 53.5, 53.5, sb[0])),
             why="geometry major 2: pad-bar slide-out, black pad corner z55.40 hit the skin (-0.10)"),
        dict(part="pad bar (all 6 kinds)", dim="P13", old="y146.5~183.0 (36.5 long), no preload",
             new="y146.5~183.5 (37.0 long, rear end on the plate step y183.5); leaf 0.6 x 4 x 8 on each rear-step edge, 0.3 preload up against the rail lip (text only)",
             why="geometry minor: the bar was driven 0.5 back on every note; no vertical play"),
        dict(part="pad-bar rails (8 per module, 2 per end part)", dim="P13", old="y168~183.0, z65.60~67.30, no lip exported",
             new="y160~183.5: y160~168 hang from the channel ceiling z68.80 down to z65.60, y168~183.5 z65.60~67.30; lip 0.6 wide z65.60~65.80 under the bar's rear-step edge (overlap 0.3), y160~183.5",
             why="geometry major 2 (bar held at rail height until its front part is out) + minor (dovetail undercut exported)"),
        dict(part="lever carrier (all)", dim="D07, S13", old="upper lips y150~186 continuous",
             new=pf("upper lips y150~%.0f and y%.0f~186; none over y%.0f~%.0f (beside the pad)", (P["lip_gap_y"][0], P["lip_gap_y"][1], P["lip_gap_y"][0], P["lip_gap_y"][1])),
             why="geometry minor: lip 0.7 beside the soft pad; pair now in the sweep"),
        dict(part="lever carrier hub collars", dim="P14", old=", ".join(pf("%s %.3f/%.3f", (n, (a + P["collar_short"]) if a > 0 else 0.0, (b + P["collar_short"]) if b > 0 else 0.0)) for n, (a, b) in g["collars"].items()),
             new=", ".join(pf("%s %.3f/%.3f", (n, a, b)) for n, (a, b) in g["collars"].items()),
             why=pf("geometry minor: every collar %.2f shorter, axial play per bay 0.32 -> %.2f", (P["collar_short"], R.get("axial_play_bay", 0.0)))),
        dict(part="frame rear wall: torsion-spring groove", dim="P18, S28", old="groove in the wall face y209.0~209.8 (0.8 deep), 1.2 wide, z50~58",
             new="printed boss y207.8~209.0, x lever +-1.6, z47~plate underside; groove y207.8~209.8 (2.0 deep, bottom unchanged), 1.2 wide, z50~58, lead-in 0.5 x 45 deg",
             why="geometry minor: an unloaded leg (keyless lever at -31.3 deg) stays in the groove"),
        dict(part="lever-rod end plug", dim="P22", old="in the model only (1.2)", new="listed part (printed, 1 per module / end part)", why="geometry minor: parts list"),
    ]
    return C


def wire_poly(seg, d):
    """thin rectangle of width d around a segment (spring leg outline)."""
    (y0, z0), (y1, z1) = seg
    L = math.hypot(y1 - y0, z1 - z0)
    ny, nz = -(z1 - z0) / L * d / 2, (y1 - y0) / L * d / 2
    return [(y0 + ny, z0 + nz), (y1 + ny, z1 + nz), (y1 - ny, z1 - nz), (y0 - ny, z0 - nz)]


def export(P, g, R, ep, OUT, pk, pl):
    keys, lay, caps = g["keys"], g["lay"], g["caps"]
    K, L = P["K"], P["L"]
    Aw, Ab = g["Aw"], g["Ab"]
    parts = []

    def key_dip(poly, black):
        """r4.4 (R44 issue 3): the truly settled 1 N bottom WITH the pad as the full planar state of the colour's key
        (rotation about the key COM + translation: the notch settles on the rod), same for both colours."""
        A_, hs_ = (Ab, g["held_pad_b"]) if black else (Aw, g["held_pad_w"])
        return [m.key_point_world(A_, hs_, p) for p in poly]

    def kpose(poly, pkn, pose):
        """r4.4 fix 2: the key pose exactly as swept (rotation about K + the notch translation)"""
        sh_ = pkn.get("_shift", {}).get(pose, (0.0, 0.0))
        return [(q[0] + sh_[0], q[1] + sh_[1]) for q in (m.rot(p, K, pkn[pose]) for p in poly)]
    for nm in m.ORDER:
        kd = keys[nm]
        yc = caps["black" if kd["black"] else "white"]
        pkn, pln = pk[nm], pl[nm]
        for tag, x0, x1, poly in m.key_prisms(P, kd, yc, lay["levers"][nm]):
            parts.append(dict(body="key " + nm, part=tag, moving=True, x=rr([x0, x1]), side_rest=rr(poly, 2),
                              side_dip=rr(key_dip(poly, kd["black"]), 2), side_dip_rigid=rr(kpose(poly, pkn, "dip_rigid"), 2),
                              side_ff=rr(kpose(poly, pkn, "ff"), 2), side_over=rr(kpose(poly, pkn, "over"), 2)))
        xl_ = lay["levers"][nm]
        for tag, x0, x1, poly in m.lever_prisms(P, xl_, g["collars"][nm]) + [("steel block SS400 9x19x40 (inside the carrier)", xl_ - P["steel_w"] / 2, xl_ + P["steel_w"] / 2, m.steel_poly(P))]:
            parts.append(dict(body="lever " + nm, part=tag, moving=True, x=rr([x0, x1]),
                              side_rest=rr([m.rot(p, L, -pln["rest"]) for p in poly], 2), side_rigid0=rr(poly, 2),
                              side_dip=rr([m.rot(p, L, -pln["dip"]) for p in poly], 2), side_ff=rr([m.rot(p, L, -pln["ff"]) for p in poly], 2),
                              side_dip_rigid=rr([m.rot(p, L, -pln["dip_rigid"]) for p in poly], 2),
                              side_over=rr([m.rot(p, L, -pln["over"]) for p in poly], 2),
                              side_service=rr([m.rot(p, L, -g["b_hold_removal"]) for p in poly], 2)))
    # r4.2: the torsion spring of every lever (world outlines per lever pose; the long leg is fixed while loaded)
    for nm in m.ORDER:
        xl_ = lay["levers"][nm]
        pln = pl[nm]
        cl_ = (P["spring_n"] + 1) * P["spring_d"] / 2          # r4.5: half the coil length; the legs leave at +-(cl_ - d/2)
        for tag, xa_, xb_, key_ in ((pf("torsion spring coil (MISUMI %s, OD %.1f, %.2f long)", (P["spring_cat"]["part"], P["spring_ID"] + 2 * P["spring_d"], 2 * cl_)), xl_ - cl_, xl_ + cl_, "coil"),
                                    ("torsion spring short leg (straight, in the hub's short-leg groove; -x coil end)", xl_ - cl_, xl_ - cl_ + P["spring_d"], "short_leg"),
                                    ("torsion spring long leg (+x coil end, straight up into the 2.4 rear-wall groove)", xl_ + cl_ - P["spring_d"], xl_ + cl_, "long_leg")):
            poses_ = dict(rest=pln["rest"], dip=pln["dip"], dip_rigid=pln["dip_rigid"], ff=pln["ff"], over=pln["over"], service=g["b_hold_removal"], rigid0=0.0,
                          drop=math.radians(R["lever_drop"][nm]["angle_deg"]))           # r4.5 fix round: key out, lever let go (the unloaded leg turns with it)
            ent = dict(body="spring " + nm, part=tag, moving=True, x=rr([xa_, xb_]))
            for pz, bb_ in poses_.items():
                sg_ = m.spring_geometry(P, bb_)
                ent["side_" + pz] = rr(sg_[key_] if key_ == "coil" else wire_poly(sg_[key_], P["spring_d"]), 2)
            parts.append(ent)
    for name, x0, x1, poly in m.fixed_prisms(P, g):
        parts.append(dict(body="fixed", part=name, moving=False, x=rr([x0, x1]), side=rr(poly, 2), **({"female": True} if name.startswith("fin boss bore") else {})))
    # r4.5 fix round (drafter): the rear-wall spring-leg grooves and their entry chamfers as female cut parts (not solids)
    for q_ in m.spring_groove_cuts(P, lay["levers"]):
        parts.append(dict(body="fixed", part=pf("spring groove cut %s (female: boss + rear wall, open at the boss underside)", q_["lever"]), moving=False, female=True, x=rr(q_["x"]), side=rr(q_["side"], 2)))
        parts.append(dict(body="fixed", part=pf("spring groove entry chamfer %s (female, %.1f x 45 deg on the x faces at the boss underside)", (q_["lever"], P["spring_lead_in"])), moving=False, female=True,
                          x=rr(q_["chamfer_x"]), side=rr(q_["chamfer_side"], 2), front=rr(q_["front"], 3)))
    end_parts = {}
    for side in ("left", "right"):
        e = ep[side]
        lst = []
        for nm in e["order"]:
            kd = e["keys"][nm]
            pkn = pk["C#"] if kd["black"] else pk["D"]
            pln = pl["C#"] if kd["black"] else pl["D"]
            for tag, x0, x1, poly in m.key_prisms(P, kd, e["caps"][nm], e["lay"]["levers"][nm]):
                lst.append(dict(body="key " + nm, part=tag, moving=True, x=rr([x0, x1]), side_rest=rr(poly, 2),
                                side_dip=rr(key_dip(poly, kd["black"]), 2), side_dip_rigid=rr(kpose(poly, pkn, "dip_rigid"), 2),
                                side_ff=rr(kpose(poly, pkn, "ff"), 2), side_over=rr(kpose(poly, pkn, "over"), 2)))
            for tag, x0, x1, poly in m.lever_prisms(P, e["lay"]["levers"][nm], e["collars"][nm]):
                lst.append(dict(body="lever " + nm, part=tag, moving=True, x=rr([x0, x1]), side_rest=rr([m.rot(p, L, -pln["rest"]) for p in poly], 2),
                                side_dip=rr([m.rot(p, L, -pln["dip"]) for p in poly], 2), side_dip_rigid=rr([m.rot(p, L, -pln["dip_rigid"]) for p in poly], 2),
                                side_ff=rr([m.rot(p, L, -pln["ff"]) for p in poly], 2),
                                side_over=rr([m.rot(p, L, -pln["over"]) for p in poly], 2),
                                side_service=rr([m.rot(p, L, -g["b_hold_removal"]) for p in poly], 2)))
        for name, x0, x1, poly in m.end_fixed_prisms(P, g, e):
            lst.append(dict(body="fixed", part=name, moving=False, x=rr([x0, x1]), side=rr(poly, 2), **({"female": True} if name.startswith("fin boss bore") else {})))
        for q_ in m.spring_groove_cuts(P, e["lay"]["levers"]):
            lst.append(dict(body="fixed", part=pf("spring groove cut %s (female: boss + rear wall, open at the boss underside)", q_["lever"]), moving=False, female=True, x=rr(q_["x"]), side=rr(q_["side"], 2)))
            lst.append(dict(body="fixed", part=pf("spring groove entry chamfer %s (female, %.1f x 45 deg on the x faces at the boss underside)", (q_["lever"], P["spring_lead_in"])), moving=False, female=True,
                            x=rr(q_["chamfer_x"]), side=rr(q_["chamfer_side"], 2), front=rr(q_["front"], 3)))
        sgr = P["spring_groove"]
        dxg = P.get("spring_groove_dx", 0.0)
        grooves = [dict(lever=nm, x=rr([xl + dxg - sgr[3] / 2, xl + dxg + sgr[3] / 2]), y=rr([sgr[0], sgr[0] + sgr[4]]), z=rr([sgr[1], sgr[2]]))
                   for nm, xl in e["lay"]["levers"].items()]
        eplan = [dict(part=pf("torsion spring groove %s", q["lever"]), poly=rr(m.rect(q["x"][0], q["x"][1], q["y"][0], q["y"][1]), 3)) for q in grooves]
        for f in m.end_fixed_prisms(P, g, e):
            if f[0].startswith(("pad bar", "sensor bar", "spring groove boss", "fin", "cheek", "lever rod", "sensor board", "rear wall (over the lead notch")):
                ys_ = [q[0] for q in f[3]]
                eplan.append(dict(part=f[0], poly=rr(m.rect(f[1], f[2], min(ys_), max(ys_)), 3)))
        # r4.4 (circuit cross-check 4): lead pads, lead path (floor), lane under the balance rail, rear-wall notch
        q4 = R["c44"]["ends"][side]
        sbd = m.END_DEF[side]["sb"]
        pr_ = P["board_pad_r"]
        for i_ in range(sbd["n_pads"]):
            xp_ = sbd["pads"][0] + i_ * (sbd["pads"][1] - sbd["pads"][0]) / (sbd["n_pads"] - 1)
            eplan.append(dict(part=pf("%s lead pad %d (underside)", ("J401" if side == "left" else "J411", i_ + 1)), circle=rr([xp_, P["sb_j201"][3], pr_], 3)))
        for xa_, ya_, xb_, yb_ in sbd["wires"]:
            eplan.append(dict(part=pf("underside wire (board, z < %.1f; 0.5 wide)", P["sb_board"][4]), poly=rr(wire_poly(((xa_, ya_), (xb_, yb_)), 0.5), 3)))
        eplan.append(dict(part=pf("lead %s %d-core (floor, from the pads through the rear-rib gap, fanned in by y%.2f)", ("W401" if side == "left" else "W411", sbd["cores"], q4["fan_y"])),
                          poly=rr(m.lead_path_poly(P, sbd), 3)))
        eplan.append(dict(part=pf("lead lane under the balance rail (z%.0f-%.0f)", tuple(P["lead_lane_z"])), poly=rr(m.rect(q4["lane"][0], q4["lane"][1], P["rail_front_y"], P["rail_y"][1]), 3)))
        eplan.append(dict(part=pf("rear-wall lead notch (z%.0f-%.0f)", tuple(P["lead_notch_z"])), poly=rr(m.rect(q4["lane"][0], q4["lane"][1], P["rear_wall"][0], P["rear_wall"][1]), 3)))
        end_parts[side] = dict(parts=lst, levers=rr(e["lay"]["levers"]), fins=rr(e["lay"]["fins"]), caps=rr(e["caps"]), cheek=e["cheek"],
                               collars=rr(e["collars"]), boss_len=rr(m.fin_boss_len(e["lay"], P)), spring_grooves=grooves, plan=eplan,
                               pad_faces={nm: dict(ref=rr(pf.ref, 3), normal=rr(pf.n, 5), tilt_deg=rr(math.degrees(pf.b_face), 3), gap=pf.gap,
                                                   z=rr((m.pad_face_z(pf, P["pad_y"][0]), m.pad_face_z(pf, P["pad_y"][1])), 3),
                                                   wedge=rr(R["end_parts"][side]["stat"][nm]["wedge"], 3)) for nm, pf in e["pads"].items()})
    pts = {}
    for A, nm, c in ((Aw, "white D", "D"), (Ab, "black C#", "C#")):
        a_ff, b_ff, b_rest, b_over = pk[c]["ff"], pl[c]["ff"], pl[c]["rest"], pl[c]["over"]
        pt = g["pad_b"] if A.black else g["pad_w"]
        named = [("key front top", A.front, "k"), ("finger point", A.finger, "k"), ("front stop (floor)", A.stop_pts[0], "k"),
                 ("rest felt bottom", A.rest_pts[0], "k"), ("magnet face", A.mag, "k"), ("key COM", A.ck, "k"),
                 ("capstan crown", (A.y_cap, P["z_c"]), "k"), ("keeper point (crossbar top)", A.keeper_pts[0], "k"),
                 ("balance pin slot centre", (P["pin_y"], P["block_step_z"]), "k"),
                 ("lever COM", A.cL, "l"), ("cap top (front corner)", (A.cap_c[0], A.cap_c[1] + A.cap_Rb), "l"),
                 ("steel top at the pad front", (P["y_steel_front"] + 3.0, P["z_st"]), "l"), ("steel rear-top corner", (P["y_steel_rear"], P["z_st"]), "l")]
        tab = []
        hs = g["held_pad_b"] if A.black else g["held_pad_w"]
        for lab, p, kind in named:
            if kind == "k":
                q0, q1, q2, q3 = p, A.kp(p, A.a_dip), A.kp(p, a_ff), m.key_point_world(A, hs, p)
            else:
                q0, q1, q2, q3 = A.lp(p, b_rest), A.lp(p, A.b_dip), A.lp(p, b_ff), A.lp(p, hs[1])
            tab.append(dict(point=lab, rest=rr(q0, 2), dip_rigid=rr(q1, 2), bottom_held_1N=rr(q3, 2), ff=rr(q2, 2)))
        pts[nm] = dict(K=K, L=L, a_dip=rr(A.a_dip, 5), b_dip=rr(A.b_dip, 5), a_ff=rr(a_ff, 5), b_ff=rr(b_ff, 5), b_rest=rr(b_rest, 5), b_over=rr(b_over, 5),
                       pad_face=dict(ref=rr(pt.ref, 3), normal=rr(pt.n, 5), tilt_deg=rr(math.degrees(g["held_b_b" if A.black else "held_b_w"]), 3), gap=P["gap_us_b" if A.black else "gap_us_w"]),
                       points=tab)
    plan = []
    for nm in m.ORDER:
        kd = keys[nm]
        xl = lay["levers"][nm]
        yc = caps["black" if kd["black"] else "white"]
        bx = m.block_x(P, kd)
        if kd["black"]:
            plan.append(dict(part=pf("key %s body", nm), poly=rr([(kd["head"][0], P["y_black_front"]), (kd["head"][1], P["y_black_front"]),
                                                               (kd["head"][1], 146.0), (kd["head"][0], 146.0)], 3)))
        else:
            h0, h1 = kd["head"]
            t0, t1 = kd["tail"]
            plan.append(dict(part=pf("key %s body", nm), poly=rr([(h0, 0.0), (h1, 0.0), (h1, 50.0), (t1, 50.0), (t1, 146.0), (t0, 146.0), (t0, 50.0), (h0, 50.0)], 3)))
        plan.append(dict(part=pf("key %s balance block", nm), poly=rr(m.rect(bx[0], bx[1], P["block_y"][0], P["block_y"][1]), 3)))
        plan.append(dict(part=pf("key %s balance pin", nm), circle=rr([(bx[0] + bx[1]) / 2, P["pin_y"], P["pin_d"] / 2], 3)))
        plan.append(dict(part=pf("key %s beam + tail", nm), poly=rr(m.rect(xl - 4, xl + 4, 146.0, P["y_tail_end"]), 3)))
        plan.append(dict(part=pf("key %s capstan", nm), circle=rr([xl, yc, P["cap_dk"] / 2], 3)))
        plan.append(dict(part=pf("key %s magnet", nm), circle=rr([kd["xc"], P["y_elem"], 2.5], 3)))
        cl, cr_ = g["collars"][nm]
        plan.append(dict(part=pf("lever %s", nm), poly=rr(m.rect(xl - P["lever_w"] / 2, xl + P["lever_w"] / 2, P["y_lever_front"] - P["nail_tab"][0], L[0] + P["hub_R"]), 3)))
        plan.append(dict(part=pf("lever %s hub + collars", nm), poly=rr(m.rect(xl - P["lever_w"] / 2 - cl, xl + P["lever_w"] / 2 + cr_, L[0] - 3.0, L[0] + 3.0), 3)))
        plan.append(dict(part=pf("up-stop pad %s", nm), poly=rr(m.rect(xl - P["pad_w"] / 2, xl + P["pad_w"] / 2, P["pad_y"][0], P["pad_y"][1]), 3)))
        plan.append(dict(part=pf("torsion spring groove %s", nm), poly=rr(m.rect(xl + P["spring_groove_dx"] - P["spring_groove"][3] / 2, xl + P["spring_groove_dx"] + P["spring_groove"][3] / 2, P["spring_groove"][0], P["spring_groove"][0] + P["spring_groove"][4]), 3)))
        # r4.4: top snap lips (lever frame y, at b = 0), the key's rest felt and rest foot
        for t_, x0_, x1_, poly_ in m.lever_prisms(P, xl, g["collars"][nm]):
            if t_.startswith("carrier top snap lip"):
                plan.append(dict(part=pf("lever %s %s (lever frame y)", (nm, t_)), poly=rr(m.rect(x0_, x1_, min(q[0] for q in poly_), max(q[0] for q in poly_)), 3)))
        (fx0_, fx1_), foot_ = m.rest_pad_x(P, nm, xl, kd["black"])
        plan.append(dict(part=pf("key %s rest felt", nm), poly=rr(m.rect(fx0_, fx1_, P["rest_pad_y"][0], P["rest_pad_y"][1]), 3)))
        if foot_:
            plan.append(dict(part=pf("key %s thin tail rest foot", nm), poly=rr(m.rect(foot_[0], foot_[1], P["rest_pad_y"][0], P["y_tail_end"]), 3)))
    for f0, f1 in lay["fins"]:
        # r4.5 fix 2 (resume): the F|F# (keel) fin over the board starts at fin_keel_front
        fy0_ = m.keel_front(P) if (P.get("board_hatch") and P["board_x"][0] < 0.5 * (f0 + f1) < P["board_x"][1]) else P["fin_y"][0]
        plan.append(dict(part="fin", poly=rr(m.rect(f0, f1, fy0_, P["fin_y"][1]), 3)))
    for f in m.fixed_prisms(P, g):
        if f[0].startswith(("fin boss bore", "lever rod end plug")):          # r4.4 (the rod itself is the 'lever rod' rectangle below)
            plan.append(dict(part=f[0], poly=rr(m.rect(f[1], f[2], P["L"][0] - P["rod_L"] / 2, P["L"][0] + P["rod_L"] / 2), 3)))
    for a, b in m.bays(lay["fins"]):
        xa2, xb2 = a + P["bar_rail"][0] + P["pad_bar_clear"], b - P["bar_rail"][0] - P["pad_bar_clear"]
        plan.append(dict(part="pad bar", poly=rr(m.rect(xa2, xb2, P["pad_bar_y"][0], P["pad_bar_y"][1]), 3)))
        for xr in (a, b - P["bar_rail"][0]):
            plan.append(dict(part="pad bar rail", poly=rr(m.rect(xr, xr + P["bar_rail"][0], P["rail_y0"], P["pad_bar_y"][1]), 3)))
        for xl_ in (a + P["bar_rail"][0], b - P["bar_rail"][0] - P["rail_lip"]):
            plan.append(dict(part="pad bar rail lip", poly=rr(m.rect(xl_, xl_ + P["rail_lip"], P["rail_lip_y0"], P["pad_bar_y"][1]), 3)))
        for xt0, xw0 in ((xa2, xa2), (xb2 - P["bar_leaf"][1], xb2 - P["bar_leaf"][1] - P["bar_leaf_slot"])):
            plan.append(dict(part="pad bar leaf window (through)", poly=rr(m.rect(min(xt0, xw0), min(xt0, xw0) + P["bar_leaf"][1] + P["bar_leaf_slot"], P["bar_leaf_y"][0] - P["bar_leaf_slot"], P["bar_leaf_y"][1]), 3)))
            plan.append(dict(part="pad bar leaf tongue", poly=rr(m.rect(xt0, xt0 + P["bar_leaf"][1], P["bar_leaf_y"][0], P["bar_leaf_y"][1]), 3)))
    for n_, rect_ in (("top plate", (0.2, 164.3, P["ledge_y0"], P["rear_wall"][0])), ("curtain strip", (0.2, 164.3, P["curtain_y"][0], P["curtain_y"][1])),
                      ("rear shelf", (0.0, m.usb_slot(P)[0]) + P["shelf_y"]), ("rear shelf", (m.usb_slot(P)[1], 164.5) + P["shelf_y"]),
                      ("rear shelf slot over the USB plug (open)", m.usb_slot(P) + P["shelf_y"]), ("balance rail", P["rail_x"] + (P["rail_front_y"], P["rail_y"][1])),
                      ("ribbon lane under the balance rail (z5-10)", P["ribbon_x"] + (P["rail_front_y"], P["rail_y"][1])),
                      ("RP2040-Zero (on pin headers)", P["zero_xy"]), ("USB-C receptacle", P["usb_rcpt"][:4]), ("CD74HC4067 module", P["mux_xy"]),
                      ("J301 ribbon 2x8 pads", (P["ribbon_pads"][0] - P["board_pad_r"], P["ribbon_pads"][1] + P["board_pad_r"], P["ribbon_pads"][2] - P["board_pad_r"], P["ribbon_pads"][3] + P["board_pad_r"])),
                      ("J302 EXT 1x6 pads", (P["ext_pads"][0] - P["board_pad_r"], P["ext_pads"][1] + P["board_pad_r"], P["ext_pads"][2] - P["board_pad_r"], P["ext_pads"][2] + P["board_pad_r"])),
                      ("key rod", P["rod_k_x"] + (139.0, 143.0)), ("lever rod", P["rod_L_x"] + (L[0] - P["rod_L"] / 2, L[0] + P["rod_L"] / 2)),
                      ("control board", P["board_x"] + P["board_y"]), ("USB plug", P["usb_x"] + P["usb_y"]),
                      ("sensor bar", (0.5, 162.9) + P["bar_y"]), ("rear wall", (0.0, 164.5) + P["rear_wall"])):
        plan.append(dict(part=n_, poly=rr(m.rect(rect_[0], rect_[1], rect_[2], rect_[3]), 3)))
    for xr in g["ribs"]:
        plan.append(dict(part="shelf rib", poly=rr(m.rect(xr - 0.6, xr + 0.6, P["rib_y0"], P["shelf_y"][1]), 3)))
    fb_ = [f for f in lay["fins"] if P["board_x"][0] < 0.5 * (f[0] + f[1]) < P["board_x"][1]][0]
    plan.append(dict(part="stripboard slot (open to the front edge)", poly=rr(m.rect(fb_[0] - P["board_slot_clear"], fb_[1] + P["board_slot_clear"], P["board_y"][0], P["board_slot_y1"]), 3)))
    plan.append(dict(part="board keep-out (no parts / wires)", poly=rr(m.rect(fb_[0] - P["board_slot_keepout"], fb_[1] + P["board_slot_keepout"], P["board_y"][0], P["board_slot_y1"] + P["board_slot_keepout"]), 3)))
    for f in m.fixed_prisms(P, g):
        if f[0] == "balance rail cradle":
            plan.append(dict(part="rod cradle", poly=rr(m.rect(f[1], f[2], P["K"][0] - 3.0, P["K"][0] + 3.0), 3)))
    # r4.4 (circuit cross-check 1, 3, 5): stand-offs / M3x6 heads / locating pins (circles), the ribbon under the board and on the
    # floor, the v3 sensor board and its support
    if P.get("board_mount") == "hung":
        hx0_, hx1_, hy0_, hy1_ = P["board_hatch"]
        nx0_, nx1_, ny1_ = P["board_hatch_notch"]
        plan.append(dict(part="floor hatch under the control board (r4.4 fix 2b; the board goes in from below)", poly=rr([(hx0_, hy0_), (hx1_, hy0_), (hx1_, hy1_), (nx1_, hy1_), (nx1_, ny1_), (nx0_, ny1_), (nx0_, hy1_), (hx0_, hy1_)], 3)))
        fk_ = [f for f in lay["fins"] if P["board_x"][0] < 0.5 * (f[0] + f[1]) < P["board_x"][1]][0]
        plan.append(dict(part=pf("F|F# fin keel z%.0f-%.1f (foot grounded to the balance rail's rear face)", (P["fin_keel"][1], P["fin_keel"][2])),
                         poly=rr(m.rect(fk_[0] + P["fin_ext_inset"], fk_[1] - P["fin_ext_inset"], P["fin_keel"][0], m.keel_front(P)), 3)))
        for q_ in m.board_boss_rects(P, g["z_shelf"] - 2.0):
            plan.append(dict(part=pf("control-board boss D%.0f hung over the board, bracket to the %s (z%.1f-%.2f)", (P["standoff_d"], q_[9], q_[4], q_[5])),
                             poly=rr(m.rect(q_[0], q_[1], q_[2], q_[3]), 3), circle=rr([q_[7], q_[8], P["standoff_d"] / 2], 3)))
    for x_, y_, k_ in ([] if P.get("board_mount") == "hung" else P["board_standoffs"]):
        plan.append(dict(part=pf("control-board stand-off D%.0f (%s)", (P["standoff_d"], pf("screw boss, bore D%.1f", P["standoff_bore"][0]) if k_ == "screw" else "locating pin")),
                         circle=rr([x_, y_, P["standoff_d"] / 2], 3)))
    for x_, y_, k_ in (P["board_standoffs"] if P.get("board_mount") == "hung" else []):
        if k_ == "screw":
            plan.append(dict(part=pf("control-board screw M3x6 head D%.1f (v3.2 L35 ISO 7380)", P["board_screw"][0]), circle=rr([x_, y_, P["board_screw"][0] / 2], 3)))
        else:
            plan.append(dict(part=pf("control-board locating pin D%.1f (board hole D%.1f)", (P["board_pin"][0], P["board_hole"])), circle=rr([x_, y_, P["board_pin"][0] / 2], 3)))
    ux0_, ux1_ = m.ribbon_x_under_board(P)
    wr_ = P["ribbon_cores"] * P["ribbon_pitch"]
    plan.append(dict(part=pf("16-core ribbon under the board (z%.0f-%.0f, J301 from the underside)", tuple(P["ribbon_under_z"])),
                     poly=rr(m.rect(ux0_, ux1_, P["rail_y"][1], P["ribbon_pads"][3] + P["board_pad_r"]), 3)))
    plan.append(dict(part=pf("16-core ribbon SB J201 -> lane (floor, centred x%.2f)", P["ribbon_xc"]),
                     poly=rr(m.rect(P["ribbon_xc"] - wr_ / 2, P["ribbon_xc"] + wr_ / 2, P["sb_board"][3], P["rail_front_y"]), 3)))
    plan.append(dict(part="SB J201 ribbon 2x8 pads (underside)", poly=rr(m.rect(P["sb_j201"][0] - P["board_pad_r"], P["sb_j201"][1] + P["board_pad_r"], P["sb_j201"][2] - P["board_pad_r"], P["sb_j201"][3] + P["board_pad_r"]), 3)))
    for f in m.fixed_prisms(P, g):
        if f[0].startswith(("sensor board", "sensor-bar ledge")):         # r4.5 circuit 2nd: + the v3 P112 right ledge (lip / post)
            ys_ = [q[0] for q in f[3]]
            plan.append(dict(part=f[0], poly=rr(m.rect(f[1], f[2], min(ys_), max(ys_)), 3)))
    # r4.3: the entries of fix rounds 1-2 are copied unchanged from the r4.2 export (they were written with r4.2 values)
    # r4.4: the rows of fix rounds 1-3 are copied unchanged from the r4.3 export (written with r4.3 values)
    OLD_CHG = [c for c in json.load(open(os.path.join(OUT, "geometry.r4_3.json")))["changes_this_round"] if c.get("round") in ("r4.2 -> r4.3", "r4.1 -> r4.2", "r4.0 -> r4.1")]
    geo = dict(
        meta=dict(project="Toccata v4 W1+ key action (round 4: fix + simplify; fix round 4 = r4.4, remaining issues: top snap lip, F / F# rest landing, dip export; "
                          "+ circuit session cross-check: BRD-01 on the 2.54 grid, plug face y196.8, control-board stand-offs, sensor-board supports, end-part lead lanes; "
                          "r4.5: torsion spring = MISUMI C-UA90R5-3-0.5 with both arms cut, new short-leg groove in the hub; r4.5 circuit 2nd: sensor-bar right ledge (v3 P112), "
                          "left end part floor without the module hatch, ghost-filter long runs)", units="mm", coords="x across (0 = C left boundary), y from the white lip (+ away), z from the desk",
                  note=pf("side polygons are (y, z) prisms extruded over x.  keys: rest / dip (truly settled 1 N bottom WITH the pad, both colours - r4.3 exported the rigid bottom) / "
                       "dip_rigid (rigid kinematic bottom) / ff (max over-travel of all dynamic cases incl. the 2.5 m/s abuse) / over (max rise above rest after a release, incl. the chord "
                       "seats and grids; F / F# from their own rest-felt landing runs); r4.4 fix 2: dip_rigid / ff / over also carry the notch translation on the rod exactly as swept "
                       "(r44.key_shift: dip_rigid = the rest seating, ff / over = the lowest rod point of the dynamics), side_rest is the design pose.  levers: side_rest = settled rest angle, side_rigid0 = b 0, dip = truly settled 1 N bottom with "
                       "the pad, dip_rigid = rigid kinematic bottom, ff (max angle incl. pad compression), over (return overshoot), service = held at %.1f deg by its "
                       "fingernail tab for a key removal (pad bar out)", math.degrees(g["b_hold_removal"]))),
        key_points=pts, parts=parts, plan=plan, end_parts=end_parts,
        solved=rr(dict(caps=caps, levers=lay["levers"], fins=lay["fins"], collars=g["collars"], boss_len=m.fin_boss_len(lay, P),
                       pad_face_w=dict(ref=g["pad_w"].ref, normal=g["pad_w"].n, y=P["pad_y"], z=(m.pad_face_z(g["pad_w"], P["pad_y"][0]), m.pad_face_z(g["pad_w"], P["pad_y"][1]))),
                       pad_face_b=dict(ref=g["pad_b"].ref, normal=g["pad_b"].n, y=P["pad_y"], z=(m.pad_face_z(g["pad_b"], P["pad_y"][0]), m.pad_face_z(g["pad_b"], P["pad_y"][1]))),
                       z_seat=g["z_seat"], z_top=g["z_top"], y_bar_step=g["y_bar_step"], wedge=g["wedge_range"], plate_under=g["plate_under"],
                       z_shelf=g["z_shelf"], z_keep=g["z_keep"], w_felt_line=g["w_felt_line"], b_felt_line=g["b_felt_line"],
                       b_rest_w=g["b_rest_w"], b_rest_b=g["b_rest_b"], b_ff_w=g["b_ff_w"], b_ff_b=g["b_ff_b"], b_over_w=g["b_over_w"], b_over_b=g["b_over_b"],
                       held_b_w=g["held_b_w"], held_b_b=g["held_b_b"], seat_k=g["seat_k_keys"],
                       spring=dict(kt=P["spring_kt"], free_deg=P["spring_free_deg"], d=P["spring_d"], ID=P["spring_ID"], n=P["spring_n"], leg=P["spring_leg"],
                                   pocket=P["spring_pocket"], groove=P["spring_groove"], boss=P["spring_boss"], slot_deg_lever_frame=P["spring_slot"][0],
                                   slot_faces=(P["spring_slot"][1], -P["spring_slot"][2]), coil_rm=P["spring_rm"], short_leg_bend_deg=R["r42"]["spring_slot"]["short_bend_deg"],
                                   long_leg_world=R["r42"]["spring_rest"]["long_leg"], tip_world=R["r42"]["spring_rest"]["tip"],
                                   short_leg_lever_frame=m.spring_geometry(P, 0.0)["short_leg"], leg_range_deg=R["r42"]["spring_b_range"], leg_slot_margin=R["r42"]["spring_slot"]["margin"],
                                   part=P["spring_cat"]["part"], E=P["spring_E"], short_leg_groove=R["r42"]["spring_slot"]["notch"], insert=dict(R["r45"]["insert"]), long_leg_end="+x",
                                   catalogue=R["spring"]["cat"], hand_over_catalogue=R["spring"]["hand_over_cat"],
                                   grooves=[dict(lever=nm, x=(xl + P["spring_groove_dx"] - P["spring_groove"][3] / 2, xl + P["spring_groove_dx"] + P["spring_groove"][3] / 2), y=(P["spring_groove"][0], P["spring_groove"][0] + P["spring_groove"][4]),
                                                 z=(P["spring_groove"][1], P["spring_groove"][2]), chamfer=P["spring_lead_in"]) for nm, xl in lay["levers"].items()],
                                   # r4.5 fix round: captured short leg; the groove band is in the LEVER frame - place it with each lever's own rest angle
                                   mode=P.get("spring_mode"), short_leg=P["spring_short_leg"], notch=P["spring_notch"], window=P["spring_window"], groove_dx=P["spring_groove_dx"],
                                   insertion_slot_deg=P["spring_slot"][0], rest_deg_per_lever={nm: math.degrees(pl[nm]["rest"]) for nm in lay["levers"]},
                                   capture=R["spring"]["capture"], capture_tol=R["spring"]["capture_tol"], float_r45=R["spring"]["float"],
                                   long_leg_drop_note="side_drop of the spring parts = lever at metrics lever_drop angle (the unloaded long leg turns with the lever below the free angle)"),
                       y_bar_joggle=g["y_bar_joggle"], plate_step_y=P["plate_step_y"],
                       end_parts={s: dict(levers=ep[s]["lay"]["levers"], fins=ep[s]["lay"]["fins"], caps=ep[s]["caps"], cheek=ep[s]["cheek"], collars=ep[s]["collars"]) for s in ep}), 3),
        dims=dims_table(P, g, R, ep),
        # r4.5 fix round: its rows, then every r4.5 / older row copied unchanged from the r4.5 export (geometry.r4_5a.json)
        # r4.5 circuit 2nd cross-check: its rows, then every row of the r4.5 fix export copied unchanged (geometry.r4_5c.json)
        changes_this_round=[dict(c, round="r4.5 fix -> r4.5 circuit 2nd") for c in changes_r45c(P, g, R, ep)] +
                           json.load(open(os.path.join(OUT, "geometry.r4_5c.json")))["changes_this_round"],
        r44=dict(lip43=R["clear"]["lip43"], lip44=R["clear"]["lip44"], rod=R["clear"]["rod"], dip=R["clear"]["dip"], over_ff=R["clear"]["over_ff"], over_brief=R["clear"]["over_brief"],
                 r43_felts=R["clear"]["r43_felts"], steel_retention=R["steel_retention"], land=R["r44"]["land"], land43=R["r44"]["land43"], land_sum=R["r44"]["land_sum"],
                 over_key=R["r44"]["over_key"], over_key_r43=R["r44"]["over_key_r43"], over_key_brief=R["r44"]["over_key_brief"],
                 key_shift=R.get("key_shift"), lever_float=R["clear"].get("lever_float"), pair_gap=R["clear"].get("pair_gap")),
        circuit_r43=R["r43"],
        circuit_r44=R["c44"],
        circuit_r45=R["c45"],
        drafter_r42=dict(fit_module=R["r42"]["fit_module"], fit_end={k: v for k, v in R["r42"]["fit_end"].items()}, gaps_module=R["r42"]["gaps_module"],
                         gaps_end=R["r42"]["gaps_end"], tab_core=R["r42"]["tab_core"], slide_fit=R["r42"]["slide_fit"]),
        patches_merged=["end_parts fin bosses one-sided on the seam fins (left 43.85-46.8, right 0.2-3.15)", "plan lever rod x = rod_L_x 1.5-162.9",
                        "black-key magnet bosses merged into the walls (+-4.0)", "r3 compression assist spring / P18 / D05 replaced by the torsion spring (audit A2)"],
    )
    # r4.5 fix round: the solved-values ripple row (old = geometry.r4_5a.json / work_r45b/metrics.r4_5a.json)
    try:
        raise RuntimeError("r4.5 circuit 2nd: the r4.5 fix ripple row is copied with geometry.r4_5c.json")
        G0_ = json.load(open(os.path.join(OUT, "geometry.r4_5a.json")))
        M0_ = json.load(open(os.path.join(OUT, "work_r45b", "metrics.r4_5a.json")))
        geo_r = rr(geo)
        row_ = dict(ripple_f2(G0_["solved"], geo_r["solved"], G0_["end_parts"], geo_r["end_parts"], M0_["white"]["lever_g"], R["white"]["lever_g"]), round="r4.5 -> r4.5 fix")
        row_["why"] = pf("r4.5 fix consequence: the lever is %.3f g %s (captured-groove pocket section, spring %.3f g with the 8.0 short leg) and k_t %.3f (was %.3f; same b = 0 torque), bottom torque %.2f (was %.2f), "
                         "so the capstans / settled bottom / pad faces / wedges move by the amounts shown",
                         (abs(R["white"]["lever_g"] - M0_["white"]["lever_g"]), "heavier" if R["white"]["lever_g"] > M0_["white"]["lever_g"] else "lighter", R["spring"]["mass_g"], P["spring_kt"], M0_["spring"]["kt"],
                          R["spring"]["states"]["bottom"]["T"], M0_["spring"]["states"]["bottom"]["T"]))
        k2_ = max(i_ for i_, c_ in enumerate(geo["changes_this_round"]) if c_.get("round") == "r4.5 -> r4.5 fix")
        geo["changes_this_round"].insert(k2_ + 1, row_)
    except Exception as e_:
        print("r4.5 fix ripple row not added:", e_)
    with open(os.path.join(OUT, "geometry.json"), "w") as f:
        json.dump(rr(geo), f, ensure_ascii=False, indent=0)
    R["dims"] = geo["dims"]
