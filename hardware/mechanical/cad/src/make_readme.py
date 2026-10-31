"""README.md for hardware/mechanical/cad from manifest.json (+ the adjustment log).

L2 (2026-10-01): the rear bar is the one-piece L2 body of spec/body_L2.json. Every L2 number in the text is read from body.py (one
ANGLE constant, spec rules) or from manifest.json, so the README follows the built files (ANGLE 40 since 2026-10-01; the first L2
choice 43 is shown as the alternative from pareto_by_angle).
"""
import collections
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import body  # noqa: E402  (constants only; build() is not called here)
import keyaction  # noqa: E402  (KEY_ROUND, A11)
import touchscreen_rev3 as TS  # noqa: E402  (R31 rev 3 numbers / poses)

L2 = json.load(open(os.path.join(OUT, "spec", "body_L2.json")))


def f(v, nd=2):
    """number without trailing zeros."""
    s = "%.*f" % (nd, v)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ------------------------------------------------------------------ L2 figures (from body.py, i.e. from the ANGLE constant)

QTS, VAS, FS, FILL = 0.72, 3.0, (90.0, 128.0, 109.0), 1.175     # spec speakers.qtc assumption / fc_hz (Fs 90~128, mid 109), fill +17.5 %
EAR_YZ = tuple(float(v) for v in re.search(r"y(-?[\d.]+), z(-?[\d.]+)", next(k for k in L2["speakers"]["aim"]["yz_offaxis_deg"]
                                                                              if k.startswith("middle"))).groups())   # (-300, 460)


def _driver_displacement_L():
    """volume of electronics.py's CW-100B25 model behind the baffle inner face (w < -T), L - check_body.py subtracts the same lump."""
    try:
        import electronics
        loc, _ = electronics.speaker_local(json.load(open(os.path.join(OUT, "spec", "electronics_rearbar.json"))))
        return loc.trim_by_plane((0.0, 0.0, -1.0), body.T).volume() / 1e6
    except Exception:                                # electronics mid-edit: leave the number out
        return None


def l2_figures():
    P = body.POD
    W = 1254.0                                       # plan width x-16..1238 (A05)
    dep = body.YB                                    # back face from the rules (40 deg: 342.5, 43 deg: 341.5)
    l1 = L2["comparison_vs_L1"]
    area_l1 = l1["behind_keys_area_mm2"]["L1"]
    area = W * (dep - 212.0)
    inner_w = body.SPK_IX["L"][1] - body.SPK_IX["L"][0]
    gross = body.poly_area(body.CAVITY) * inner_w / 1e6
    disp_w1 = L2["speakers"]["inner_volume"]["gross_L"] - L2["speakers"]["inner_volume"]["net_L"]   # W1 rule: unit = 0.100 L
    net = gross - disp_w1
    disp_model = _driver_displacement_L()
    mc = P.D(0.0, -45.5)                             # magnet centre (w -37..-54)
    steel = P.D(-52.5, 7.0)                          # flange lower corner (nearest steel)
    mb = P.D(0.0, -54.0)                             # magnet back face centre
    pole_b, pole_f = (body.YBI - mb[0]) / P.s, (mb[1] - body.Z_BOT) / P.c      # along the axis to the back ply / the bottom ply
    pole = min(pole_b, pole_f)
    r_net, r_fill = math.sqrt(1.0 + VAS / net), math.sqrt(1.0 + VAS / (net * FILL))
    ear = math.degrees(math.atan2(EAR_YZ[1] - P.C[1], P.C[0] - EAR_YZ[0]))          # elevation of the middle ear seen from the driver
    sp = {
        "module": P.sightline_clear((212.0, body.MOD_TOP)),
        "flange": P.sightline_clear(P.D(-52.5, 7.0)),
        "gasket": P.sightline_clear(P.D(-52.5, 3.0)),
        "F": P.sightline_clear(P.F),
        "grille_foot": P.sightline_clear(P.D(-50.0, 0.0)),
        "plate_perp": P.perp_clear(P.D(body.GR_S0, body.GR_W[0])),
        "plate_vert": -P.sightline_clear(P.D(body.GR_S0, body.GR_W[0])),
    }
    return {
        "angle": body.ANGLE, "angle_v": 90.0 - body.ANGLE, "depth": dep, "area": area, "area_l1": area_l1,
        "area_pct": 100.0 * (area / area_l1 - 1.0), "top": body.SPK_ZT, "centre_top": body.Z_LID, "drv": body.DRV_YZ,
        "drv_x": body.DRV_X, "slant": body.SL_LEN, "gross": gross, "net_spec": net, "disp_w1": disp_w1,
        "net_model": (gross - disp_model) if disp_model else None,
        # W1 method: Qtc and the fill (+17.5 % apparent volume) on the NET volume (gross - 0.100 L), Vas 3 L, Qts 0.72
        "qtc_net": QTS * r_net, "qtc_fill": QTS * r_fill, "qtc_gross": QTS * math.sqrt(1.0 + VAS / gross),
        "fc_net": tuple(fs * r_net for fs in FS), "fc_fill": tuple(fs * r_fill for fs in FS),
        "aim_ear": ear, "aim_off": (90.0 - body.ANGLE) - ear,
        "sp": sp, "d14_sensor": math.hypot(mc[0] - body.SENSOR_YZ[0], mc[1] - body.SENSOR_YZ[1]),
        "d14_steel": math.hypot(steel[0] - body.SENSOR_YZ[0], steel[1] - body.SENSOR_YZ[1]),
        "d14_sensor_z8": math.hypot(mc[0] - body.SENSOR_YZ[0], mc[1] - 8.0), "d14_steel_z8": math.hypot(steel[0] - body.SENSOR_YZ[0], steel[1] - 8.0),
        "mag_back": body.YBI - P.D(42.5, -54.0)[0], "pole_wall": "뒤판" if pole_b <= pole_f else "아랫판",
        "pole": pole, "depth_normal": min((body.YBI - P.C[0]) / P.s, (P.C[1] - body.Z_BOT) / P.c), "l1_top": l1["heights_z"]["pods_L1"],
        "area_l1_latch": l1["behind_keys_area_mm2"]["L1_with_latches"],
        "l1_depth": l1["depth_y"]["L1"], "l1_depth_latch": l1["depth_y"]["L1_with_latches"],
        "pod_w": body.SPK_X["L"][1] - body.SPK_X["L"][0], "pod_d": dep - body.Y0,
        "duct_y": body.DUCT_Y, "duct_z": body.DUCT_Z, "y0": body.Y0,
    }


def _real_path_clear():
    """27 deg line from the real radiating edge D(-45, 7): vertical clearance over the module rear top edge (212, 72.85)."""
    o = body.POD.D(-45.0, 7.0)
    return o[1] + (o[0] - 212.0) * body.TAN27 - body.MOD_TOP


def pareto_row(deg):
    return next((r for r in L2["pareto_by_angle"]["rows"] if abs(r["baffle_deg"] - deg) < 1e-6), None)


def grille_stats(man):
    """(holes, open % lattice, open % in front of D94, plate) from the grille note (the build writes the counted numbers there)."""
    g = next((p for p in man["parts"] if p["id"] == "SPKL-GRILLE"), None)
    n = (g or {}).get("note") or ""
    m1 = re.search(r"구멍 (\d+)개, 개구율 ([\d.]+) %", n)
    m2 = re.search(r"Ø94 앞 ([\d.]+) %", n)
    return (int(m1.group(1)) if m1 else None, float(m1.group(2)) if m1 else None, float(m2.group(1)) if m2 else None)


# ------------------------------------------------------------------ note parsing (사양 그대로 / 사양과 다름 / 추정)

TAG_RX = re.compile(r"(?:^|;\s*)(사양 그대로|사양과 다름\(작은 고침\)|추정)\s*:\s*")


def note_segments(note):
    """[(tag, text)] of a part note written as 'tag: text; tag: text'."""
    parts = TAG_RX.split(note or "")
    return [(parts[i], _fix_note(parts[i + 1].strip(" ;"))) for i in range(1, len(parts) - 1, 2)]


def _fix_note(txt):
    """README-side corrections of part-note text that the model numbers contradict (the notes are written in body.py).
    W1 review 2026-10-02: the PR-HUBSHELF note says the bracket screw bites 'about 9' into the back ply; the model gives
    bracket front y + head seat 4 + screw length - back-ply inner face = 7 (M3 x 12, L78) / 8 (13 mm)."""
    return re.sub(r"[합뒤]판 물림 약 [\d.]+", lambda m_: "뒤판 물림 %s (M3 × 12, L78) / %s (13 mm)" % (f(shelf_engage(12.0), 1), f(shelf_engage(13.0), 1)), txt)


def _base_name(n):
    n = n.split(" (")[0]
    return re.sub(r"\s[LR](?=\s|$|\()", "", n)


def grouped_notes(man, tag):
    """[(name, text, count)] for every part-note segment with this tag; parts whose texts differ only in numbers are one row."""
    rows = collections.OrderedDict()
    for p in man["parts"]:
        for (t, txt) in note_segments(p.get("note")):
            if t != tag or not txt:
                continue
            k = (_base_name(p["name_ko"]), re.sub(r"-?\d+(\.\d+)?", "#", txt))
            if k not in rows:
                rows[k] = [p["name_ko"].split(" (")[0], txt, 0, set()]
            rows[k][2] += 1
            rows[k][3].add(txt)
    return [(n, t, c, len(v)) for (n, t, c, v) in rows.values()]


def _pig_out(man):
    """pigtail length outside the pod, from the C-SPKPIG-L note ('스피커 밖 N mm')."""
    g = next((p for p in man["parts"] if p["id"] == "C-SPKPIG-L"), None)
    m = re.search(r"스피커 밖 ([\d.]+) mm", (g or {}).get("note") or "")
    return float(m.group(1)) if m else 0.0


def _elec():
    """electronics.py with its C25 route computed (build() fills E.C25; build_all has normally done it in this process)."""
    import electronics as E_
    if not E_.C25:
        E_.build()
    return E_


def quickserts_line():
    B = body
    reach = B.CU_IX[0] + B.SLV[2] - B.SPK_X["L"][1]
    return ("구매 목록 v4 L72·L74 (스피커 ↔ 가운데 결합): 손잡이볼트 M4×20 (L72, 머리 Ø8 × 6) 4 — 슬리브 끝에서 이음면까지 %s라 인서트에 %s 물림 "
            "(M4×22면 %s = 인서트 길이, 끝이 구멍 바닥 %s 위; %s보다 길면 끝이 구멍 바닥을 누름 → **최대 M4×22**) + 고무 슬리브 = 연료 호스 OD%s × ID%s "
            "(13 mm로 4개, 끝벽 Ø8 구멍에 꽉 낌). **2026-10-07: L73 Norelem 나사산 인서트는 안 씀** — 스피커 안쪽 옆판을 출력하므로 사용자 열 인서트 세트의 "
            "**M4 황동 열압입 인서트 바깥 Ø%s × 길이 %s 4개**를 출력 구멍 Ø%s × %s (막힘, 앞판 L69 인서트와 같은 규칙)에 인두로 이음면까지. 구멍 바닥 뒤 PETG %s "
            "(밀폐 기준 %s 이상) — 드릴·깊이 멈춤 없음"
            % (f(reach, 0), f(B.TS_LEN - reach, 0), f(22.0 - reach, 0), f(B.INS_HOLE[1] - (22.0 - reach), 1), "M4×%s" % f(reach + B.INS_HOLE[1], 1),
               f(B.SLV[0], 0), f(B.SLV[1], 1), f(B.INS[0], 0), f(B.INS[2], 0), f(B.INS_HOLE[0], 1), f(B.INS_HOLE[1], 1), f(B.T - B.INS_HOLE[1], 1),
               f(B.INS_BACK_MIN, 1)))


def upstream_line():
    E_ = _elec()
    g = E_.C25
    return ("구매 목록 v4 C25 (Coms NA977, USB-A **위로 꺾임** → USB-B 곧음, 커넥터 포함 250 mm): 모델이 제품 방향대로 — A 머리는 Pi 5 GPIO 쪽 USB-A 2단의 "
            "**아래 포트**(위로 꺾인 머리가 포트 축에서 %s 올라감: 위 포트면 끝이 z%s라 뚜껑 밑 z%s까지 %s뿐, 선을 꺾을 수 없음; 아래 포트면 끝 z%s, 위 포트는 "
            "머리에 가려 못 씀 — 남는 USB-A는 RJ45 옆 2단의 위 포트). 선은 위로 나와 z%s(화면 전원선 밑 %s)로 허브 선반 위에 납작한 U자(x%s까지)를 그리고 "
            "내려와 허브 −x 끝면의 업스트림 B 포트(y%s z%s)에 곧은 B 플러그(%s mm)로. 길이 A %s + 선 %s + B %s = %s. '위로'는 Pi 포트에서 확인 "
            "(아래로 꺾이는 선은 머리가 바닥에 닿아 못 씀)"
            % (f(g["z_top"] - g["za"], 1), f(g["za"] + 8.4 + g["z_top"] - g["za"], 1), f(E_.Z_LIDU), f(E_.Z_LIDU - (g["za"] + 8.4 + g["z_top"] - g["za"])),
               f(g["z_top"], 1), f(E_.C25_LOOP_Z, 1), f(59.6 - E_.C25_LOOP_Z - E_.UP_D / 2, 1), f(g["x_far"] + E_.UP_D / 2, 0), f(E_.C25_B_PORT[0], 0),
               f(E_.C25_B_PORT[1], 1), f(E_.C25_B_BODY[0] + E_.C25_B_BOOT[0], 0), f(g["a_len"], 0), f(g["cable"], 0), f(g["b_len"], 0), f(g["len"], 0)))


def pipower_line():
    E_ = _elec()
    h, z = E_.C24_HEAD, E_.CC["Z-PI-PWR"]
    return ("구매 목록 v4 C24 (Coms BT663, USB-C **옆으로 꺾임** 20 cm, A 쪽을 잘라 빨강·검정을 강압 출력에): 꺾인 머리(사진 비례 추정 %s × %s × %s)가 "
            "사양 지킴 자리 Z-PI-PWR (x%s~%s y%s~%s z%s~%s) 안에 들어감 — 선이 −x(강압 쪽)로 나오게 꽂음 (USB-C는 뒤집으면 +x). "
            "받으면 머리가 x 방향 14보다 길지 않은지 잼 (선이 −x로 나가므로 머리가 길면 −x 쪽으로 늘어남 - x540~546도 비어 있어 18 mm 머리까지 들어감). "
            "**2026-10-26 (사용자: 둘 다 일자):** Pi 5를 건반 쪽으로 **%s mm** 옮겨(가운데 아랫판 가운데 조각만 다시 출력 - Pi 받침 기둥 4개는 같은 모양, 붙이는 자리만 9 앞으로) Pi 쪽 동글 젠더와 허브 DC "
            "플러그를 **둘 다 일자**로 씀 — C24 머리가 앞 공간 줄 y241에 닿아 %s가 최대. 허브 DC는 업스트림 B와 같은 −x 끝면(잭 y%s z%s)에 **곧은 DC 플러그**"
            "(몸 Ø%s, 모델 %s mm, 선은 바로 위로 R%s)로 모델 — 잭 면에서 몰드·부트 끝까지 **%s mm 이하**면 들어감 (더 길면 Pi 쪽 일자 젠더·C25 머리에 닿음 — "
            "check_electronics.py; 옮기기 전엔 %s mm). 허브의 딸린 어댑터 선 플러그를 그대로 쓰고, 길면 같은 규격 짧은 곧은 플러그 선을 사는데 그때 허브 잭의 "
            "**배럴 바깥/안 지름(5.5 × 2.1 / 5.5 × 2.5 / 3.5 × 1.35)과 배럴 길이**를 재서 맞춤. "
            "Pi의 동글 젠더는 **일자** USB-C(F)→USB-A(M) (2026-10-26 사용자, ㄱ자 IH190 대신): 포트 밖 길이 **%s mm 이하** (모델 %s, 흔한 짧은 젠더 약 14)"
            % (f(h[1] - h[0], 0), f(h[3] - h[2], 0), f(h[5] - h[4], 0), f(z[0], 0), f(z[1], 0), f(z[2], 0), f(z[3], 0), f(z[4], 0), f(z[5], 0),
               f(-E_.L2["centre"]["pi_move_2026_10_26"]["dy"], 0), f(-E_.L2["centre"]["pi_move_2026_10_26"]["dy"], 0), f(E_.HUB_DC_YZ[0], 0),
               f(E_.HUB_DC_YZ[1], 1), f(E_.HUB_DC_STRAIGHT[0], 0), f(E_.HUB_DC_PLUG_L, 0), f(E_.HUB_DC_STRAIGHT[1], 0), f(E_.HUB_DC_STRAIGHT_MAX, 1),
               "16.5", f(E_.GENDER_STRAIGHT_MAX, 1), f(E_.GENDER_STRAIGHT[0], 0)))


def extra_deviations(man):
    """spec adjustments the implementers wrote under '추정' in the notes (not tagged '사양과 다름'), with the model numbers."""
    B = body
    E_ = _elec()
    sz = {os.path.basename(r["file"]).split("__")[0]: r["size_mm"] for r in man["print"]}
    xt = " / ".join("%s %s" % (k[-1], " × ".join(f(v, 1) for v in sz[k])) for k in ("XT60집게_L", "XT60집게_R") if k in sz)
    MM = E_.mismate()
    return [
        ("방진 브래킷 BRK2", "그로밋이 끼는 세움 다리는 z%s~%s (사양은 판 z8~14만 적음): 6 mm 판에는 Ø6 그로밋(중심 z12, 자리 Ø6.5)이 들어가지 않음. "
         "핀을 받치는 판(팔)은 z8~14 그대로" % (f(B.BRK2_Z0), f(B.BRK2_LEG_TOP))),
        ("고무 슬리브", "끝벽만 지나감 (길이 %s, 가운데 쪽으로 %s 나옴) — 사양처럼 3 mm 틈까지 건너면 스피커를 들 때 아래 EVA 띠가 걸림. EVA 띠 구멍 Ø10은 "
         "나사가 실제로 띠를 지나는 곳에만" % (f(B.CU_IX[0] + B.SLV[2] - B.CU_X[0], 1), f(B.SLV[2], 1))),
        ("가운데 아랫판", "이음 기둥 자리(x500~512, 710~722)는 앞 모서리 R3 없음 (흡기 Ø8 구멍은 아래 '드릴 줄이기')"),
        ("뒤판 출력물", "루버 x%s~%s (사양 ~536): 옆 테 2 mm를 남김" % (f(B.BP_LOUV_X[0]), f(B.BP_LOUV_X[1]))),
        ("보드 받침", "사양 STANDOFFS(90 × 60 받침 판) 대신 낱개 기둥 14개 (보드에 먼저 나사, 기둥 밑을 아랫판에 MS 폴리머) — 흡기 홈을 막지 않음. "
         "앰프(HW-720) 3 mm 받침 4개와 앞 받침 밑 혀는 허브 선반과 한 몸"),
        ("XT60 집게 (2026-10-07, XT30 → XT60)", "XT60 암(15.8 × 8.2 × 16)을 세워 넣는 홈 %s × %s × %s (0.2씩 여유), 끝벽에 붙는 판 구멍 Ø%s, 판 앞 목 %s mm "
         "안은 45° 원뿔 (서포트 없음), 걸림 턱은 목 밖에만 (%s, 베드 위). 눕히면(y 16.2) L은 나비나사 머리와 배터리 사이에 들어가지 않아 세움"
         % (f(B.XT60_LF + B.XT60_CLR, 1), f(B.XT60_T + 2 * B.XT60_CLR, 1), f(B.XT60_W + 2 * B.XT60_CLR, 1), f(B.END_HOLE_D, 0), f(B.CLIP_COLLAR, 1), xt)),
        ("CU 화면 뚜껑", "터치스크린 3판(A장)을 더함: 리본·전원선 구멍 22 × 6 (x%s~%s y%s~%s, 사양 dsi 권장 자리 x580~602 대신 - 화면 커넥터가 +x 쪽), "
         "배기 홈 8 × (34 × 4) y300~325 (centre.vents.exhaust의 4 × 34 y292~326 대신 W1 3판 값), 갈비는 덩어리에 합침 (부록 A10)"
         % tuple(f(v) for v in B.SLID_RIBBON)),
        ("스피커 앞판·그릴", "유닛 나사 인서트는 구매 목록 L69 (ShenzenAV M4x4x6: 바깥 Ø%s × 길이 %s)를 구멍 Ø%s × %s에 인두로 면까지 (지름 %s 물림, 모델에 있음). "
         "M4×12(L70)는 플랜지 %s + 가스켓 %s을 지나 %s 들어가 인서트를 지나 %s 더, 끝은 구멍 바닥 %s 위. 그릴 판 아래 끝과 잘린 윗끝에 막힌 띠 2 mm, "
         "가장자리 칸은 Ø3 원이 들어가는 것만 뚫음 (W1 조건)"
         % (f(B.DRV_INS[0], 0), f(B.DRV_INS[2], 0), f(B.DRV_INSERT[0], 1), f(B.DRV_INSERT[1], 1), f(B.DRV_INS[0] - B.DRV_INSERT[0], 1), f(B.DRV_SCREW[1], 0),
            f(B.DRV_SCREW[2], 0), f(B.DRV_SCREW_IN, 0), f(B.DRV_SCREW_IN - B.DRV_INS[2], 0), f(B.DRV_INSERT[1] - B.DRV_SCREW_IN, 1))),
        ("케이블 집게 (사양 CABLE-CLIPS 8)", "사양에 자리가 없어 정함: 스피커 통로 지붕 밑 3개씩 (z19~27 y226~236, 묶음 위라 모델에서는 비어 있음) + 끝벽 L 안면 2개 "
         "(스피커선 C-SPK-L을 잡음, 선을 x275.1로 옮김). 출력 파일 하나 `케이블집게__8개`"),
        ("허브 선반 받침 나사", "8호 13 mm 대신 Ø3 × 12~13 둥근머리 목재 나사 (머리 Ø6 이하; 구매 목록 v4 L78 = 스텐 트러스 태핑 피스 M3 × 12) — 사양 받침 "
         "10 × 8에는 8호(Ø4.2, 머리 Ø8)가 들어가지 않음. 머리 자리 Ø%s × %s(받침 앞면 y%s부터)를 지나 뒤판(y%s~)에 물림 %s (M3 × 12) / %s (13 mm), 뒤판 "
         "바깥면까지 %s / %s 남음. 머리 자리 눈물방울 꼭지를 받침 윗면 0.8 아래에서 자름. 나사 축 z%s의 머리(아래 끝 z%s)가 선반 윗면 z%s보다 낮아, "
         "받침 앞 선반 윗면에 머리·드라이버 길 홈 %s × %s (선반 앞끝 y%s → 받침 y%s, 바닥 %s 남음)"
         % (f(SHELF_SEAT[0], 1), f(SHELF_SEAT[1], 0), f(B.CC["PR-SHELFBRK-1"][2], 0), f(B.YBI, 0), f(shelf_engage(12.0), 1), f(shelf_engage(13.0), 1),
            f(B.T - shelf_engage(12.0), 1), f(B.T - shelf_engage(13.0), 1),
            f(B.SHELF_SCREW_Z, 0), f(B.SHELF_SCREW_Z - 3.0, 1), f(B.CC["PR-HUBSHELF"][5], 1), f(B.SHELF_GROOVE[0], 0), f(B.SHELF_GROOVE[1], 1),
            f(B.CC["PR-HUBSHELF"][2], 0), f(B.CC["PR-SHELFBRK-1"][2], 0), f(B.CC["PR-HUBSHELF"][5] - B.CC["PR-HUBSHELF"][4] - B.SHELF_GROOVE[1], 1))),
        ("보드 받침 기둥 (5 mm)", "10/7: 나사 M3×5 → M3×6, 구멍 깊이 4.0 (바닥 1.0) → 관통 5 — 끝이 아랫판 위 0.6. Pi는 M2.5×6 (구멍 Ø2.2 × 5, 바닥 1.0) 그대로"),
        ("뒤판 출력물 바닥 탭", "2026-10-07 배터리로 바뀌어 탭 2개 (왼쪽 x400~414 = 배터리 밑, 오른쪽 x452~474 + 앞으로 낸 혀 = 90° 돌린 PED 보드 밑) 대신 "
         "탭 하나 x%s~%s y%s~ 에 접시 8호 13 두 개 (%s, %s) · (%s, %s) — 배터리(x≤424)와 J501 받침 사이, 드라이버 Ø6 길은 KCD1 단자 왼쪽 1.6 · J501 받침 왼쪽 "
         "0.5 (받침 왼쪽 끝을 J501 기판 끝 x%s에 맞춤). 배터리 뒤(y323~331)에 나사를 두면 아랫판 뒤 모서리에서 4 이하라 쪼개짐. 받침 버팀벽·혀는 없앰. "
         "USB-C PD 입력 주머니와 케이블 통과 Ø12는 막힌 벽"
         % (f(B.BP_TABS[0][0], 0), f(B.BP_TABS[-1][1], 0), f(B.BP_TAB_Y0, 0), f(B.BP_TABS[0][2], 1), f(B.BP_TABS[0][3], 0), f(B.BP_TABS[1][2], 1),
            f(B.BP_TABS[1][3], 0), f(B.CC["CU-E-J501BOARD"][0], 0))),
        ("배터리 틀 (2026-10-07)", "보조배터리 받침·퓨즈 받침 대신 출력 하나: LiFePO4 둘레 벽 1.5 × 14 (0.5 틈, 받침 바닥 없음 - 배터리가 아랫판 위), +x 끝은 "
         "모서리 8만 남기고 열림 (선 두 개가 나오는 끝, 가정), 끈 구멍 22 × 3 앞·뒤 (x%s~%s), 나사 4 = 왼쪽 귀 2 (옛 받침 귀 자리) + 앞 낮은 덩어리의 Ø9 구멍 "
         "바닥 2 (y246 = 아랫판 앞 모서리에서 5.0), 앞에 퓨즈 선반 x%s~%s (사용자 ATC/ATO 퓨즈 홀더를 옆으로 눕혀 놓고 양끝 선 꼭지 Ø8을 받침 2개에 눌러 "
         "끼움; 앞 공간 위 z27 이상, 밑면 y·x 모두 45°). XT60 짝과 DC 충전 커넥터는 배터리 윗면에 눕힘 (뚜껑 밑 "
         "1.65 / 1.35). PED 보드는 90° 돌려 x426.5~476.5 (선 꺾는 자리 z30 위를 비움). 스피커선 L은 끝벽을 따라 앞까지 와서 XT60 집게 판 위 z%s로 "
         "(옛 길은 배터리 자리)" % (f(B.BF_STRAP_X[0], 0), f(B.BF_STRAP_X[1], 0), f(B.FS_X[0], 0), f(B.FS_X[1], 1), f(E_.SPKL_HIGH_Z, 1))),
        ("퓨즈 홀더 (2026-10-07)", "Coms BU914 (5×20 유리관) 대신 사용자 것 ATC/ATO 칼날형 인라인 홀더 + 5 A ATO 퓨즈, 12 AWG 빨간 선. 크기는 사용자 제품 도면 "
         "40.1 (선 꼭지 포함) × 11.1 × 33.8 (덮개 포함), 덮개는 곧게 위로 약 20 뽑음. 세우면 33.8 + 20이 앞 공간 높이(z27~61.35, 34.35)에 들어가지 않아 "
         "옆으로 눕힘: 앞 공간 위 x%s~%s y%s~%s z%s~%s, 선 축 x, 덮개 +y (배터리 쪽). 덮개를 -y로 두어도 앞이 건반 모듈 뒷벽이라 그 자리에서는 뽑을 수 "
         "없음. 퓨즈 갈기: 뚜껑 L을 들고 홀더를 받침에서 위로 빼서 선 축으로 90° 돌려 덮개를 위로 뽑음 (홀더 위는 뚜껑까지 비어 있음). 12 AWG 꼬리는 양끝에서 "
         "R15로 +y로 꺾여 약 %s mm 뒤 16 AWG와 이음 (납땜 + 수축 튜브)"
         % (f(B.FH_BOX[0], 0), f(B.FH_BOX[1], 1), f(B.FH_BOX[2], 1), f(B.FH_BOX[3], 1), f(B.FH_BOX[4], 0), f(B.FH_BOX[5], 1),
            f(E_.LENGTHS["PWR-IN-12"], 0))),
        ("드릴 줄이기 (2026-10-07, 사용자 '드릴을 써야되는 부분을 최소한으로')", "뚜껑 L·R, 가운데 끝벽 L·R, 스피커 안쪽 옆판 L·R을 오꾸메 대신 PETG 출력 "
         "(같은 모양·두께·자리, 배기 홈·구멍·자석 자리·인서트 구멍이 출력에 있음; L73 인서트 대신 사용자 세트의 M4 열 인서트). 합판에 남은 환기는 Ø8 구멍 "
         "(가진 날, 간격 %s = 나무 %s): 뒤판 앰프 뒤 %d개 한 줄 x%s~%s z%s (전 홈 8 × 4×15, %s → %s mm²), 아랫판 강압 아래 %d · Pi 아래 %d "
         "(전 홈 14 × 4×34, %s → %s mm²). 합판 드릴 구멍 약 624 → %d (Ø8 관통 %d + 뒤판 윗모서리 자석 자리 %d)"
         % (f(B.VENT_PITCH, 0), f(B.VENT_WEB, 0), len(B.BACK_HOLES), f(B.BACK_HOLES[0][0], 0), f(B.BACK_HOLES[-1][0], 0), f(B.BACK_HOLES[0][1], 1),
            f(B.OLD_SLOT_AREA["back"], 0), f(len(B.BACK_HOLES) * math.pi * B.VENT_D ** 2 / 4, 0), len(B.BOT_HOLES_BUCK), len(B.BOT_HOLES_PI),
            "{:,.0f}".format(B.OLD_SLOT_AREA["bottom"]), "{:,.0f}".format((len(B.BOT_HOLES_BUCK) + len(B.BOT_HOLES_PI)) * math.pi * B.VENT_D ** 2 / 4),
            len(B.BACK_HOLES) + len(B.BOT_HOLES_BUCK) + len(B.BOT_HOLES_PI) + 4, len(B.BACK_HOLES) + len(B.BOT_HOLES_BUCK) + len(B.BOT_HOLES_PI), 4)),
        ("합판 없앰 (2026-10-16, 사용자 'A안: 합판 전부 출력')", "남은 오꾸메 10조각(스피커 바깥 옆판·뒤판·윗판·아랫판 L·R, 가운데 아랫판·뒤판)도 "
         "PETG 출력 (같은 모양·두께 %s·자리). 가운데 아랫판·뒤판은 베드보다 길어 x%s · x%s에서 반턱 이음(겹침 %s)으로 3토막씩. 환기 Ø8 구멍·자석 자리·나사 "
         "자리(Ø%s 안내 구멍, 끝은 45° 원뿔)가 모두 출력에 있어 드릴 0번, 합판 지그(08)·합판 재단·목공본드가 없어짐 (이음은 모두 MS 폴리머)"
         % (f(B.T, 1), f(B.SPLIT_X[0], 0), f(B.SPLIT_X[1], 0), f(B.LAP, 0), f(B.PILOT_D["foot"], 1))),
        ("전자부 단자 자리 (가정)", "강압 입력 −x 끝(y306)·출력 앞면(x529.5); 앰프(HW-720) 왼쪽(−x) 끝: 스피커 L 단자(뒤 y318)·DC 잭(가운데 y306, 12.8 V를 핀에 밑에서 납땜)·스피커 R 단자(앞 y291), 오른쪽 끝: XH 3핀 입력·볼륨; 허브는 W1 10/1 "
         "제품 사진대로 업스트림 USB 3.0 B 포트(y%s)와 DC 잭(y%s, 곧은 플러그 - 2026-10-26 Pi를 앞으로 옮긴 뒤)이 같은 −x 끝면 (사양: 업스트림 −x · DC +x). 끝면 안 자리는 받은 허브로 확인"
         % (f(E_.C25_B_PORT[0], 0), f(E_.HUB_DC_YZ[0], 0))),
        ("스피커 꼬리선", "XT60 암의 16 AWG 10 cm 선: 스피커 밖 %s mm, 여유 약 %s mm를 끝벽 Ø%s 터널 안에 %s바퀴 느슨하게 감아 둠, 나머지는 옆판 Ø6 구멍을 "
         "지나 상자 안에서 짧은 선(약 %s mm)과 이어 유닛 단자로 — 스피커를 %s mm 들고 %s mm 바깥으로 밀어도 암이 집게에 남고, 그다음 암을 터널로 빼냄 "
         "(check_body.py가 확인; XT60 암이 길이 16이라 바깥으로 미는 거리가 XT30 때 15 → 18). 두 가닥을 Ø3 한 줄로 표시"
         % (f(_pig_out(man), 0), f(B.PIG_SLACK_MM, 0), f(B.END_HOLE_D, 0), f(__import__("electronics").PIG_COIL[1], 1),
            f(__import__("electronics").LENGTHS.get("PIG-L", 0.0) - B.PIG_LEAD_MM, 0), f(B.POD_LIFT, 0), f(B.POD_SLIDE, 0))),
        ("홀 센서 높이 (D14)", "D14 거리를 사양의 z8이 아니라 홀 소자 높이 z%s (포켓 바닥 12.19 + 0.75)까지 잼 → 사양 %s / %s보다 1~2 mm 짧음 (≥100은 그대로)"
         % (f(B.SENSOR_YZ[1], 1), f(L2["speakers"]["d14"]["to_sensor_row_mm"], 1), f(L2["speakers"]["d14"]["nearest_steel_point_mm"], 1))),
        ("XT60 잘못 꽂기 막기 (2026-10-07)", "전원과 스피커가 같은 XT60이라 색으로 나눔: 전원 XT60(배터리 선 암, 하네스 수, 시험 전원 어댑터) = 빨간 수축 튜브, "
         "스피커 XT60(꼬리 암, 앰프 선 수) = 파란 수축 튜브 + 'SPK'. 하네스 수 선은 퓨즈 홀더 -x 끝에서 (12 AWG 꼬리 + 이음 포함) %s mm로 잘라 둠 — 스피커 집게에 꽂히려면 직선 %s (L) / "
         "%s (R) mm가 필요해 닿지 않음 (10 cm 그대로면 L에 닿음). 배터리 선 구역 → 집게 입구 %s (L) / %s (R) mm (check_electronics.py)"
         % tuple(f(v, 0) for v in (MM["cut"], MM["need"]["L"], MM["need"]["R"], MM["zone"]["L"], MM["zone"]["R"]))),
    ]


def deviations(man):
    """L2 small fixes against the spec, merged when the same fix is written on several parts. Parts whose texts differ only in
    their numbers (L / R mirror parts, the four moved feet) stay one group, but every distinct text is printed with its own parts -
    merging on the masked text alone printed only the first part's numbers (review 2026-10-01: end wall R z49.5 showed as z44)."""
    by = collections.OrderedDict()
    for p in man["parts"]:
        if p["id"].startswith("TS-"):
            continue                                                 # R31 touchscreen deviations: own list in the A10 section
        for (t, txt) in note_segments(p.get("note")):
            if t == "사양과 다름(작은 고침)":
                k = re.sub(r"-?\d+(\.\d+)?", "#", txt)
                by.setdefault(k, collections.OrderedDict()).setdefault(txt, []).append(p["name_ko"].split(" (")[0])
    out = []
    for variants in by.values():
        for txt, names in variants.items():
            u = list(collections.OrderedDict.fromkeys(names))
            out.append((" · ".join(u[:3]) + (" 외 %d" % (len(u) - 3) if len(u) > 3 else ""), txt))
    return out


# ------------------------------------------------------------------ plywood (L2 cut list)

PIECE_OF = [(r"^SPK[LR]-PLY-SIDE", "PLY-POD-SIDE"), (r"^SPK[LR]-PLY-BACK$", "PLY-POD-BACK"), (r"^SPK[LR]-PLY-TOP$", "PLY-POD-TOP"),
            (r"^SPK[LR]-PLY-BOTTOM$", "PLY-POD-BOTTOM"), (r"^CU-PLY-END-", "PLY-CU-END"), (r"^CU-PLY-BACK$", "PLY-CU-BACK"),
            (r"^CU-PLY-BOTTOM$", "PLY-CU-BOTTOM"), (r"^LID-L$", "PLY-CU-LID-L"), (r"^LID-R$", "PLY-CU-LID-R")]


def piece_of(pid):
    for rx, k in PIECE_OF:
        if re.search(rx, pid):
            return k
    return None


def _uv(yz):
    """(y, z) -> (u from the front edge y214, v from the bottom edge z5) on a side panel / end wall."""
    return "(u%s, v%s)" % (f(yz[0] - body.Y0, 1), f(yz[1] - body.ZB, 1))


SHELF_SEAT = (6.5, 4.0)        # body.hub_shelf: head seat D6.5 x 4 from the bracket front face (b[2] .. b[2] + 4)
BP_TAB_TOP = 20.5              # body.back_plate: bottom tabs z16.5..20.5, countersink in the tab top
CSK_LEN = 13.0                 # L77 countersunk 8호 13 mm (overall length = head flush with the printed face)
SLOT_W = 4.0                   # every okoume vent slot is 4 wide


def shelf_engage(screw_len):
    """hub-shelf bracket screw: thread in the centre back ply (mm) = bracket front + head seat + screw length - back-ply inner face."""
    return body.CC["PR-SHELFBRK-1"][2] + SHELF_SEAT[1] + screw_len - body.YBI


def slot_pitches():
    """slot pitch of each printed-lid slot row (one value per row, from body.py), None if a row is not evenly spaced."""
    B = body

    def p(rows, i):
        d = sorted(set(round(rows[k + 1][i] - rows[k][i], 3) for k in range(len(rows) - 1)))
        return d[0] if len(d) == 1 else None
    return collections.OrderedDict([("lidL", p(B.LIDL_SLOTS, 2)), ("lidR", p(B.LIDR_SLOTS, 0))])


def vent_rows(holes):
    """[(row coordinate, [first, last], count, pitch)] of a D8 grid: rows by the second coordinate."""
    rows = collections.OrderedDict()
    for (a_, b_) in sorted(holes, key=lambda h: (h[1], h[0])):
        rows.setdefault(b_, []).append(a_)
    return [(k, v[0], v[-1], len(v)) for k, v in rows.items()]


def csk_spots():
    """[(what, (x, y), tip above the ply bottom face)] of the L77 countersunk 8호 13 screws driven from above into the centre bottom ply.
    body.wood_screws() (the model's screw table, if this body.py has one) is used first; otherwise the back-plate tabs + holder screws."""
    B = body
    ws = getattr(B, "wood_screws", None)
    if callable(ws):
        try:
            out = [(re.sub(r"[\s_-]*\d+$", "", str(s.get("label", "접시 8호 13"))), (float(s["at"][0]), float(s["at"][1])), float(s["tip"]) - B.ZB)
                   for s in ws() if s.get("ply") == "CU-PLY-BOTTOM" and s.get("dir", 0) < 0]
            if out:
                return out
        except Exception:                                       # body.py mid-edit / other schema: fall back to the constants
            pass
    tab = [("뒤판 출력물 탭", (sx, sy), BP_TAB_TOP - CSK_LEN - B.ZB) for (_, _, sx, sy) in B.BP_TABS]
    return tab + [("배터리 틀", xy, getattr(B, "BF_HEAD_Z", BP_TAB_TOP) - CSK_LEN - B.ZB) for xy in getattr(B, "BF_SCREWS", [])]


def ply_work(piece):
    """what to cut by hand on each cut-list piece (u = back from the front edge, v = up from the bottom edge, x from the left end)."""
    B = body
    un, vn = B.DUCT_Y[1] - B.Y0, B.DUCT_Z[1] - B.ZB
    if piece == "PLY-POD-SIDE":
        return ("바깥 옆판 2장만 (안쪽 2장은 10/7부터 출력). 사각으로 받은 뒤 직접 자름 (앞 모서리에서 뒤로 u, 아래 모서리에서 위로 v): ① 앞 아래 통로 홈 %s × %s 따냄 "
                "② 앞 모서리는 v%s까지 두고, 거기서 수평으로 %s 들어간 점 (u%s, v%s)부터 윗변 u%s까지 %s° 사선 (사선 길이 %s, 윗변에 남는 길이 %s). 구멍 없음"
                % (f(un, 1), f(vn, 1), f(B.Z_FB - B.ZB), f(B.SL_A[0] - B.Y0), f(B.SL_A[0] - B.Y0), f(B.Z_FB - B.ZB), f(B.SL_B[0] - B.Y0),
                   f(B.ANGLE, 1), f(B.SL_LEN), f(B.YB - B.SL_B[0])))
    if piece == "PLY-POD-BACK":
        return "없음 (옆판 사이). 안쪽에 흡음솜을 두되 자석 뒤 폴 벤트 축 방향 10 mm는 비움 (W1)"
    if piece == "PLY-POD-TOP":
        return "없음. 앞 모서리(y%s)는 출력 앞판 윗마개에 맞댐" % f(B.TOP_Y0)
    if piece == "PLY-POD-BOTTOM":
        fl = [xy for g, xy, _ in B.foot_positions() if g == "스피커 L"]
        xs = sorted(set(round(x - B.SX0, 1) for x, y in fl))          # from the outer (-x) end of the L bottom; R is the mirror
        ys = sorted(set(round(y - B.RISER[0], 1) for x, y in fl))
        return ("없음. 밑면 고무발 나사 자리 4 (8호 13 mm 이하, L49): 바깥 끝에서 %s, 앞 모서리에서 %s (발 Ø28이 옆판 밑까지 나옴; 사양 2.5는 나사가 끝면에 "
                "너무 가까워 옮김). 밀폐 상자 바닥이라 구멍에 MS 폴리머 한 방울"
                % ("·".join(f(v, 1) for v in xs), "·".join(f(v, 1) for v in ys)))
    if piece == "PLY-CU-BACK":
        x0 = B.CU_X[0]
        h0, h1 = B.BACK_HOLES[0], B.BACK_HOLES[-1]
        shelf = [((b[0] + b[1]) / 2.0, B.SHELF_SCREW_Z) for b in (B.CC["PR-SHELFBRK-1"], B.CC["PR-SHELFBRK-2"])]
        return ("뒤판 출력물 창: 왼쪽 끝에서 %s~%s (폭 %s), 아래 모서리에서 %s 위부터 윗변까지 (위가 열림) — 톱으로 두 번 세로 자르고 가로로 따냄; "
                "앰프 뒤 환기 Ø%s 관통 %d개 한 줄 (중심: 왼쪽 끝에서 %s~%s, 간격 %s, 아래에서 %s — 지그 J-d3, 오른쪽 끝·윗모서리에 댐); "
                "윗모서리 자석 자리 Ø8 × 3.2 4곳 (왼쪽 끝에서 %s — J-b 새들); "
                "안쪽 면 허브 선반 받침 나사 자리 %d (L78 M3 × 12 트러스 태핑: 왼쪽 끝에서 %s, 아래 모서리에서 %s — 받침을 대고 받침 구멍 Ø3.4로 조임, "
                "합판 물림 %s, 바깥면까지 %s 남음)"
                % (f(B.BP_X[0] - x0), f(B.BP_X[1] - x0), f(B.BP_X[1] - B.BP_X[0]), f(B.Z_BOT - B.ZB), f(B.VENT_D, 0), len(B.BACK_HOLES),
                   f(h0[0] - x0), f(h1[0] - x0), f(B.VENT_PITCH, 0), f(h0[1] - B.ZB),
                   "·".join(f(x - x0) for s in "LR" for x in B.MAG_BACK_X[s]),
                   len(shelf), "·".join(f(x - x0) for x, z in shelf), "·".join(sorted(set(f(z - B.ZB) for x, z in shelf))),
                   f(shelf_engage(12.0), 1), f(B.T - shelf_engage(12.0), 1)))
    if piece == "PLY-CU-BOTTOM":
        x0 = B.CU_IX[0]
        bk, pi = vent_rows(B.BOT_HOLES_BUCK), vent_rows(B.BOT_HOLES_PI)
        fl = [xy for g, xy, _ in B.foot_positions() if g == "가운데 유닛"]
        cs = csk_spots()
        by_w = collections.OrderedDict()
        for (w, xy, tip) in cs:
            by_w.setdefault(w, []).append((xy, tip))
        csk = ", ".join("%s %d (%s; 끝은 판 밑면 %s 위)" % (w, len(v), " · ".join("%s/%s" % (f(x - x0), f(y - B.RISER[0])) for (x, y), _ in v),
                                                       "/".join(sorted(set(f(t_, 1) for _, t_ in v)))) for w, v in by_w.items())
        rows_t = lambda rs: " / ".join("앞 모서리에서 %s: %d개 %s~%s" % (f(y - B.RISER[0]), n, f(a_ - x0), f(b_ - x0)) for (y, a_, b_, n) in rs)
        return ("앞 윗모서리 R3 (이음 기둥 자리 왼쪽 끝에서 %s는 빼고); 흡기 Ø%s 관통 %d개 (지그 J-d4 — 뒤 모서리 + 왼쪽 끝에서 %s 연필선; 간격 %s, 중심을 "
                "왼쪽 끝에서 잼): 강압 아래 %d (%s), Pi 아래 %d (%s); 윗면 접시머리 8호 13 mm (L77) 나사 자리 %d (왼쪽 끝·앞 모서리에서): %s — 출력물을 "
                "제자리에 놓고 그 접시 구멍으로 조임; 밑면 고무발 나사 자리 %d (8호 13 mm, L49): 왼쪽 끝에서 %s, 앞 모서리에서 %s"
                % (" · ".join("%s~%s" % (f(a - x0), f(b - x0)) for a, b in B.FILLET_SKIP), f(B.VENT_D, 0), len(B.BOT_HOLES_BUCK) + len(B.BOT_HOLES_PI),
                   f(200.0, 0), f(B.VENT_PITCH, 0), len(B.BOT_HOLES_BUCK), rows_t(bk), len(B.BOT_HOLES_PI), rows_t(pi), len(cs), csk, len(fl),
                   "·".join(f(v) for v in sorted(set(x - x0 for x, y in fl))), "·".join(f(v) for v in sorted(set(y - B.RISER[0] for x, y in fl)))))
    return ""


def plywood_rows(man):
    """[(piece id, name, qty, model blank (a, b), spec blank, parts)] in cut-list order."""
    spec = collections.OrderedDict((p["id"], p) for p in L2["plywood_cut_list"]["pieces"])
    got = collections.OrderedDict((k, []) for k in spec)
    other = []
    for p in man["parts"]:
        if p["kind"] != "plywood":
            continue
        k = piece_of(p["id"])
        (got[k] if k in got else other).append(p)
    rows = []
    for k, ps in got.items():
        if not ps:
            continue
        dims = set()
        for p in ps:
            b = p["bbox"]
            d = sorted([round(b[3] - b[0], 2), round(b[4] - b[1], 2), round(b[5] - b[2], 2)], reverse=True)[:2]
            dims.add(tuple(d))
        lo, hi = sorted(sorted(dims)[-1])                               # the largest blank among the parts of this piece
        sb = tuple(spec[k]["blank_mm"])
        mb = (lo, hi) if sb[0] <= sb[1] else (hi, lo)                   # same orientation as the spec blank
        if all(abs(x - y) < 0.05 for x, y in zip(mb, sb)):
            mb = sb
        rows.append((k, spec[k]["name"], len(ps), mb, sb, ps))
    return rows, other


def nesting_check(rows):
    """re-place the spec 400 x 1200 nesting with the MODEL blank sizes; (fits, used w, used h)."""
    nest = L2["plywood_cut_list"]["nesting_400x1200"]
    blank = {k: mb for (k, n, q, mb, sb, ps) in rows}
    spec_blank = {p["id"]: p["blank_mm"] for p in L2["plywood_cut_list"]["pieces"]}
    rects = []
    for (pid, x, y, w, h) in nest["layout_xywh"]:
        a, b = blank.get(pid, (w, h))
        sa, sb_ = spec_blank.get(pid, (w, h))
        if abs(w - sa) < abs(w - sb_):        # same orientation as the spec blank
            rects.append((pid, x, y, a, b))
        else:
            rects.append((pid, x, y, b, a))
    ok = all(x + w <= 1200.0 + 1e-6 and y + h <= 400.0 + 1e-6 for (_, x, y, w, h) in rects)
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            _, x1, y1, w1, h1 = rects[i]
            _, x2, y2, w2, h2 = rects[j]
            sep = max(x2 - (x1 + w1), x1 - (x2 + w2), y2 - (y1 + h1), y1 - (y2 + h2))
            if sep < nest["kerf"] - 0.1:
                ok = False
    return ok, max(x + w for (_, x, y, w, h) in rects), max(y + h for (_, x, y, w, h) in rects)


# ------------------------------------------------------------------ fixed text

NOT_MODELLED = [
    ("홀센서 DRV5055A2QLPG, 저항·커패시터, 핀 헤더, 납땜 패드", "88 + α", "회로 부품 (요청대로 생략). 센서 자리는 센서 바 포켓으로 표시"),
    ("스텐 직결피스 8호 13 mm 둥근머리 (L49)", "14", "고무발 14 (L2). 고무발은 25 mm가 아니라 13 mm 이하 — 16 mm 이상은 스피커 밀폐 바닥을 뚫음"),
    ("스텐 트러스 태핑 피스 M3 × 12 (L78; 모델은 Ø3 × 12~13 둥근머리, 머리 Ø6 이하)", "2",
     "허브 선반 받침 2개를 뒤판에 (받침 10 × 8에 8호가 들어가지 않음). 구멍 Ø3.4·머리 자리 Ø%s × %s는 모델에 있음. 뒤판에 %s 물림 (13 mm면 %s). "
     "구매 목록 v4 L78 (최종 재료 i220, 2 + 예비 2) — 트러스 머리 약 Ø6이라 받으면 머리 자리에 들어가는지 확인"
     % (f(SHELF_SEAT[0], 1), f(SHELF_SEAT[1], 0), f(shelf_engage(12.0), 1), f(shelf_engage(13.0), 1))),
    ("스텐 직결피스 8호 13 mm 접시머리 (L77)", "%d" % len(csk_spots()),
     "%s → 가운데 아랫판. 구멍(접시 자리)은 모델에 있음. 구매 목록 v4 L77 (최종 재료 i219, 6 + 예비 2)"
     % " + ".join("%s %d" % (w, n) for w, n in collections.Counter(w for w, _, _ in csk_spots()).items())),
    ("스텐 직결피스 8호 19 mm (L49)", "8", "그릴 4 × 2 (W1: 떨리지 않게 4개 모두). 25 mm는 앞판 아래 파일럿 끝 2.15 밑 밀폐면을 뚫음 — 19 mm 이하"),
    ("M4×12 유두 렌치볼트 (L70)", "8", "스피커 유닛을 출력 앞판의 L69 인서트(모델에 있음)에. 플랜지 4 + 가스켓 3을 지나 5 들어가 인서트 4를 지나 1 더, "
     "끝은 구멍 Ø5.6 × 6.5 바닥 1.5 위. 인서트는 면까지만 넣고 나사는 M4×12 이하 — 아래 구멍 밑 밀폐면이 2.78"),
    ("보드 나사: M2.5×6 자가 탭 (Pi 5), M3×6 자가 탭 (강압 4·J702 2·PED 2), M3×6 자가 탭 (앰프 4)", "4 / 8 / 4",
     "받침 기둥 구멍은 Pi Ø2.2 × 5 (바닥 1.0), 나머지는 관통 5 (끝이 아랫판 위 0.6) — M3×8 이상은 아랫판에 닿아 기둥을 밀어 올림. 앰프는 받침 + 선반 관통"),
    ("AUX 3.5 mm 선 2가닥 W701/W702 (볼 헤드폰 잭 ↔ 동글·J702), 페달 선, 배터리 끈 (벨크로 L79), 충전기 플러그", "—",
     "경로는 조립 때 정해짐. 플러그 자리(Z-J702-PLUG·Z-DONGLE-PLUG)와 배터리 선 꺾는 자리(Z-BAT-LEADS)가 비어 있는 것은 check_electronics.py가 확인. "
     "모듈 USB 선, 배터리 선 2 (XT60·DC 충전), XT60 짝, DC 충전 커넥터, 전원선(XT60 → 퓨즈 홀더 (12 AWG 꼬리 + 이음) → KCD1 → 12.8 V · 5.1 V), 스피커선, 스피커 꼬리선, 스피커 XT60 짝, 리본, "
     "EXT 선, JST-XH는 모델에 있음"),
    ("흡음솜(폴리에스터), 부싱 천 0.5T (노치·핀 홈·탭 옆), 종이 펀칭, PET 심, MS 폴리머", "—",
     "두께가 출력 치수에 이미 들어 있음(노치 R2.55 → 천 뒤 R2.05). 흡음솜 조건은 아래 'W1 음향 조건'"),
]

BUY_GAPS = [
    "M3×20 십자 둥근머리 볼트 4개 + M4 와셔 (방진 브래킷 BRK2, 10/7 M3×16 대신, 볼 구멍을 y199까지 늘림): M3×10은 볼 속 너트에 닿지 않음",
    "QUICKSERT",
    "구매 목록 v4에 있음 — L69 M4 열압입 인서트 (ShenzenAV M4x4x6, 바깥 Ø6 × 4) 8 + 예비 2와 L70 M4×12 8 + 예비 2: 스피커 유닛을 출력 앞판에 "
    "(L1의 직결피스 8호 16 mm 대신). 모델 인서트도 Ø6 × 4 (구멍 Ø5.6 × 6.5 그대로, 지름 0.4 물림)",
    "10/7: M3 열압입 인서트는 M3 바깥 5 × 높이 4 (L71 ShenzenAV M3x4x4.5 대신) 4개 = 화면 뚜껑 이음 레일 4. 모델 인서트 Ø5 × 4 "
    "(구멍 Ø4.0 → Ø4.2 × 4.5, 지름 0.8 물림; 길이 4 = 자리파기 계산 값 그대로). M3×10 4개는 기존 줄",
    "터치스크린 3판 부품은 구매 목록 v4에 있음 (135 화면 Waveshare 7-DSI-TOUCH-C, 49 GUOCONN 22P 0.5 mm 300 mm B형 + 50 A형 보험, 51~54 실리콘 점퍼 "
    "F/F·M/M 빨강·검정 20 cm, 75 M3×20 × 4, 76 M2.5×6 × 4) — 모델과 개수가 같음. 글만 고칠 것: 49줄 '경로 약 271 mm(여유 29)' → 모델 254 / W1 계산 256 "
    "(여유 약 44); 62줄 M3×10 설명의 'R31 CU 뚜껑 앞 모서리 2곳'은 L2에서 화면 뚜껑 4개(레일 인서트)",
    "캡톤테이프(26줄)를 화면 받침 안 리본 누름 패드 자리(xr26.75~39.45 u8~16)에도 씀 (사양 C-7)",
    "TOUCH_PETG",
    "열수축튜브: Waveshare MX1.25→2.54 3핀 선이 120.54 mm보다 짧으면 3핀 이음이 경첩 고리 안에 오므로 감쌈 (사양 G-4, 22 × 6 구멍 통과)",
    "USB_CABLES",
    "전원 (2026-10-07 사용자 결정, 2026-10-26 같은 꼴로 바꿈): LiFePO4 12.8 V 6 Ah 배터리 (4S1P 32700 '12.8V 10Ah DCXT60-3A', 140 × 35 × 72, 약 900 g, "
    "BMS 4S 40 A, XT60 선 + DC 5.5×2.1 충전 선)와 세트의 3 A LiFePO4 충전기는 사용자가 따로 삼 — 구매 목록은 hardware/bom 담당. 버스 쪽 **XT60 수 커넥터 1개**(16 AWG 선, 퓨즈 홀더 12 AWG 꼬리에 납땜 이음)가 필요함 - 목록에 있는지 확인. "
    "퓨즈 홀더는 사용자 것 ATC/ATO 칼날형 + **5 A ATO 칼날 퓨즈** (2026-10-07, Coms BU914·5×20 퓨즈 대신 - 목록에서 빼는지는 hardware/bom 담당). "
    "12 V 전원 장치로 시험하려면 그 선 끝에 XT60 암",
    "UPSTREAM",
    "PIPOWER",
    "흡음솜 (폴리에스터): 스피커 상자마다 약 35 g을 상자 전체에 느슨하게 (W1). 기존 줄 양으로 되는지 확인",
    "구매 목록 v4에 있음 — L79 (최종 재료 i221) 벨크로 링벨트 20 mm × 30 cm 1개: LiFePO4 배터리를 배터리 틀 앞·뒤 벽 아래의 끈 구멍 22 × 3 "
    "(x304~326)으로 밑·위를 감아 묶음 (둘레 약 230 mm)",
    "센서 바 나사는 버튼헤드(머리 1.65)로: 캡볼트면 눌린 C·A0·C8 건반 밑과 0.48",
]

DROPPED = [
    "토글 래치 매미고리 L64 × 2 (−4,800원): 도브테일 블록과 함께 없어짐",
    "오꾸메 합판 (400 × 1200 한 장 17,680원, 600 × 1200은 −22,520원)과 목공본드: 2026-10-16 A안 - 판을 모두 출력",
    "직결피스 8호 16 mm (스피커 유닛 4 × 2): M4 인서트 + M4×12로 바뀜. 8호 13 mm 둥근머리는 L1 46개 → L2 14개",
    "L1 출력물: CU 트레이, CU 뚜껑 v2, 모서리 받침 12, 예비 건반 칸막이, 작은 부품 상자(+뚜껑), 도브테일 블록 4, XT30 받침 2, L1 브래킷 2, I/O 판 "
    "→ PETG 양은 대략 같음 (사양: L2 뒷바 출력물 약 1.1 kg, 모자라면 1 kg 스풀 +16,150원)",
    "R31 공식 Touch Display 2와 그 받침(2판): 사용자가 Waveshare 7-DSI-TOUCH-C로 바꿈 (2026-10-01). 3판 부품은 아래 '터치스크린 3판' 구매 줄",
    "R31 2판의 FIT0997 22→15핀 리본: 3판은 22핀 ↔ 22핀 GUOCONN FFC (구매 목록 v4 49·50줄)",
    "USB-C PD 전원 (2026-10-07): HUSB238 PD 트리거 (L57), 65 W PD 충전기, 모루이 MT-65 보조배터리(선택 O07), ㄱ자 USB-C to C 0.3 m — LiFePO4 배터리로 "
    "바뀌어 쓰지 않음 (사양 bom_changes의 +2,060원 줄은 0으로). 출력물 보조배터리 받침·퓨즈 받침도 배터리 틀 하나로",
    "Coms BU914 인라인 퓨즈 홀더 + 5×20 5 A T 퓨즈 (2026-10-07): 사용자 ATC/ATO 칼날형 홀더 + 5 A ATO 퓨즈로 바뀌어 쓰지 않음",
    "사양 bom_net_krw: %s원 (위 추가분 포함)" % format(L2["bom_net_krw"], ",").replace("-", "−"),
]

KEY_ORDER_NOTES = [
    "건반 모듈은 서로 도브테일(뿌리 6 → 끝 9, 깊이 4, 암은 밑이 열림)로 위에서 내려 끼웁니다. 뒤 꼬리는 높이 14라 빼려면 약 14 mm 들어야 합니다. "
    "모듈은 도브테일 때문에 위로만 빠지므로 앞으로 밀지 않습니다.",
    "제어 기판(BE163 80 × 120 통째로, A16)은 센서 기판·리본과 함께 납땜한 뒤 바닥틀 자리(받침 리브 위, 둘레 턱 틈 0.3)에 내려놓고, 따로 출력한 밸런스 레일을 "
    "그 위에 얹어 양 끝 깊은 구멍으로 M3×6 2개를 받침에 조입니다 - 레일 밑면이 판의 빈 띠(y132.3~144.5)를 눌러 판도 잡습니다. 그다음 건반 봉·건반, 레버틀 순서입니다.",
    "강철 블록은 칸 길이 40.0에 딱 맞으므로 40 −0.1/−0.3으로 자르고 두께 8.9~9.1만 씁니다. 캐리어 칸 속 떼는 지지대는 먼저 떼어 냅니다.",
    "스프링은 레버 봉을 넣기 전에 짧은 다리 끝부터 허브 가둠 홈으로 밀어 넣습니다(DESIGN 1f). 긴 다리는 뒷벽 보스의 홈(2.4 × 3.2)으로 밑에서 들어갑니다.",
]


def touch_petg_line(man):
    rows = [r for r in man["print"] if r["folder"].startswith("07")]
    need = sum(r["mass_g_solid_petg"] * r["qty"] for r in rows if "선택" not in r["name"])
    opt = sum(r["mass_g_solid_petg"] * r["qty"] for r in rows if "선택" in r["name"])
    return ("PETG: 07_터치스크린 출력물 약 %s g (속 꽉 채움 기준, 선택 화면 덮개 %s g 별도) + 화면 뚜껑(05) — 94줄 추가 1 kg 스풀 안에 들어감"
            % (f(need, 0), f(opt, 0)))


def usb_cable_line(man):
    """count the module / PED USB cables by their standard length (names carry '1.0 m' / '0.5 m' / '0.3 m')."""
    c = collections.OrderedDict()
    for p in man["parts"]:
        if p["id"].endswith("-C-USB") or p["id"] == "C-USB-PED":
            m = re.search(r"([\d.]+) m", p["name_ko"])
            who = p["id"].split("-")[0] if p["id"] != "C-USB-PED" else "PED"
            if m:
                c.setdefault(float(m.group(1)), []).append(who)
    parts = ["%s m × %d (%s)" % (f(k, 1), len(v), ", ".join(v)) for k, v in sorted(c.items(), reverse=True)]
    return ("USB-A→C 케이블 (NA993 계열) 길이별: " + ", ".join(parts) + " — L1의 1 m × 8 대신. 모델 길이는 ±30 mm 추정이라 사기 전에 끈으로 "
            "재 봄 (길이 = 플러그 25 + 경로 + 허브 플러그 35 ≤ 표준 − 40, 케이블마다 메모에 있음)")


def assembly_order(F):
    B = body
    pin = "L x%s · R x%s, y%s" % (f(B.PIN_XY["L"][0], 1), f(B.PIN_XY["R"][0], 1), f(B.PIN_XY["L"][1], 0))
    eh = B.END_HOLE_YZ
    MM = __import__("electronics").mismate()
    return [
        "**고무발** — 스피커 아랫판마다 4개, 가운데 아랫판 6개 (화성고무 28×5, 8호 **13 mm 이하**; 모두 통로 뒤 y≥248, 스피커 바깥 발은 사양 x−2/1224에서 "
        "x6/1216으로 옮김). 나사는 출력 아랫판의 안내 구멍(막힌 구멍)에 바로 조임. 스피커 아랫판은 밀폐 상자 바닥이므로 나사 구멍마다 MS 폴리머 한 방울 (16 mm 이상은 상자 안으로 뚫림).",
        "**스피커 상자 (책상 밖에서)** — 먼저 출력 안쪽 옆판(10/7부터 출력)의 인서트 구멍 Ø%s × %s 2곳에 M4 열 인서트(사용자 세트, 바깥 Ø%s × 길이 %s)를 인두로 "
        "이음면까지 곧게 (뒤 PETG %s, 구멍 바닥까지 밀지 않음). 바깥 옆판 + 아랫판 + 뒤판 + 윗판 + 안쪽 옆판(모두 출력)을 MS 폴리머로 잇고 (목공본드는 PETG에 안 붙음; 마스킹테이프로 눌러 굳힘), "
        "출력 통로 틀을 옆판 사이 앞에 넣어 세움벽 밑을 아랫판 앞 모서리"
        "(y241)에 붙임. 출력 앞판(%s°)을 앞벽·턱 위에 MS 폴리머로 붙이고 둘레를 밀봉한 뒤 새는 곳이 없는지 확인. 앞판 유닛 자리에 L69 인서트 4개 (인두, 면까지), "
        "통로 지붕 밑(z27)에 핀 소켓 블록 (%s)과 케이블 집게 3개, 바깥 옆판 홈에 통로 옆 마개. 스피커 꼬리선(XT60 암 16 AWG 10 cm, 파란 수축 튜브 + SPK; 상자 안에서 "
        "짧은 선과 납땜 + 수축 튜브로 이어 유닛 단자로)을 안쪽 옆판 Ø6 구멍으로 약 %s mm 빼고 본드로 밀봉. Ø94 구멍으로 흡음솜을 상자 전체에 느슨하게 넣고(유닛 뒤 10 mm·폴 벤트 축 10 mm는 비움), 유닛(가스켓 3T + M4×12 × 4 → 앞판 "
        "인서트; 더 긴 나사 금지), 그릴(8호 19 mm × 4; 25 mm 금지)." % (f(B.INS_HOLE[0], 1), f(B.INS_HOLE[1], 1), f(B.INS[0], 0), f(B.INS[2], 0),
                                                                   f(B.T - B.INS_HOLE[1], 1), f(B.ANGLE, 0), pin, f(_PIG_OUT[0], 0)),
        "**가운데 유닛** — 아랫판·뒤판은 3토막씩 출력: 먼저 반턱 이음 2곳씩을 MS 폴리머로 겹쳐 붙이고 곧은 자에 모서리를 맞춰 굳힘 (아랫판 679, 뒤판 702가 "
        "되는지 잼). 그다음 아랫판 + 뒤판 + 출력 끝벽 L·R을 MS 폴리머로 (끝벽 Ø8 구멍에 고무 슬리브 = 연료 호스 OD8 ID4.5, 꽉 낌; 끝벽 윗모서리 "
        "자석 자리·XT60 Ø19 구멍은 출력에 있음). 뒤판 창에 뒤판 출력물을 끼우고 바닥 탭의 나사 2개를 접시 8호 13 mm(L77)로: "
        "(%s, %s) · (%s, %s) — KCD1 단자와 J501 받침 사이로 드라이버가 곧게 닿음. "
        "J501 기판은 그 뒤 받침 위에 MS 폴리머. 이음 레일·기둥 2개(M3 인서트를 먼저 인두로)를 뒤판 안면·아랫판에 MS 폴리머로. 보드는 받침 기둥에 먼저 나사(M3×6, Pi M2.5×6)로 단 뒤 기둥 밑을 (관통 구멍은 막지 않게 고리로) "
        "아랫판에 MS 폴리머 (스스로 자리 잡음; PED 보드는 90° 돌려 x426.5~476.5). 배터리 틀(접시 8호 13 × 4: 왼쪽 귀 2 + 앞 낮은 덩어리의 Ø9 구멍 2), 허브를 뒤판에 붙여 바닥에 놓고 허브 선반(받침 2를 뒤판에 "
        "M3 × 12 트러스 태핑 피스 L78 — 드라이버는 선반 윗면의 머리 길 홈을 따라 앞에서), 앰프(HW-720)를 선반 받침에(M3×6, 노브는 빼서 보관 - 꽂아 두면 뚜껑에 닿음). 이 나사들은 모두 곧은 드라이버(Ø6 × 80)로 "
        "닿음 (check_body.py). XT60 집게 2개를 끝벽 안쪽 Ø19 구멍에 맞춰 MS 폴리머 (판 구멍과 끝벽 구멍이 같은 축, 홈이 세워짐), "
        "끝벽 L 안면에 케이블 집게 2개(y262~282·286~306, z48~58). 뚜껑 자석 12개(극이 서로 당기게). 전원선·5.1 V선·스피커선 배선 (스피커선 L은 끝벽 "
        "집게에 끼우고 집게 E1 앞에서 z56.5로 올려 XT60 집게 판 위로 y%s까지 와서 XT60 수로; 앰프 선 끝 XT60 수는 16 AWG 10 cm 선을 앰프 선에 "
        "납땜 + 수축 튜브로 잇고 파란 수축 튜브 + 'SPK'). 퓨즈 홀더(ATC/ATO)에 5 A ATO 퓨즈를 넣고 덮개를 닫음. 12 AWG 꼬리 두 가닥을 홀더 끝에서 "
        "약 %s mm 뒤(30 mm 안)에서 잘라 16 AWG와 납땜 + 수축 튜브로 잇고 (12 AWG는 R15보다 좁게 꺾지 않음): -x 꼬리 → 하네스 XT60 수, +x 꼬리 → KCD1 "
        "아래 단자. 틀 나사 4개를 조인 뒤 홀더를 덮개가 +y(배터리 쪽)로 가게 눕혀 배터리 틀 퓨즈 선반의 꼭지 받침 2개에 눌러 끼움 — **하네스 수 선은 퓨즈 "
        "홀더 -x 끝에서 (꼬리 + 이음 포함) 약 %s mm로 잘라** 빨간 수축 튜브 (10 cm 그대로면 왼쪽 스피커 XT60 집게까지 닿음: "
        "직선 %s mm). 배터리 선 XT60 암과 시험 전원 어댑터에도 빨간 수축 튜브. **배터리나 시험 전원을 스피커 XT60(파랑)에 꽂지 않음** — 12.8 V 직류가 "
        "앰프 출력이나 스피커 코일에 걸림. 마지막에 배터리를 틀에 넣고 끈(L79)으로 감은 뒤 선 두 개를 +x 끝에서 위로 꺾어 XT60 짝과 DC 충전 커넥터를 배터리 윗면에 눕힘."
        % (f(B.BP_TABS[0][2], 1), f(B.BP_TABS[0][3], 0), f(B.BP_TABS[1][2], 1), f(B.BP_TABS[1][3], 0), f(__import__("electronics").SPKL_WALL_Y, 0),
           f(_elec().LENGTHS["PWR-IN-12"], 0), f(MM["cut"], 0), f(MM["need"]["L"], 0)),
        "**책상에서: 건반 쪽** — 모듈과 끝 부속을 도브테일로 잇고, 볼 뒤 M3 자리에 방진 브래킷 BRK2 (그로밋 2 + M3×20 × 2, 스피커를 올리기 전에 조임). "
        "모듈 USB-C 선을 꽂아 통로 자리(y%s~%s) 책상 위에 눕힘. 스피커 밑에 올 O1·O7 선과 EL·ER 리드·JST-XH는 이때 통로 안쪽으로 가지런히." % (
            f(B.DUCT_Y[0], 0), f(B.DUCT_Y[1], 0)),
        "**가운데 유닛 놓기** — 모듈 뒤 2 mm 틈(y212~214)을 두고 놓음. 앞벽이 없어 앞 공간(y214~241)이 선 위로 옴.",
        "**스피커 놓기** — EVA 3T 띠 2줄을 스피커 안쪽 옆판에 미리 붙임. 스피커를 브래킷 핀보다 약 %s mm 위, 제자리보다 약 %s mm 바깥에 들고, 꼬리의 "
        "XT60 암을 입구(가운데 쪽)부터 끝벽 Ø%s 구멍(L z%s · R z%s)에 세워서(넓은 면이 위아래) 넣고 뒤끝을 드라이버 손잡이로 밀어 끝벽(11.5)과 집게 판(3)을 "
        "지나게 한 뒤, 가운데 안에서 잡아 집게 홈에 곧게 당겨 넣고 위에서 눌러 끼움 (구멍과 홈이 같은 축, 판 앞 목은 깔때기). 스피커를 안쪽으로 밀어 EVA가 끝벽에 닿게 하면서 남는 꼬리(여유 약 %s mm)를 끝벽 구멍 안에 느슨하게 감아 넣고, 핀에 곧게 "
        "내려 끼움 (L 둥근 / R x 방향 긴 소켓, 핀 끝과 소켓 바닥 사이 2 mm). 가운데 안에서 M4 나비나사 2개씩 (머리는 고무 슬리브에만 닿음). 앰프 선 "
        "XT60 수(파랑 + SPK) 꽂기 — 집게 홈에는 축 방향 멈춤이 없어(홈 뒤가 터널로 열려 있어야 스피커를 뗄 수 있음) 홈 안의 F에 M을 대고 밀면 F가 터널로 밀려 들어감: "
        "F를 홈 입구로 가운데 쪽에 당겨 꺼내고(꼬리 여유 약 %s mm), 손으로 M을 끝까지 꽂은 뒤, 짝을 다시 가져와 F 앞면을 홈 입구에 맞춰 위에서 걸림 턱 "
        "밑으로 눌러 끼움 (M은 입구 밖으로 나옴)." % (f(B.POD_LIFT, 0), f(B.POD_SLIDE, 0), f(B.END_HOLE_D, 0), f(eh["L"][1], 1), f(eh["R"][1], 1),
                                                   f(B.PIG_SLACK_MM, 0), f(B.PIG_SLACK_MM, 0)),
        "**선 정리** — 뚜껑을 모두 뗀 채 앞 공간에서 모듈 USB 선을 묶음(y237.5, 4층)으로 모아 허브 포트에 꽂음 (포트 2 PED, 3 O3, 4 O1, 5 O2, 6 O4, "
        "7 O5, 8 O6, 9 O7; 짧은 O5·O6은 묶음 위 앞쪽 줄). 헤드폰 선 W701/W702는 왼쪽 볼 홈에서 통로 바닥을 따라 동글·J702로.",
        "**터치스크린: 화면 → 받침 (책상 밖에서)** — 화면 ZIF(22핀, 입구 +x)에 FFC B형을 3.5 꽂고 잠금 → 입구에서 +x로 4 mm 뒤 45°로 말아 접음(R3, 날카롭게 "
        "꺾지 않음) → 리본 길 xr27.25~38.95(x638.25~649.95)를 따라 아래로, 누름 패드 자리(u8~16)에 캡톤 → MX1.25 전원선은 그 옆 xr40.45~43.45로 → 둘을 "
        "아래 트인 홈으로 빼고 화면을 받침에 넣음(굵은 테두리 9.65가 아래, 커넥터 창이 오른쪽, 유리 아래 끝이 아래 벽에 얹힘) → 뒤에서 M2.5×6 4개(구멍 깊이를 "
        "먼저 잼, 사양 G-2) → 점검창 덮개를 걸쇠가 걸리게 눌러 끼움 → 받침다리를 다리 걸이 볼 사이에 넣고 M3×20을 −x에서(육각 L렌치 2.0) 먼 볼에 탭 → "
        "머리가 볼에 닿을 때까지 돌린 뒤 약 1/4바퀴 풀어 다리가 제 무게로 돌게 함 (PETG 탭 나사산 마찰로 풀리지 않음; 조이면 볼이 다리를 물어 "
        "아래 '받침다리 펴기'가 안 됨).",
        "**터치스크린: 받침 → 화면 뚜껑** — 리본과 전원선을 뚜껑의 22 × 6 구멍(x%s~%s)으로 위에서 아래로 넣고(3핀 이음도 통과), 뚜껑 밑에서 리본을 "
        "밑면에 붙여 +y로 → 클립 덩어리 밑에 리본을 대고 전원선 2가닥을 클립 윗면 홈(x652.6~656.1)에 넣은 채 클립 핀 2개를 Ø3.1 구멍에 눌러 끼움 → 리본을 "
        "y270.5에서 45° 접어 −x로 x583까지 → 받침 귀 2개를 귀 홈에 넣고 M3×20을 바깥 가까운 볼에서(왼쪽 −x, 오른쪽 +x) 넣어 먼 볼 Ø2.5에 탭(물림 7.6) → "
        "머리가 볼에 닿을 때까지 돌린 뒤 약 1/4바퀴 풀어 귀가 제 무게로 돌게 함 (PETG 탭 나사산 마찰로 풀리지 않음; 귀와 볼 사이 틈은 0.2씩뿐이라 "
        "조이면 화면이 25°로 돌아가지 않음)."
        % (f(B.SLID_RIBBON[0]), f(B.SLID_RIBBON[1])),
        "**뚜껑** — 출력 뚜껑 L·R (자석 3쌍씩: 밑면 자석 자리는 출력에 있음, 순간접착제로 붙이고 극이 짝과 당기게). 화면 뚜껑은 얹기 전에 리본을 기둥 x583으로 내려 안 쓰는 micro-HDMI 위로 Pi 5 CAM/DISP 1(x589, 입구 −x)에 "
        "2.7 꽂고 잠그며, 점퍼를 GPIO 2번(빨강 5 V)·6번(검정 GND)에 꽂음 → 이음 레일 위에 얹고 M3×10 × 4 (자리파기 5.5, 머리 자리 z67.35; 양쪽 이음에 0.5씩 "
        "틈). 고무발(5)과 모듈 EVA(3)의 눌림 차이로 뚜껑이 건반 윗면과 ±0.5 어긋나면 얇은 받침으로 맞춤.",
        "**받침다리 펴기·접기** — 화면을 22°(뒤꿈치가 멈춤 블록에 닿음)까지 앞으로 기울여 댄 채 다리를 내림: 다리가 수평 아래 약 40°에서 발이 경사에 먼저 "
        "닿고, 손을 놓으면 화면이 25°로 돌아가며 발이 경사를 타고 뒷벽까지 미끄러짐. 25°에서 그대로 내리면 발이 뒷벽 위 모서리를 약 0.66 긁음 "
        "(check_body.py가 22°·25° 두 경우를 돌려 봄). 접을 때도 22°에서 다리를 올려 받침 뒤 클립에 끼운 뒤 화면을 뒤로 눕힘.",
    ]


_PIG_OUT = [0.0]            # set in main() from the manifest (pigtail length outside the pod)

SERVICE = [
    ("패드 바", "없음", "뒷바가 y214부터라 패드 바(y146.5~185) 위가 비어 있음"),
    ("모듈 제어 기판 (A16)", "그 모듈 (아래 줄대로 들어 냄)",
     "건반 12개를 뺌(레버 손톱 턱을 들고 3 mm 앞으로 밀어 뽑음, 흑건은 양옆 백건 먼저) → 건반 봉을 들어 냄 → 레버틀(바닥 밑 M3×10 4개) → 밸런스 레일(양 끝 M3×6 2개) "
     "→ 기판을 리본째 들어 올림. 기판은 받침 리브 위에 놓여 둘레 턱(틈 0.3)과 레일만이 잡으므로 나사가 없음"),
    ("O2·O3 모듈", "뚜껑 L (자석)", "앞 공간에서 USB-C 부트를 위로 뽑고 모듈을 곧게 들어 올림"),
    ("O5 모듈", "뚜껑 R (자석)", "같음"),
    ("O4 모듈", "화면 뚜껑 (M3×10 4개, 화면째)",
     "사양 B (O4 정비): 화면을 뒤로 접고(다리는 클립에) → M3×10 4개(앞 y246, 뒤 y322)를 풂 → 뚜껑을 화면째 천천히 듦(리본을 꽂은 채 약 96 mm) → "
     "Pi 5 CAM/DISP 1 잠금 막대를 올려 리본을 뺌(화면 쪽 ZIF는 받침 안이라 건드리지 않음) → GPIO 2·6 점퍼를 뺌 → 뚜껑을 옆에 두고 앞 공간에서 플러그를 뽑음. "
     "되돌릴 때 리본 B형 방향 확인 후 잠금, 점퍼 2번 빨강·6번 검정, 나사 4개"),
    ("O1·O7 모듈, EL·ER 끝 부속", "그쪽 스피커", "허브에서 선을 뽑고 스피커를 들어낸 뒤 (아래 줄), 모듈을 곧게 들어 올림"),
    ("O6 모듈", "스피커 R (또는 뒷바 전체)", "플러그가 가운데 끝벽 R / 스피커 이음 밑"),
    ("스피커 하나", "뚜껑 L 또는 R",
     "XT60 짝을 홈 입구로 가운데 쪽에 당겨 꺼내 손으로 XT60 수(파랑)를 뽑고 암은 다시 홈에 눌러 끼움 (홈에는 축 방향 멈춤이 없음 - 짝은 홈 밖에서 꽂고 뽑음) → "
     "나비나사 2개 풀기 → 스피커를 약 10 mm 들어 핀에서 빼고, 통로 지붕 밑 케이블 집게에 끼운 선(EL·ER 리드·헤드폰 선)이 있으면 이때 모두 빼냄 "
     "(집게는 스피커에 붙어 있어 선이 같이 들림) → 약 18 mm 바깥으로 밂 (끝벽 구멍 안에 감긴 꼬리가 풀려 나오고 XT60 암은 "
     "집게에 남음; 암 길이 16이 벌어진 틈에 들어가려면 18) → 가운데 안에서 XT60 암을 집게 홈에서 끝벽 쪽으로 곧게 밀어 터널에 넣고(드라이버 손잡이로), 벌어진 틈에서 꼬리를 당겨 끝벽 구멍 "
     "밖으로 빼냄 → 스피커를 들어냄 (가로 다월 없음; check_body.py가 이 순서를 확인)"),
    ("뒷바 전체", "뚜껑 L · 화면 뚜껑 (M3×10 4개, 화면째 - 위 O4 줄처럼 리본·점퍼를 Pi에서 뺌) · 뚜껑 R",
     "허브의 USB-A 7개(O1~O7; PED는 가운데 안이라 그대로)와 3.5 mm 플러그 2개(J702 x514~526, 동글 x644~656 — 둘 다 화면 뚜껑 아래)를 뽑고, 뽑은 "
     "플러그는 앞 공간(y<241)으로 옮겨 놓음 → 선은 모두 건반 쪽에 남아 통로에 놓임 → 뒷바를 곧게 들어 올림 (앞 공간은 아래가 열려 있어 선 위로 빠짐; "
     "W701/W702를 볼 쪽 끝에서 뽑아도 됨)"),
]


def _collars():
    from keyaction_parts import collar_plan
    out = []
    for side in (None, "left", "right"):
        for n, (l, r) in collar_plan(side).items():
            out.append("%s %s" % (n, ("%.2f" % r).rstrip("0").rstrip(".") if r else "0"))
    return ", ".join(out)


COLLAR_TEXT = _collars()
FG = l2_figures()
AD = L2.get("angle_decision", {})
SEL_ANGLE = L2.get("selected_angle", body.ANGLE)              # user decision 2026-10-01: 40 (W1 relayed)
EARLIER = AD.get("earlier_choice_deg", 43.0)                  # the first L2 choice
ALT = EARLIER if abs(body.ANGLE - EARLIER) > 1e-6 else SEL_ANGLE   # the other angle shown next to the built one

ADJUSTMENTS = [
    ("A1", "흑건 키퍼 훅 5개 (C#·D#·F#·G#·A#)",
     "geometry.json에서 훅 뒤끝 y80.5와 탭 앞면 y80.8 사이가 0.3 떠 있어 훅이 공중에 뜸 → 훅 단면 그대로 y80.3~81.0을 채워 탭에 붙임. 움직이는 부품과의 틈은 그대로(훅 폭 5.2 < 탭 폭 6.9)."),
    ("A2", "뒷벽 스프링 홈 12곳 (+ 끝 부속 4곳)",
     "긴 다리(P18: y205.87 z32.91 → y210.75 z54.50, 선 0.5)가 뒷벽 면 y209를 z46.76에서 지나는데 홈은 z47부터라 다리가 뒷벽을 0.3 파고듦(z45.6~47) → 뒷벽 쪽(y209~211)만 홈을 2.0 아래(z45)까지 연장. 보스 쪽 홈·모따기는 그대로."),
    ("A3", "패드 바 잎 혀",
     "geometry.json의 잎 혀는 설치 상태(0.3 눌려 올라감). 출력 파일은 자유 상태(끝이 0.3 아래, 외팔보 처짐 곡선)로 바꿔 설치할 때 예하중 0.3이 생기게 함. 조립 파일은 설치 상태."),
    ("A5", "레버 캐리어 허브 칼라",
     "P14는 레버 사이 칼라를 양쪽 허브에 나눠 붙였는데, 그러면 C#·E·G·A#·A#0은 양쪽 옆면에 칼라가 튀어나와 DESIGN 15장 방향(옆벽을 베드에)으로 눕힐 수 없음 → 짝마다 두 칼라를 낮은 x 레버의 +x 쪽 한 칼라로 합침(총길이·허브 사이 틈·칸마다 축 놀음 0.46/0.46/0.43/0.30 그대로). 모든 캐리어가 −x 면을 베드에 댐. 새 오른쪽 칼라(왼쪽은 모두 0): " + COLLAR_TEXT + ". 음 이름은 +x 쪽 웹 바깥면(y194.7 z36.7)에 Arial Black 0.4 깊이로 새김(획 0.6 이상)."),
    ("A6", "뒤 도브테일 암 (모듈 왼쪽 끝, 오른쪽 끝 부속)",
     "geometry.json의 'rear dovetail (female groove…)'는 홈 자리 상자일 뿐이고 그 둘레에 바닥판 2 mm 말고 재료가 없어 이웃 모듈의 수 꼬리를 잡지 못함 → 선반 밑에 출력 블록 x0~6.1 · y195.9~209.0 · z3~18.05를 넣고(선반·뒷벽과 한 몸) 그 안에 암 홈(입구 6.214 → 깊이 4.1에서 9.288, 한쪽 틈 0.10, 천장 z17.3, 밑이 열림)을 팜. 앞 도브테일은 흰건반 앞 레일 속에 그대로 팜. 수 꼬리(뿌리 6 → 끝 9, 깊이 4)는 모듈 오른쪽 면(x164.5~168.5)과 왼쪽 끝 부속에 붙임."),
    ("A7", "방진 브래킷 BRK2와 볼 (끝 부속)",
     "v3 A12 평판(y205~222, z12)은 v4 끝 부속의 전높이 뒷벽(z5~72.85)을 지나야 해서 붙일 수 없어 L1에서 그로밋 2개로만 닿는 브래킷을 새로 만들었고, "
     "L2에서는 이 브래킷(BRK2)에 스피커를 얹는 세운 핀 Ø6(z14~24)을 붙임. 볼 뒷면 y212의 M3 자리 2개(z12; 왼쪽 x−11.80/−4.88, 오른쪽 "
     "x1226.88/1233.80 = 볼 가운데 기준)와 밑에서 넣는 너트 홈(맞변 5.6 × 2.6, 천장 z15.2)은 L1 그대로. 핀 x는 사양 0.5/1221.5 → %s/%s "
     "(핀 판이 안쪽 볼트 머리·렌치 길을 막지 않게, 핀 사이 %s; R 긴 소켓 공차 ±2.3 그대로). 브래킷 밑 z8은 왼쪽 볼의 헤드폰 선 홈(x−12.6~−4.1 · "
     "z3~7.5) 위라 L1의 선 홈은 필요 없음."
     % (f(body.PIN_XY["L"][0], 1), f(body.PIN_XY["R"][0], 1), f(body.PIN_XY["R"][0] - body.PIN_XY["L"][0], 1))),
    ("A8", "CU 칸 배치 (L2)",
     "L1은 v3 배치(도면 10: Pi 5와 앰프가 9 mm로 붙어 USB 플러그가 들어가지 않음)를 다시 짜고 CU 트레이 칸막이 탭을 옮겼음. L2에는 트레이·칸막이가 "
     "없고 사양 centre_contents 상자(쌍 1368개 검사, 문제 0; 2026-10-07 바뀐 상자는 check_electronics.py가 다시 검사)를 그대로 씀: LiFePO4 배터리(A칸 x271.5~426)·퓨즈 홀더(앞 공간 위 x397~437) · I/O·PED(B) · 강압·J702(D) · "
     "Pi 5·동글(E) · 허브·앰프 선반(F x668~950.5). 보드는 사양의 받침 판(90×60) 대신 낱개 받침 기둥(보드에 먼저 나사, 기둥 밑을 아랫판에 MS 폴리머)이라 "
     "아랫판 흡기 홈을 막지 않음. 앰프 받침(2026-10-26 HW-720: 3 mm)은 허브 선반과 한 몸."),
    ("A9", "뒷바 L2 (한 몸 뒷바, spec/body_L2.json)",
     "사용자 요청(2026-10-01, '건반과 뒤 부품을 합쳐서 뒤 영역을 최대한 줄이고, 케이블이 밖으로 안 나오게, 스피커는 더 눕히고 작게')에 맞춘 새 뒷바 "
     "(설계안 C + 고침, W1 음향 확인 통과). 전체 깊이 %s → %s (건반 뒤 면적 %s %%, 래치 포함 L1 %s 대비 %s %%). 뒷바는 모듈 뒷벽 y212 뒤 2.0 mm "
     "공기 틈(D15) 다음 y214~%s. 모듈 USB 선은 L1의 열린 통로(y212~252) 대신 뒷바 밑 닫힌 통로 y%s~%s × z%s~%s로 (스피커 밑은 출력 통로 지붕, "
     "가운데는 뚜껑 아래 앞 공간, 양끝은 출력 마개) → 위·뒤·옆에서 선이 거의 보이지 않음 (배기 홈 아래와 건반 뒤 2 mm 틈으로만 조금 — 아래 '선 가리기'). 가운데 유닛 z5~%s: 뚜껑 3장(L 오꾸메 · 화면 뚜껑 출력 · R 오꾸메) "
     "윗면이 건반 윗면과 같은 높이(L1 z88에서 −15.15), 앞벽 없음. 스피커 파트 %s × %s × z5~%s (L1 213 × 195 × z5~134): 앞판을 수평에서 %s° "
     "(수직에서 %s°, L1은 수직에서 30°)로 더 눕히고 안 부피 %s L (유닛 뺀 %s L, L1 2.95 L). 유닛 중심 x%s / %s (스피커 가운데보다 40 안쪽), y%s z%s, "
     "축은 가운데 귀(y%s, z%s)와 y-z 면에서 %s° 어긋남 (W1 한계 20°). Qtc %s, Fc %s~%s Hz (흡음솜 넣으면 Qtc %s, Fc %s~%s Hz; Vas 3 L · Qts 0.72 · Fs 90~128 가정, "
     "유닛 뺀 부피 기준 - W1 계산 방식). "
     "스피커 윗면이 L1보다 %s 높은 까닭: ① 27° 소리 길이 모듈 뒤 윗모서리(y212, z72.85) 위 %s (W1 3.0 + 조립 0.5), ② 그릴 판 아래 모서리가 "
     "y213 뒤(R18: 모듈을 위로 뺄 때 걸리지 않음, 지금 y%s), ③ 앞판 각도 — 이 세 규칙이 유닛 중심을 정하고, 윗면 = 그릴 판이 "
     "프레임 윗모서리를 덮는 높이 + 0.5. 깊이를 1 mm 늘리면 윗면이 약 0.51 낮아짐. 각도: 사용자가 2026-10-01 %s°를 고름 (W1 전달; 처음 L2 선택은 %s°). "
     "%s°에서 유닛 플랜지 아래 모서리가 27° 선 아래 %s로 W1 엄격 기준 3.0보다 작지만 W1이 받아들임 (모듈 뒤 윗모서리 여유 %s ≥ 3.0 조건). "
     "%s°였다면 z%s · 뒤 y%s · 플랜지 %s (사양 pareto_by_angle, body.py의 ANGLE 한 줄). "
     "이음: 도브테일 블록 4·토글 래치 2 대신 BRK2 세운 핀(L 둥근 / R 긴 소켓) + 가운데와 M4 나비나사 2개씩(고무 슬리브) + EVA 3T 띠. 합판 "
     "%s → %s m² (400 × 1200 한 장) → 0 (2026-10-16 A안: 판을 모두 출력). L1 뒷바는 src/body_L1.py · electronics_L1.py · check_*_L1.py(쓰지 않음)."
     % (f(FG["l1_depth"], 1), f(FG["depth"]), f(FG["area_pct"], 1).replace("-", "−"), f(FG["l1_depth_latch"], 0),
        f(100.0 * (FG["area"] / FG["area_l1_latch"] - 1.0), 1).replace("-", "−"), f(FG["depth"]), f(FG["duct_y"][0], 0),
        f(FG["duct_y"][1], 0), f(FG["duct_z"][0], 0), f(FG["duct_z"][1], 0), f(FG["centre_top"]), f(FG["pod_w"], 1), f(FG["pod_d"], 1),
        f(FG["top"]), f(FG["angle"], 1), f(FG["angle_v"], 1), f(FG["gross"], 3), f(FG["net_spec"], 2), f(FG["drv_x"]["L"], 1), f(FG["drv_x"]["R"], 1),
        f(FG["drv"][0]), f(FG["drv"][1]), f(EAR_YZ[0], 0), f(EAR_YZ[1], 0), f(FG["aim_off"], 1), f(FG["qtc_net"]),
        f(FG["fc_net"][0], 0), f(FG["fc_net"][1], 0), f(FG["qtc_fill"]), f(FG["fc_fill"][0], 0), f(FG["fc_fill"][1], 0),
        f(FG["top"] - FG["l1_top"]), f(FG["sp"]["module"]), f(body.POD.D(body.GR_S0, body.GR_W[1])[0]),
        f(SEL_ANGLE, 0), f(EARLIER, 0), f(FG["angle"], 0), f(FG["sp"]["flange"]), f(FG["sp"]["module"]),
        f(ALT, 0), f((pareto_row(ALT) or {}).get("pod_top_z", 0)), f((pareto_row(ALT) or {}).get("back_y", 0), 1),
        f((pareto_row(ALT) or {}).get("flange_corner_clearance_mm", 0)),
        f(L2["plywood_cut_list"]["L1_area_m2"], 3), f(L2["plywood_cut_list"]["area_m2"], 3))),
    ("A10", "터치스크린 3판 (R31, Waveshare 7-DSI-TOUCH-C)",
     "W1 3판 3a(`touchscreen/rev3/design/CAD_SPEC_rev3.md` A~G + `numbers.json`, 사용자 승인 2026-10-01)를 그대로 만듦: touchscreen_rev3.py가 3판 numbers.json을 "
     "읽고(2판은 L1 보관본이 쓰는 touchscreen.py 그대로), body.py가 화면 뚜껑에 경첩 볼·뒤꿈치 멈춤 블록·리본 구멍과 벽·클립 덩어리·다리 주머니·접이 받침 발·배기 홈·"
     "자리파기 5.5를 더하고 받침·받침다리·점검창 덮개·리본 클립·화면 덮개(선택)를 07_터치스크린으로, electronics.py가 화면·DSI FFC·전원선을 만듦. "
     "사양과 다르게 한 곳은 아래 '터치스크린 3판'의 표 (뚜껑 실제값 x%s~%s · y%s~%s, 앞 기둥 자리, 보스 자리파기 평평한 물방울, 아래 뒤 모서리 C%s, "
     "패드 45° 모따기, 다리 클립 45° 받침, 덮개 걸쇠 보·홈 등)." % (f(body.SLID_X[0], 1), f(body.SLID_X[1], 1), f(body.Y0, 0), f(body.YB, 1), f(body.CR_C2, 1))),
    ("A11", "건반 모서리 둥글게 (백건·흑건 전부, 2026-10-26)",
     "geometry.json의 건반은 모서리가 직각인 상자. 실제 피아노 건반처럼 출력 건반을 둥근 외곽으로 깎음(keyaction.key_rounding): 백건 앞 모서리(평면) R%s, "
     "앞 립 아래 앞면 세로 모서리 R%s(윗판 밑 0.3까지 — 립 1.5 뒤라 보이지 않음), 흑건 앞 모서리(평면, 비스듬한 앞면 따라) R%s, 흑건 아래쪽 앞 모서리 R%s, "
     "드러난 윗모서리(앞·양옆, 머리와 꼬리) R%s. 백건 머리 뒤 계단(흑건 앞) 모서리는 그대로. "
     "윗모서리 둥글림은 윗면 쪽 절반을 45° 면으로 바꿔, 윗면을 베드에 대고 뒤집어 출력해도 45°보다 더 처지는 곳이 없음. 재료를 깎기만 하므로 틈은 줄지 않고, "
     "건반 한 개당 약 0.06 g 가벼워짐(터치 무게 변화 0.1 g 미만). 가림판 밑(흑건 y144.3 뒤)과 숨은 빔·꼬리는 그대로."
     % (f(keyaction.KEY_ROUND["white_corner"], 1), f(keyaction.KEY_ROUND["white_front"], 1), f(keyaction.KEY_ROUND["black_corner"], 1),
        f(keyaction.KEY_ROUND["black_low"], 1), f(keyaction.KEY_ROUND["top_edge"], 1))),
    ("A12", "서포트 없이 뽑게 나눈 프레임·레버·패드 바 (2026-10-29)",
     "한 옥타브를 뽑아 보니 서포트를 떼기 어려웠음(프레임 윗판 밑 모듈마다 약 88 g이 핀 사이 좁은 칸 안에, 레버 강철 칸 속 떼는 지지대, 패드 바 자리 밑) → "
     "모든 면이 베드 위 벽이나 짧은 다리(23 이하)로 나오게 나눔 (keyaction.frame_split 등). "
     "**프레임 → 바닥틀 + 레버틀 + 가이드 탭.** 바닥틀(바닥·흰건반 앞 레일·흑건 멈춤 레일·탭 받침·센서 바 받침·밸런스 레일·도브테일·기판 앞 보스, 끝 부속은 볼까지)은 "
     "바로 세워 뽑고, 레버틀(윗판·패드 바 레일·핀 5장·봉 보스·뒷벽·스프링 홈·뒤 선반·선반 갈비·기판 뒤 보스)은 뒷벽 바깥면을 베드에 눕혀 뽑음 - 핀과 윗판이 모두 "
     "세워진 벽이 되고, 옛 바로 세운 출력에서 층간이던 윗판↔핀 이음(FE 핀 윗 이음 층간 최대 5.7 MPa, 8.1장)이 한 층 안에 들어가 더 강함. 레버틀은 핀 발이 "
     "바닥틀의 홈 둑(높이 2.5, 틈 0.15) 사이에 들어가 자리 잡고, 모듈은 바닥 밑에서 M3×10 자가 탭 4개(앞: 2·4번 핀의 뾰족 보스 x41.66/123.93 y160.5, "
     "뒤: 선반 밑 뒷벽 D 보스 x29/143 y203)로 조임 - 나사만이면 레버를 단 채 레버틀을 들어 낼 수 있고, MS 폴리머를 같이 바르면 한 몸처럼 단단함. "
     "끝 부속은 볼이 바닥틀에 통째로 남고 레버틀의 끝 핀·윗판 끝·봉 보스·뒷벽 끝이 볼 안쪽 면 홈(깊이 약 1.1)에 들어가 MS 폴리머로 붙음. "
     "탭과 키퍼 훅은 따로 옆으로 눕혀 뽑아 바닥틀 자리(깊이 5.3)에 순간접착제로 꽂음 - 옛 키퍼 훅 밑(3.3 내민 면) 서포트가 없어지고, 옆으로 미는 힘이 층 안에 "
     "들어가며, 하나가 부러지면 탭만 다시 뽑음. 훅은 탭 폭 전체(백 7.5, 흑 6.9; 설계 P34 5.2)로 넓힘(펠트 5.2는 그대로 가운데) - 건반 홈 안이고 빼기 동작은 "
     "y·z 방향이라 틈은 그대로(탭 ↔ 가이드 갈비 0.55). 촉은 앞 1.0이 짧아 거꾸로 꽂히지 않음. 레버틀 뒤에 눕혀 뽑으려고 바꾼 곳: F|F# 핀 아래 앞(기판 홈 속)의 "
     "계단 y170.7을 45°로(킬까지 내려가는 버팀), 끝 핀 뒤 아래 노치 y196.7을 45°로, 봉 보스와 기판 뒤 위치 핀을 +y 쪽 45° 뾰족하게(핀 끝은 r1.45에서 잘라 "
     "기판 구멍 Ø3.0에 들어감), 기판 뒤 보스를 뒷벽까지 이음, 뒷벽 USB 구멍을 선반 틈 폭 x%s~%s로 좁힘(플러그 x77.75~90.25), 핀 보스 구멍 눈물방울 끝을 위(−y)로. "
     "기판 앞 보스 2개(레일 뒷면에 매달림) 밑에는 바닥틀 출력 파일에만 떼는 기둥(0.2 떨어짐)이 들어 있음. "
     "**레버 캐리어 → 몸통 + 덮개.** 강철 칸의 +x 옆벽(0.7)과 그 립 3개를 덮개로 따로 뽑음(바깥면을 베드에, 립이 위) - 몸통은 칸 위가 열려 서포트가 없고, "
     "옛 떼는 지지대·사포질이 없어짐. 강철을 MS 폴리머로 붙일 때(10장 4단계) 덮개를 같이 덮어 붙임: 위 앞 립 앞끝이 앞 뚜껑(y153)에, 위 뒤 립 뒤끝이 칸 뒷벽"
     "(y190)에 닿아 자리가 잡히고, 붙이고 나면 모양·질량이 옛 캐리어와 같음. 덮개는 88개 모두 같은 파일. "
     "**패드 바 → 윗면 한 평면.** 윗면을 윗판 자리 z%s 한 평면으로(옛 앞부분이 1.5 높아 자리 부분이 베드에서 1.5 떠 있었음), 앞부분(아래 계단 y165.5 앞)은 "
     "두께 %s로 내려 윗판에서 떨어짐 - 자리는 패드 위(y168~185)만, 레버 손톱 턱과 ff에서 1.56(옛 2.56, 규칙 1.3 이상; 이 판 스윕). 앞 손잡이는 아래로 2.5. "
     "잎 혀를 0.9 올려 자유 상태 윗면이 바 윗면과 같아짐 - 끝 돌기는 그대로 립 윗면 z65.55까지 내려오고(돌기 길이 +0.9), 윗판 밑에 혀 길을 따라 깊이 %s 홈"
     "(y167.9~183.4, 혀 폭 + 0.2씩)을 파서 0.3 휘는 자리를 줌. 혀 길이·두께·폭·예하중은 그대로. "
     "**건반은 한 몸 그대로**(숨은 빔 뿌리가 PLAY 11.5 MPa로 가장 센 곳이라 나누면 약해짐) - 슬라이서 서포트 대신 빔·꼬리 밑에 떼는 빗(가운데 날 0.8 + 8 mm마다 "
     "가로 날, 0.2 떨어짐)과 흑건 윗면 뒤끝 턱 밑 받침을 출력 파일에 넣음. "
     "확인: check_interf 쉼 자세 0건, 레버 쉼~ff(+서비스 15°) ↔ 레버틀 0.055(옛 프레임과 같은 축 놀음 자리), 건반 쉼·dip·ff ↔ 바닥틀 1.41 이상, ↔ 가이드 탭 0.55(설계와 같음)."
     % (f(keyaction.A12["usb_open"][0], 2), f(keyaction.A12["usb_open"][1], 2), f(keyaction.PAD_SEAT_A12, 2), f(keyaction.PAD_FRONT_T, 1),
        f(keyaction.A12["groove"], 1))),
    ("A13", "Bambu Studio 기준 서포트 0 - 천장을 없앰 (2026-10-30)",
     "A12 뒤 사용자: '아치 같이 바닥이 없고 천장이 있는 부분은 다 서포트가 생성이 될거야 ... 서포트는 트리 형태로 생성되니까 지금 모델링은 맞지 않아' → "
     "Bambu Studio는 바닥이 없는 천장마다(다리·구멍 꼭대기 포함) 트리 서포트를 세우고, STL에 넣은 떼는 빗·기둥(A12)과 상관없이 생김. A13은 천장 자체를 "
     "없앰: 출력 자세에서 아래를 보는 면은 45° 지붕(리본 길만 40°)이거나 베드 위. 확인은 src/check_support.py (0.2 mm 층으로 슬라이스해 층마다 아래층보다 "
     "Bambu 기본 문턱 30°(0.35 mm)보다 더 나간 곳 = 서포트 자리; 한두 층·폭 2 mm 이하 조각은 작은 다리로 뺌). "
     "**건반**: A12 빗 없음. 출력 때 천장이던 앞 멈춤 바닥(백 19.6 · 흑 8.0)과 밸런스 블록 위 두 칸 밑에 45° V 채움(건반 안쪽, 백건 +0.8 g), 흑건 윗면 뒤끝 "
     "턱(55.5 → 54.1)은 y142.9부터 45° 비탈, 캡스턴은 너트 없이 빔의 Ø%s 구멍에 바로 돌려 넣음(너트 홈 바닥이 옆 홈 속 천장이었음). 남는 곳: 숨은 꼬리"
     "(빔 + 얇은 꼬리, y146~199)는 위에 레버가 0.7 위라 채울 수 없어 바닥에서 15(백)·27(흑) mm 떠 있음 → 건반만 Bambu 서포트 켬(트리 자동, 빌드 플레이트"
     "에서만) - 바깥 면 하나라 한 덩어리로 떨어짐; 키퍼 가로대(8.6)는 위에 키퍼 펠트 2T가 있어 지붕 자리가 없는 양쪽 붙은 다리 - Bambu 기본 최대 다리 길이 "
     "10 mm 안이라 서포트 없음. **레버 캐리어**: 스프링 칸 지붕(+x 볼 안쪽 면, 코일 위 8 × 12 천장)에 Ø6.7 → Ø3.9 45° 원뿔(볼 1.4 들어감, 축 받침 길이 "
     "3.8 → 2.4 + 깃). **바닥틀**: 제어 기판 구멍(아래에서 나사 - 레일·선반에 매달린 보스 4개의 밑면이 천장)을 바닥으로 막고 기판을 기둥 Ø%s 4개(z5~%s) "
     "위에 위에서 M3×6 2개 + 위치 핀 Ø2.8 2개로 - 기판 손볼 때는 레버틀(나사 4개)을 들어 냄, EVA 바닥 시트에 기판 구멍 없음; 밸런스 레일 밑 리본 길 "
     "(23 폭 지붕)은 옆벽 z%s에서 %s° 뾰족 지붕(밸런스 핀 E·F 구멍 밑 0.2·0.5 남음); 암 도브테일 홈 위는 열린 끝면 쪽으로 45° 지붕; 끝 부속 볼의 잭 홈·선 홈은 "
     "45° 지붕, 너트 홈은 90° V 지붕(너트 옆 꼭짓점이 비탈에 얹혀 볼트 축 z12에 섬). **본체**: 스피커 앞판의 인서트·그릴 구멍 끝 45° 뾰족(상자 안까지 "
     "0.98·1.15), 허브 선반 머리 자리 물방울 꼭지가 윗면으로 트임, 뚜껑 이음 레일 인서트 구멍은 기둥 위 45° 뾰족·레일만인 곳 관통, 방진 브래킷 2는 옆으로 "
     "눕혀 출력(핀이 층과 나란해 굽힘에 더 강함), CU 화면 뚜껑은 갈비 칸(38 × 48 천장)을 한 덩어리 판으로 채움(배기 홈 관통, 클립 핀 구멍 끝 뾰족). "
     "**남은 곳**: 07 화면 받침(크래들)·점검창 덮개 - A13 때는 서포트 켬(크래들 약 30 cm², 덮개 약 3.7 cm²), A14에서 서포트 없이 바꿈. 채움·지붕은 붙는 면과 0.01 겹치거나 0.01 떨어지게 둠(맞닿은 "
     "같은 평면은 불리언이 위치마다 다르게 잘라 같은 건반이 다른 파일이 되고 STL이 닫히지 않았음). 확인: check_body·check_electronics·check_interf 통과, 동작 스윕 A12와 같음(레버 ↔ 레버틀 0.055, "
     "건반 ↔ 바닥틀 1.41 이상, ↔ 레버틀 1.47 이상, ↔ 가이드 탭 0.55)."
     % (f(keyaction.A13["self_tap_d"], 1), f(keyaction.A13_BOARD["post_d"], 1), f(keyaction.A13_BOARD["z_board"], 1),
        f(keyaction.A13_LANE["side_z"], 1), f(keyaction.A13_LANE["angle"], 0))),
    ("A14", "07 화면 받침·점검창 덮개도 서포트 0 (2026-10-30)",
     "A13 뒤 사용자: '07도 바꿔 줘' → 같은 Bambu Studio 기준(check_support). 받침은 윗변(u103.5)을 베드에 세운 자세 그대로(귀가 위, 높이 119.76) - 이 자세에서 "
     "+u를 보는 면이 모두 천장. **받침**: 아래 벽 앞 턱(w%s 앞, 유리가 얹히는 면 = 맨 위 166.7 × 9 천장)을 떼어 **유리 턱 띠 TS-LEDGE**(왼쪽 131.25 · 오른쪽 "
     "17.30, 사이가 아래 벽 홈 xr48~66; u0 면을 베드에 높이 2.5)로 따로 뽑아 아래 벽 앞면 w8·옆벽에 세메다인 슈퍼X(i071)로 붙임(붙임 틈 %s; 화면을 먼저 "
     "나사로 고정하고 유리 끝을 지그로). 남은 아래 벽(w8~16) 밑은 뒷판 앞(w8~10.5)·뒤(w13~16) 45° 받침; 가로 갈비 밑면 45° - u24 갈비는 다리 축 길에서 멀어지게 "
     "기울임(뿌리 u20~25, 위 u20~22 → 축 머리 길까지 2.0 이상 그대로), u80 갈비는 발을 u84까지; 보스 4개 + 옆벽 채움 밑에 기울인 45° 받침(앞 2.5 · 뒤 3, 위 두 "
     "개는 위 벽까지 50°); 누름 패드 밑 45°. **점검창**: 곧은 위 변이 29.5 다리(Bambu 기본 '최대 브리지 길이' 10 mm 넘음)라 u33 위에 45° 박공을 올려 맨 위 "
     "u22.75에 폭 %s 다리(10 mm 안 - 서포트 없음); 창 둘레 갈비는 박공을 따라 돌고 아래 변에 45° 발, 박공 위 가운데(갈비 위 변이 3 깊이 천장)는 덮개 턱 "
     "자리에서 45°로 눕힘; u24 갈비는 창 둘레에서 끊음. **덮개**: 같은 육각; 턱 밑면 1.7 처마 → 끼움부 가장자리 w12.8에서 창 + 1.5의 w14.5까지 45° 모따기"
     "(창 뒤 모서리에 선으로 얹힘) + w15까지 테; 볼록 자리 천장(13.7 다리) 위에 45° 지붕 → 맨 위 9 × 9 다리(안 w17.55, 바깥 w18.75 - 접은 상태·스윕 확인); "
     "걸쇠 보 2개를 창 옆벽 쪽(u 방향, 뿌리 u48 · 자유 끝 u54)으로 옮김 - 박공 때문에 위 변이 짧아짐, 휨·끼움·변형률 1.6 %%는 그대로, 보 위 홈은 7 × 2.3 다리. "
     "**확인**: check_support 07 서포트 0(남은 천장은 위 세 다리와 2 mm 안 구멍 꼭대기), check_body(받침·띠·덮개 모양, 22~90° 스윕, 접은 상태)·"
     "check_electronics(리본 길)·check_interf 통과."
     % (f(body.LEDGE_W, 0), f(body.LEDGE_GAP, 2), f(body.WIN_FLAT, 0))),
    ("A15", "캡스턴 너트를 되살림 - 너트 홈 천장은 구멍 없는 막 (2026-10-30)",
     "A13 뒤 사용자: '너트는 사용하는데, 기존 구조의 경우 서포트 처리가 어려워. 서포트 처리가 쉬우면서 너트를 사용하는 구조를 디자인해줘' → "
     "예전(D02·A12) 너트 홈은 빔 옆(+x)으로 열린 맞변 5.6 홈이었고, 뒤집어 출력하면 너트가 얹히는 면이 홈 속 천장이 되는데 그 가운데로 "
     "나사 끝 구멍 Ø3.3이 뚫려 있어 구멍 둘레가 허공에 떠서 Bambu가 홈 속까지 트리 서포트를 넣었음(빼기 어려움). **A15**: 같은 옆 홈(닫힌 끝만 육각 V 대신 축에서 3.2 평평한 벽 - 너트 꼭짓점 3.175가 닿아 축에 섬, 다리가 단순한 직사각형)과 M3 너트(i011)를 "
     "쓰되 나사 끝 구멍을 홈 천장 %s(두 층) 앞에서 멈춤 → 홈 위 첫 층은 구멍 없는 다리(맞변 사이 %s, 양쪽 맞변에 붙고 +x 끝은 열림) - Bambu 기본 "
     "최대 다리 길이 10 mm 안이라 서포트 없음. 캡스턴 M3×6을 처음 돌려 넣을 때 나사 끝이 막을 뚫음(도면 높이에서 끝이 막 속 0.05; 빡빡하면 "
     "Ø3 드릴을 손으로 밑에서). 홈 높이 %s(z%s~%s) = 너트 2.4 + 다리 처짐 0.4, 면은 모두 두 출력의 0.2 층 경계(43.5 − z · 55.5 − z). 위 잠김 구멍 Ø%s(D02)로 "
     "되돌림. 레버가 늘 캡스턴을 내리누르므로 너트는 홈 밑면(막 쪽)에 앉음. **check_support**: 건반 꼬리의 트리 서포트 인정을 바깥 밑면(출력 z18.7 백 · "
     "30.7 흑)까지로 줄여 빔 속 천장이 트리로 숨지 않게 하고, 너트 홈 천장(백 y188.34 ± 2.8 · 흑 126.11 ± 2.8, 출력 z20.0 · 32.0)을 다리로 인정 - 다리는 구멍 없는 조각만(예전 구멍 천장은 같은 검사에서 걸림); 03 탭 3D의 주황 면도 층 높이까지 맞춰 홈 천장을 칠하지 않음. "
     "**확인**: 01_건반·예비 건반 출력 파일 모두 서포트 0(꼬리 바깥 밑면만 트리), 캡스턴 축 층 확인(홈 열림 → 막 2층 → 구멍), 너트 ↔ 건반 0, check_interf 통과."
     % (f(keyaction.A15["membrane"], 1), f(keyaction.A15["slot_af"], 1), f(keyaction.A15["slot_z"][1] - keyaction.A15["slot_z"][0], 1),
        f(keyaction.A15["slot_z"][0], 1), f(keyaction.A15["slot_z"][1], 1), f(keyaction.FEAT["cap_hole_d"], 1))),
    ("A16", "제어 기판 80 × 120 통째로 - 바닥에 눕히고 밸런스 레일을 따로 출력 (2026-10-31)",
     "사용자: '80 120 으로 설계를 다시 만들어줄 수 있어? 지금 뒤쪽에 기판이 있는데, 기판을 바닥으로 내려도 돼' → BE163을 70 × 50으로 자르지 않음. 모듈 바닥에 "
     "80 mm 깊이의 빈 곳이 없어서(센서 바 y59~77.5, 검은 건반 탭 받침 ~y93, 밸런스 레일 y132.3~144.5, 레버틀 핀 발 y152~), 기판을 탭 받침 바로 뒤 "
     "바닥 x%s~%s × y%s~%s에 눕히고 밸런스 레일 밑을 지나게 함. **밸런스 레일**은 바닥틀에서 떼어 따로 출력(03 밸런스레일, 7개, 밑면 z%s = 기판 윗면, 바로 세워 서포트 없음) - "
     "윗면·봉 받침 판·밸런스 핀 구멍·옆 위치는 그대로라 건반 동작은 바뀌지 않음. 레일은 양 끝벽(x0.3~1.3 · x163.2~164.2, 봉 끝 기둥 그대로) 사이(틈 0.15)와 "
     "끝 받침 두 곳(z5~%s, 앞뒤 턱 틈 0.15) 위에 놓이고, 양 끝 깊은 구멍 Ø%s(바닥 z%s)에 예전 기판 나사 M3×6(i059) 2개로 받침에 자가 탭; 레일 밑면이 기판의 "
     "빈 띠를 눌러 기판도 잡음 - 기판에는 나사·구멍·자르기 없음. **바닥틀**: 기판 받침 리브 z5~%s(가장자리 둘레 + 레일 밑 띠; 앞은 리본 틈 x%s~%s, 레일 밑은 "
     "배선 틈 x%s~%s; 판 밑 2.0 = 리본 가닥 배선 두 겹 1.8이 지나감), 둘레 턱 z%s(틈 %s); 옛 기판 기둥·리본 길(레일 밑 40° 지붕)은 없어짐. **레버틀**: 핀 2·4번은 기판 위(y%s 앞)에서 밑변 z%s, F|F# 핀은 "
     "제로·USB 플러그 위로 z%s부터(킬은 레일 뒷면에 닿는 z%s~19.3만 남음); 레버틀 나사 2개(핀 2·4번 발)를 y160.5 → y186으로. **전자부**: 제로는 핀 헤더 몰드를 "
     "그대로 둔 채(2.5) 뒤쪽 칸에, USB-C 플러그 y170.5~195.5가 지금 뒷벽 구멍으로 곧게 나감(선 길이 여유 87 mm 이상 - 산 선 그대로), 먹스·리본 J301은 레일 앞 칸; "
     "기판 밑 다리 끝은 1.0 이하로 자름. 회로 BRD-01·08 △33(넷 그대로). 판은 7장 필요 - 가진 4 + 더 사는 8 × 12 양면 4장(3장은 MB, 1장은 PED 조각). "
     "기판 지그 P-MB는 없어지고 P-PED만 남음. **확인**: check_interf·check_electronics·check_support·check_perfboard_jigs 통과, 전자부 ↔ 건반 동작부 겹침 0."
     % (f(keyaction.A16["board"][0], 2), f(keyaction.A16["board"][1], 2), f(keyaction.A16["board"][2], 1), f(keyaction.A16["board"][3], 1),
        f(keyaction.A16["board_top"], 1), f(keyaction.A16["board_top"], 1), f(keyaction.A16["cb"][0], 1), f(keyaction.A16["cb"][1], 1),
        f(keyaction.A16["rib_top"], 1), f(keyaction.A16["front_gap"][0], 1), f(keyaction.A16["front_gap"][1], 1),
        f(keyaction.A16["wire_gap"][0], 0), f(keyaction.A16["wire_gap"][1], 0), f(keyaction.A16["lip_top"], 1), f(keyaction.A16["lip_clr"], 1),
        f(keyaction.A16["fin_y1"], 1), f(keyaction.A16["fin_z"], 1), f(keyaction.A16["ffs"][2], 1), f(keyaction.A16["ffs"][2], 1))),
    ("A4", "구멍 크기",
     "레버 허브·핀 보스 구멍은 설계대로 Ø3.9로 출력(핀 보스는 눈물방울) → Ø4.0 드릴. 밸런스 핀 구멍 Ø1.95 막힌 구멍(z11.3까지, 가벼운 압입; 안 들어가면 Ø2.0으로 다듬음), 센서 바 받침 기둥 자가 탭 자리 Ø2.75(관통), 센서 바 쪽 Ø3.4, 캡스턴 자리 Ø2.8 + 끝 여유 Ø3.3, 너트 홈 맞변 5.6 × 2.6. (A13에서 바뀜: 제어 기판은 기둥의 Ø2.5 파일럿; A15: 캡스턴 너트 홈 맞변 5.6 × 2.8 + 밑 0.4 막, 위 Ø2.8; A16: 제어 기판 기둥은 없어지고, 모듈 밸런스 핀 구멍은 따로 출력한 레일에, 레일 나사 자리 = 받침 Ø2.5 막힌 구멍(z3.5까지) + 레일 Ø3.4 / 깊은 구멍 Ø6.2)"),
]

ADJUSTMENTS.sort(key=lambda a: int(a[0][1:]))


def key_figures(man):
    """[(label, L1, L2 model)] for the summary table."""
    fg = FG
    sp = fg["sp"]
    cmp_ = L2["comparison_vs_L1"]
    ply = sum(1 for p in man["parts"] if p["kind"] == "plywood")
    return [
        ("전체 깊이 (y)", "%s (래치 포함 %s)" % (f(fg["l1_depth"], 1), f(fg["l1_depth_latch"], 0)), "**%s**" % f(fg["depth"])),
        ("건반 뒤 면적 (1254 폭)", "%s mm²" % format(int(fg["area_l1"]), ","), "**%s mm² (%s %%)**" % (format(int(round(fg["area"])), ","), f(fg["area_pct"], 1).replace("-", "−"))),
        ("가운데 윗면", "z%s" % f(cmp_["heights_z"]["centre_L1"]), "**z%s** (건반 윗면과 같은 높이)" % f(fg["centre_top"])),
        ("스피커 파트", cmp_["pod"]["L1"], "%s × %s × %s (z5~%s)" % (f(fg["pod_w"], 1), f(fg["pod_d"], 1), f(fg["top"] - 5.0), f(fg["top"]))),
        ("앞판 각도", "수직에서 30°", "**수평에서 %s°** (수직에서 %s°), 경사 길이 %s" % (f(fg["angle"], 1), f(fg["angle_v"], 1), f(fg["slant"]))),
        ("스피커 안 부피", "2.95 L", "%s L (유닛 빼면 %s L = W1 규칙 −%s L%s, 최저 1.8)"
         % (f(fg["gross"], 3), f(fg["net_spec"], 3), f(fg["disp_w1"], 3),
            "; check_body.py는 유닛 모형을 속이 찬 덩어리로 빼서 %s L" % f(fg["net_model"], 2) if fg["net_model"] else "")),
        ("Qtc / Fc (Vas 3 L 가정)", "약 1.02", "%s, Fc %s~%s Hz (유닛 뺀 부피; 전체 부피면 %s), 흡음솜 넣으면 약 %s, Fc %s~%s Hz (W1 방식, 유닛 뺀 %s L × 1.175)"
         % (f(fg["qtc_net"]), f(fg["fc_net"][0], 0), f(fg["fc_net"][1], 0), f(fg["qtc_gross"]), f(fg["qtc_fill"]), f(fg["fc_fill"][0], 0),
            f(fg["fc_fill"][1], 0), f(fg["net_spec"], 3))),
        ("스피커 겨냥 (가운데 귀 y%s z%s)" % (f(EAR_YZ[0], 0), f(EAR_YZ[1], 0)), "—", "축 수평 위 %s°, 귀는 %s° → y-z 면에서 %s° 어긋남 (W1 한계 20°)"
         % (f(fg["angle_v"], 1), f(fg["aim_ear"], 1), f(fg["aim_off"], 1))),
        ("모듈 USB 선", "모듈 뒤 열린 통로 y212~252 (위에서 보임)",
         "뒷바 밑 닫힌 통로 y%s~%s × z%s~%s (거의 보이지 않음 — 배기 홈·건반 뒤 2 mm 틈으로만 조금)" % (f(fg["duct_y"][0], 0), f(fg["duct_y"][1], 0), f(fg["duct_z"][0], 0), f(fg["duct_z"][1], 0))),
        ("27° 소리 길 여유 (수직)", "—", "사양 선(Ø94 가장자리 D(−47, 0)에서): 모듈 뒤 윗모서리 %s, 플랜지 모서리 %s, 가스켓 모서리 %s, 앞판 아래 끝 %s, "
         "그릴 옆벽 발 %s (W1 ≥3.0); 실제 소리 가장자리 D(−45, 7)에서: 모듈 뒤 윗모서리 %s"
         % (f(sp["module"]), f(sp["flange"]), f(sp["gasket"]), f(sp["F"]), f(sp["grille_foot"]), f(_real_path_clear()))),
        ("D14 (자석 ↔ 홀 소자 y67 z%s)" % f(body.SENSOR_YZ[1], 1), "226 (z8까지)", "자석 중심 %s, 가장 가까운 쇠(플랜지 아래 모서리) %s (≥100; 사양 방식 z8까지 %s / %s)"
         % (f(fg["d14_sensor"], 1), f(fg["d14_steel"], 1), f(fg["d14_sensor_z8"], 1), f(fg["d14_steel_z8"], 1))),
        ("합판", "%s m² (600 × 1200 포함)" % f(L2["plywood_cut_list"]["L1_area_m2"], 3),
         ("%s m², 조각 %d (400 × 1200 한 장)" % (f(L2["plywood_cut_list"]["area_m2"], 3), ply)) if ply else
         "0 (2026-10-16 A안: 옛 합판 10조각을 모두 출력)"),
    ]



# ------------------------------------------------------------------ R31 touchscreen rev 3 section

def _mbb(man, pid):
    p = next((q for q in man["parts"] if q["id"] == pid), None)
    return p["bbox"] if p else None


def _len_from_note(man, pid, rx):
    p = next((q for q in man["parts"] if q["id"] == pid), None)
    m = re.search(rx, (p or {}).get("note") or "")
    return float(m.group(1)) if m else 0.0


def _sound_path_min(man):
    """plan distance of every driver centre -> ear line (ears x611 +-75, y-350) to the standing screen rectangle (= check_electronics R31)."""
    cr = _mbb(man, "TS-CRADLE")
    rect = (cr[0], min(cr[1], 216.0), cr[3], TS.POCKET["back_wall_y"])
    best = 1e9
    for s_ in "LR":
        a_ = (body.DRIVER_POSE[s_][0], body.DRIVER_POSE[s_][1])
        for e_ in ((TS.XC - 75.0, -350.0), (TS.XC + 75.0, -350.0)):
            for k_ in range(2001):
                t_ = k_ / 2000.0
                x_, y_ = a_[0] + (e_[0] - a_[0]) * t_, a_[1] + (e_[1] - a_[1]) * t_
                best = min(best, math.hypot(max(rect[0] - x_, 0, x_ - rect[2]), max(rect[1] - y_, 0, y_ - rect[3])))
    return best


def touch_deviations(man):
    """(spec item, what the CAD built, why) - the deviation list for W1, formatted from the model (body / manifest), not typed in."""
    PLc = TS.PL
    lid = _mbb(man, "CU-SCREENLID")
    cr = _mbb(man, "TS-CRADLE")
    crf = _mbb(man, "TS-CRADLE-FOLD")
    CK = TS.CHECKS
    sr = PLc["sound_rule"]
    qy, qz = body.D(-47.0, 0.0)
    z212 = qz + (qy - 212.0) * body.TAN27
    pocket_back = body.YB - TS.POCKET["back_wall_y"]
    posts = [(xs, xs + body.POST) if i == 0 else (xs - body.POST, xs) for i, xs in enumerate(body.LID_SEAMS)]
    sp_post = PLc["seam"]["post"]
    rb = TS.CR["rib_relief_at_cheeks"]
    cv = TS.INSP["cover"]
    bo = TS.BOSS
    return [
        ("자리 블록 뚜껑 x%s~%s" % (f(PLc["lid"]["x"][0], 0), f(PLc["lid"]["x"][1], 0)),
         "x%s~%s (CAD L2 뚜껑, 이음마다 %s 틈)" % (f(lid[0], 1), f(lid[3], 1), f(body.LID_SEAM_GAP, 1)),
         "뚜껑 L·R(10/7부터 출력)과 틈 0이면 세 장이 나란히 들어가지 않음 (L2 설계). 화면 쪽 좌표는 모두 그대로; 받침과 뚜껑 끝 사이 %s (사양 %s)"
         % (f(cr[0] - lid[0]), f(min(CK["lid_x_margin"])))),
        ("자리 블록 뚜껑 뒤 y%s, 스피커 윗면 z%s, 스피커 y%s, 소리 규칙 앞판 %s°"
         % (f(PLc["lid"]["y"][1], 1), f(PLc["speaker_top_z"]), f(PLc["speakers_plan"][0][1], 1), f(sr["baffle_deg"], 0)),
         "뚜껑 뒤 y%s, 스피커 윗면 z%s, 유닛 중심 y%s z%s (앞판 %s°, 사용자 결정 2026-10-01)"
         % (f(lid[4], 1), f(body.SPK_ZT), f(body.DRV_YZ[0], 1), f(body.DRV_YZ[1]), f(body.ANGLE, 0)),
         "W1 3판은 %s° 값으로 계산. 화면 부품은 바뀌지 않고 여유만 바뀜: 접은 뒤끝 여유 %s → %s, 접은 윗면과 스피커 윗면 %s → %s, "
         "화면을 지나는 소리 길(평면) 최소 %s → %s (≥ 200), 다리 주머니 뒷벽 뒤 살 %s → %s, 27° 규칙 Ø94 아래 가장자리 (%s, %s) → (%s, %s), "
         "모듈 뒤 윗모서리 위 %s → %s (W1 ≥ 3.0)"
         % (f(sr["baffle_deg"], 0), f(CK["fold_rear_margin"]), f(body.YB - crf[4]), f(CK["fold_speaker_margin"]), f(body.SPK_ZT - crf[5]),
            f(CK["sound_paths_min"]), f(_sound_path_min(man)), f(CK["pocket_back_material"], 1), f(pocket_back, 1),
            f(sr["cone_lower_edge_yz"][0]), f(sr["cone_lower_edge_yz"][1]), f(qy), f(qz), f(sr["clear_above_module_edge"]), f(z212 - body.MOD_TOP))),
        ("A-7 앞 기둥 x%s~%s · x%s~%s (나사 x%s·%s이 기둥 안쪽 모서리 위; 'CAD가 기둥을 안쪽으로 2 옮기면 가운데')"
         % (f(sp_post[0][0], 0), f(sp_post[0][1], 0), f(sp_post[1][0], 0), f(sp_post[1][1], 0), f(body.SLID_SCREWS[0][0], 0), f(body.SLID_SCREWS[2][0], 0)),
         "x%s~%s · x%s~%s (CAD L2: 나사 밑이 기둥 가운데)" % (f(posts[0][0], 0), f(posts[0][1], 0), f(posts[1][0], 0), f(posts[1][1], 0)),
         "기둥 폭 10이라 나사를 가운데에 두려면 %s 옮겨야 함 (사양의 '안쪽으로 2'는 계산 실수). M3 인서트 Ø5 (p16 세트)가 기둥 안에 다 들어감"
         % f(abs(posts[0][0] - sp_post[0][0]), 0)),
        ("A-7 나사 자리 Ø8 기둥", "CAD L2 보스 10 × 12 (Ø8을 덮음), Ø3.4 + 위에서 Ø%s × %s" % (f(TS.LID_SCREW["cbore_d"], 1), f(TS.LID_SCREW["cbore_depth"], 1)),
         "L2 뚜껑 설계 그대로. 자리파기·머리 자리 z%s·나사 끝 z%s는 사양대로" % (f(TS.LID_SCREW["head_seat_z"]), f(TS.LID_SCREW["tip_z"]))),
        ("A 갈비 규칙 (배기 홈은 말 없음)", "갈비 x571·x651이 배기 홈 밑을 그대로 지남", "판을 받치는 갈비를 끊지 않음 (홈 34 중 2 mm 가림, 출력은 갈비 면이 베드라 문제 없음)"),
        ("A-9 출력 방향 (갈비 면을 베드에)", "그대로 - 자리만 잡은 판은 윗면을 베드에 두었으나 3판은 경첩 볼·발이 윗면에 있어 뒤집음", "(사양대로, 바뀐 점만 기록)"),
        ("C-3 보스 자리파기 Ø%s (w%s부터)" % (f(bo["cbore_d"], 1), f(bo["seat_w"], 0)),
         "물방울(꼭짓점 −u = 출력 때 위) 꼭짓점을 축에서 %s로 평평하게 자름 (평평한 천장 폭 %s)"
         % (f(body.BOSS_CB_CAP, 1), f(2 * (bo["cbore_d"] / 2 * math.sqrt(2.0) - body.BOSS_CB_CAP))),
         "보스가 R%s라 물방울 꼭짓점(%s)까지 파면 살이 %s만 남아 슬라이서가 지움 → 자르면 %s"
         % (f(bo["d"] / 2, 0), f(bo["cbore_d"] / 2 * math.sqrt(2.0)), f(bo["d"] / 2 - bo["cbore_d"] / 2 * math.sqrt(2.0)), f(bo["d"] / 2 - body.BOSS_CB_CAP, 1))),
        ("C-10 아래 뒤 모서리 C%s ('경첩 볼과 %s 이상')" % (f(TS.CHAMFER_C2, 0), f(rb["gap_after"])),
         "C%s (모델 최소 틈은 check_body.py C-10, 90°에서)" % f(body.CR_C2, 1),
         "C%s면 3D로 90°에서 %s (W1 3D 모델도 0.541; %s는 2D 값) → C%s로 키워 사양의 %s 이상을 지킴. 귀 붙는 면(w8~13)은 그대로"
         % (f(TS.CHAMFER_C2, 0), f(body.C2_GAP_AT_C2, 3), f(rb["gap_after"]), f(body.CR_C2, 1), f(rb["gap_after"]))),
        ("C-11 · C-17 뒤 패드 16 × 16, '45° 모따기로 서포트 없이'", "패드 +u 면(출력 때 아래를 향함)을 45° × %s 모따기 → 접혔을 때 받침 발에 얹히는 면 16 × %s"
         % (f(body.PAD_CH, 0), f(16 - body.PAD_CH, 0)),
         "모따기를 밖으로 붙이면 접은 받침이 뒤 발의 턱(y322.05)에 걸림; 안으로 깎으면 턱과 1.5 이상"),
        ("C-15 다리 클립 몸 u87~93 (45° 모따기)", "몸 +u 쪽에 45° 받침을 붙임 (w%s → u%s에서 뒷판)" % (f(TS.LCLIP["back_w"]), f(TS.LCLIP["u"][1] + TS.LCLIP["back_w"] - body.PLO)),
         "같은 이유 (출력 때 7.7 mm 내민 면). 접은 다리·뚜껑과 닿지 않음 (턱 끝 z73.63 그대로)"),
        ("E-1 점검창 덮개 걸쇠 2개 (모양은 CAD 재량)",
         "끼움부 아래·위 끝의 xr 방향 탄성 보 (뿌리 xr%s, 자유 끝 xr%s, 두께 %s × 높이 %s, 턱 밑 틈 %s) + 끝 쪽 돌기 %s (w%s~%s, 45° 들어가는·빼는 경사), "
         "뒷판 창 벽에 짝 홈 %s × 앞쪽 %s"
         % (f(body.COVER_TABS[0], 0), f(body.COVER_TABS[1], 0), f(body.COVER_BEAM[0], 1), f(body.COVER_BEAM[1], 1), f(body.COVER_BEAM[2], 1),
            f(body.COVER_BUMP[0], 1), f(body.PLI + body.COVER_BUMP_LIFT), f(body.PLI + body.COVER_BUMP_LIFT + 2 * body.COVER_BUMP_W[0] + body.COVER_BUMP_W[1]),
            f(body.COVER_GROOVE[0], 1), f(body.COVER_GROOVE[1], 1)),
         "덮개만으로는 걸 곳이 없어 받침에 홈을 냄 (리본·ZIF·전원선 길과 떨어진 자리). 처음 만든 뒷판 쪽(w 방향) 혀는 길이 2.1에 끼움 %s라 변형률 약 6.8%% "
         "(PETG 항복 3~4%%, 층을 가로질러 휨) → 출력 층 안에서 휘는 xr 방향 보로 바꿔 약 %s%%"
         % (f(body.COVER_SNAP[0], 1), f(body.COVER_SNAP[1] * 100, 1))),
        ("E-1 끼움부 두께 = 뒷판 %s" % f(body.PLO - body.PLI, 1), "w%s~%s (사양대로)" % (f(body.PLI, 1), f(body.PLO, 0)),
         "W1 3D 모델은 w10.7부터 (2.3) - CAD는 사양 글을 따름"),
        ("C-12 귀 윤곽 profile_uw", "그대로, 붙는 면만 아래 벽 안으로 %s" % f(body.EAR_INTO_WALL), "면이 겹치지 않게 한 몸으로 (모양 같음)"),
        ("C-17 출력 (서포트 말 없음)", "아래 벽 앞 턱(w−1~10.5, 유리가 얹히는 면) 밑에 트리 서포트", "윗변을 베드에 세우면 그 턱이 11.5 mm 내민 지붕이 됨 (유리 주머니 안, 앞이 트여 떼기 쉬움)"),
        ("F 리본 (뚜껑 밑 45° 접기)", "날카로운 접기로 그림, 말아 접기 여유 9.42는 길이에만 더함; 접힌 겹은 0.27씩 겹쳐 한 몸", "모델 표현 (실제 리본 모양과 같음)"),
        ("F 전원선 (MX1.25 → 점퍼 → GPIO 2·6)", "두 부품 TS-C-PWR-RED / -BLK (Ø1.1, 간격 1.3), 끝마다 F 점퍼 하우징", "가닥끼리 겹치는 불리언을 피함; 하우징은 CAD Pi의 헤더 상자(핀 끝까지 한 덩어리)와 겹침 = 의도"),
        ("F Pi 5 (micro-HDMI·방열판 추정 자리)", "CAD Pi에 micro-HDMI 2개(x564.5~571.5 · 578~585, y262~269.5, 윗면 z27.3)를 더함; 방열판은 CAD Pi 모델 그대로(x563.5~578.5 y279.5~294.5)",
         "리본이 HDMI 1 위에 얹힘(틈 0). W1 추정 방열판 상자(x572~583 y276~293)면 리본이 닿지만(사양 G-8) CAD Pi 자세에서는 5.37 떨어짐 - 실제 Pi로 확인"),
        ("C-3 화면 모서리 구멍 (깊이 모름)", "화면 모델에 Ø2.2 × 4 (나사산 안지름)", "M2.5×6 물림 3을 나사산 겹침으로 보이게 (추정)"),
    ]


TOUCH_W1_MODEL_NOTE = ("참고 (CAD와 다름이 아니라 W1 3D 모델 쪽): 다리 걸이 볼(C-13) 밑면은 사양·t03 B-B대로 45°, 뒷판 w13에서 u%s까지 만듦. "
                       "W1 `model3d/b1model.py`의 clevis_profile은 끝이 u35.37이라 밑면이 수평에서 20.6° (출력 때 서포트 필요) — 그쪽 모델만 고치면 됨.")


TOUCH_CONFIRM = [
    "**커넥터 방향 (G-1):** 화면 앞에서 커넥터 창이 오른쪽, 입구 +x로 모델함. 반대면 창·홈·구멍·클립을 x611 기준으로 뒤집고 리본은 A형(약 200 mm).",
    "**M2.5 구멍 깊이 (G-2):** 물림 = min(깊이 − 0.5, 4), 최소 2. 3.5보다 얕으면 와셔. 모서리가 박힌 스터드면 보스를 Ø6.2로 w13.7까지 팜(사양 G-2).",
    "**뒤 볼록판 높이 (G-3):** 2.1로 모델(뒷판과 0.4). 더 높으면 뒷판 안쪽 면 = 8.0 + 높이 + 0.4로 다시 계산.",
    "**Waveshare 3핀 선 길이 (G-4):** 120.54 mm 이상이면 이음이 뚜껑 밑, 짧으면 경첩 고리 안 → 열수축튜브.",
    "**리본 길이 (G-5):** 받침·뚜껑 출력 전에 폭 12 mm 종이띠로 길을 잼. 모델 RIBBON_LEN / W1 256 / 케이블 300.",
    "**뒤꿈치 틈 0.37 (G-6):** 출력 공차와 비슷 - 다리 발이 주머니에 잘 안 들어가면 뒤꿈치를 0.3 깎음.",
    "**화면 아래 끝 돌기 (G-7):** 위치(xr54.99~59.24 추정)와 높이(약 0.85)를 잼. 홈 xr48~66 밖이면 홈을 옮김.",
    "**실제 Pi 5 (G-8):** micro-HDMI 윗면 높이(z27.3 추정)와 리본이 그 위로 입구에 들어가는지, CAM/DISP 1 깊이(꽂는 길이 2.7), 방열판이 리본 기둥 x582.85~583.15를 "
    "비키는지(CAD Pi 모델 방열판은 5.37 떨어짐, W1 추정 상자는 닿음).",
    "**레일 인서트 길이 (G-9):** 4로 모델 = M3 바깥 5 × 높이 4 (10/7, 구멍 Ø4.2) — 자리파기 그대로. 길이가 다른 인서트로 바꾸면 자리파기 = 11.5 − (10 − 인서트 물림)으로 다시.",
]


def touch_section(man):
    L = []
    a = L.append
    N = TS.N
    P = N["points"]
    cr = _mbb(man, "TS-CRADLE")
    sc = _mbb(man, "TS-E-SCREEN")
    rlen = _len_from_note(man, "TS-C-DSI", r"펼친 길이 모델 [\d.]+ \(\+ 뚜껑 밑 말아 접기 [\d.]+ = ([\d.]+)\)")
    plen = max(_len_from_note(man, "TS-C-PWR-RED", r"≈ ([\d.]+) /"), _len_from_note(man, "TS-C-PWR-BLK", r"≈ ([\d.]+) /"))
    h22 = TS.pt(TS.CR_U[0], TS.CR_W[0], TS.TILT_HEEL)
    a("## 터치스크린 3판 (R31, Waveshare 7-DSI-TOUCH-C) — 부록 A10")
    a("")
    a("사양: `hardware/mechanical/touchscreen/rev3/design/CAD_SPEC_rev3.md` (W1, 3a, 사용자 승인 2026-10-01) + `numbers.json` (자리 블록 = L2 값), 도면 "
      "`rev3/drawings/t01~t06`, 화면 치수 `touchscreen/screen_dims/ws_7-DSI-TOUCH-C-details-size.jpg`. 좌표 변환은 `src/touchscreen_rev3.py` 하나(받침 좌표 "
      "xr = x − %s, u = 유리 아래 끝에서 위로, w = 유리 앞면에서 뒤로; 경첩 축 (y%s, z%s) = 받침 (u%s, w%s); 사용 25°, 뒤꿈치 22°, 접음 90°). "
      "조립 파일에는 사용 상태(25°, 다리 폄)만 들어가고, 접은 상태(90°, 다리는 받침 뒤 클립)는 그룹 `터치스크린 (접은 상태, 별도 보기)`로 "
      "`stl/assembly/`에만 있습니다(한 파일 조립·3MF·GLB·뷰어에서 뺌)."
      % (f(TS.XC, 0), f(TS.AX_Y), f(TS.AX_Z), f(TS.AX_U, 0), f(TS.AX_W, 0)))
    a("")
    a("| 부품 | id | 종류·파일 | 자리 (사용 상태, world) |")
    a("|---|---|---|---|")
    for pid in ("CU-SCREENLID", "TS-CRADLE", "TS-LEDGE-L", "TS-LEDGE-R", "TS-LEG", "TS-WINCOVER", "TS-RCLIP", "TS-SCREENCOVER", "TS-M3X20-HINGE-L", "TS-M3X20-HINGE-R", "TS-M3X20-LEG",
                "TS-M25-1", "TS-E-SCREEN", "TS-C-DSI", "TS-C-PWR-RED", "TS-C-PWR-BLK"):
        p = next((q for q in man["parts"] if q["id"] == pid), None)
        if not p:
            continue
        b = p["bbox"]
        fn = "`%s`" % os.path.basename(p["print_file"]) if p.get("print_file") else {"bought": "구매", "electronics": "전자"}.get(p["kind"], p["kind"])
        a("| %s | `%s`%s | %s | x%s~%s y%s~%s z%s~%s |" % (p["name_ko"], pid, " (외 3)" if pid == "TS-M25-1" else "", fn, f(b[0]), f(b[3]), f(b[1]), f(b[4]),
                                                         f(b[2]), f(b[5])))
    a("")
    a("**주요 값 (numbers.json ↔ 모델)** — 측정은 `check_body.py` (4) · `check_electronics.py` (4)가 입체에서 다시 잽니다.")
    a("")
    a("| 항목 | 사양 (numbers.json) | 모델 |")
    a("|---|---|---|")
    rows = [
        ("25° 받침 가장 앞 / 가장 높은 곳 / 가장 뒤", "y%s / z%s / y%s" % (f(P["use"]["cr_bot_front"][0]), f(P["use"]["cr_top_front"][1]), f(P["use"]["cr_top_rib"][0])),
         "y%s / z%s / y%s" % (f(cr[1]), f(cr[5]), f(cr[4]))),
        ("22° (뒤꿈치 멈춤) 가장 앞 — 금지선 y≤%s·z≥%s" % (f(TS.KEEP_Y, 0), f(TS.KEEP_Z)), "y%s" % f(N["footprint_y"]["front_22"]), "y%s (22~90° 휩쓸기 최소도 같음)" % f(h22[0])),
        ("25° 유리 아래 끝 / 위 끝", "(%s, %s) / (%s, %s)" % (f(P["use"]["glass_bottom"][0]), f(P["use"]["glass_bottom"][1]), f(P["use"]["glass_top"][0]), f(P["use"]["glass_top"][1])),
         "y%s / z%s (화면 외곽)" % (f(sc[1]), f(sc[5]))),
        ("접은 받침 y / z", "y%s~%s · z%s~%s" % (f(N["fold"]["y"][0]), f(N["fold"]["y"][1]), f(N["fold"]["rib_plane_z"]), f(N["fold"]["top_z"])),
         "같음 (뚜껑 뒤 y%s까지 %s, 스피커 윗면 z%s까지 %s)" % (f(body.YB), f(body.YB - N["fold"]["y"][1]), f(body.SPK_ZT), f(body.SPK_ZT - N["fold"]["top_z"]))),
        ("접은 뒤끝 여유 / 스피커 여유", "%s / %s (%s° L2 값)" % (f(N["checks"]["fold_rear_margin"]), f(N["checks"]["fold_speaker_margin"]), f(TS.PL["sound_rule"]["baffle_deg"], 0)),
         "%s / %s (%s°)" % (f(body.YB - N["fold"]["y"][1]), f(body.SPK_ZT - N["fold"]["top_z"]), f(body.ANGLE, 0))),
        ("귀 ↔ 멈춤 블록·홈 바닥", "22°: %s (닿음), 25~90°: ≥ %s" % (f(N["checks"]["ear_block_gap_22"]), f(N["checks"]["ear_block_gap_25_90"])), "check_body.py C-12 (0.5° 간격)"),
        ("받침다리 축 / 발끝 / 각도", "(%s, %s) / (%s, %s) / %s°" % (f(TS.LG["pivot_yz"][0]), f(TS.LG["pivot_yz"][1]), f(TS.LEG_TIP_YZ[0]), f(TS.LEG_TIP_YZ[1]), f(TS.LG["angle_deg"])),
         "(%s, %s) / 같음 / %s° (축~발끝 %s)" % (f(TS.LEG_AX_YZ[0]), f(TS.LEG_AX_YZ[1]), f(TS.LEG_ANGLE), f(TS.LEG_LEN_MODEL))),
        ("뚜껑 나사 M3×10", "자리파기 Ø%s × %s, 머리 자리 z%s, 끝 z%s, 인서트 물림 %s" % (f(TS.LID_SCREW["cbore_d"]), f(TS.LID_SCREW["cbore_depth"]), f(TS.LID_SCREW["head_seat_z"]),
                                                                       f(TS.LID_SCREW["tip_z"]), f(TS.LID_SCREW["insert_engage"])),
         "같음 (끝과 인서트 구멍 바닥 z%s 사이 %s)" % (f(body.Z_LIDU - body.INS3[3]), f(TS.LID_SCREW["tip_z"] - (body.Z_LIDU - body.INS3[3])))),
        ("DSI FFC 길이 (300 mm B형)", "%s (여유 %s)" % (f(TS.RIBBON["total"]), f(TS.RIBBON["margin"])), "%s (여유 %s; 접기 말림 여유 포함)" % (f(rlen, 1), f(TS.RIBBON["cable"] - rlen, 1))),
        ("전원선 (MX1.25 → GPIO 2·6)", "%s (있는 길이 %s~%s)" % (f(TS.PWIRE["total"]), f(TS.PWIRE["available"][0], 0), f(TS.PWIRE["available"][1], 0)), "약 %s (하우징·핀·꽂는 여유 포함)" % f(plen, 0)),
        ("뚜껑 위 금지선 (모듈 위)", "y≤%s·z≥%s에 아무것도 없음" % (f(TS.KEEP_Y, 0), f(TS.KEEP_Z)), "check_body.py C-16 · G, check_electronics.py (선 가장 앞 y≈221.6)"),
    ]
    for r_ in rows:
        a("| %s | %s | %s |" % r_)
    a("")
    a("**W1에 넘길 사양과 다른 점 (가장 작은 고침)**")
    a("")
    a("| 사양 항목 | CAD가 만든 것 | 이유 |")
    a("|---|---|---|")
    for r_ in touch_deviations(man):
        a("| %s | %s | %s |" % r_)
    a("")
    a(TOUCH_W1_MODEL_NOTE % f(body.CLEVIS_END_U))
    a("")
    a("**07_터치스크린 출력:**")
    a("")
    for r in [r for r in man["print"] if r["folder"].startswith("07")]:
        a("- `%s` — %s mm, 속 꽉 채움 %s g. %s" % (os.path.basename(r["file"]), " × ".join(f(v, 1) for v in r["size_mm"]), f(r["mass_g_solid_petg"], 0), r["note"]))
    lid = next((r for r in man["print"] if "화면뚜껑" in r["file"]), None)
    if lid:
        a("- (05) `%s` — %s mm. %s" % (os.path.basename(lid["file"]), " × ".join(f(v, 1) for v in lid["size_mm"]), lid["note"]))
    a("")
    a("**조립 순서:** 아래 '조립 순서 (L2)'의 터치스크린 단계(화면 → 받침 → 화면 뚜껑 → 뚜껑 놓기 → 받침다리). O4 정비는 '분해·점검' 표.")
    a("")
    a("**받은 부품으로 확인할 것 (사양 G, 출력 전에):**")
    a("")
    for t_ in TOUCH_CONFIRM:
        a("- " + t_.replace("RIBBON_LEN", f(rlen, 0)))
    a("")
    return L

def jig_section(rs, extra):
    """text under the 08_합판지그 table (W1 plywood jigs 2026-10-02, cut down 2026-10-07; src/plywood_jigs.py, guide cad/jigs/README.md)."""
    L = []
    a = L.append
    gaps = [m_.group(1) for m_ in (re.search(r"틈([\d.]+)", r["name"]) for r in rs) if m_]
    g_req = sum(r.get("mass_g_print_est") or 0.0 for r in rs)
    hours = sum(r.get("print_min_est") or 0.0 for r in rs) / 60.0
    nb = len(body.BACK_HOLES)
    nbot = len(body.BOT_HOLES_BUCK) + len(body.BOT_HOLES_PI)
    a("08 폴더는 합판 가공용 출력 지그 %d개(악기당 1벌)입니다. 공구를 새로 사지 않고 가진 전동 드릴과 Ø8·Ø4 날로 오꾸메 조각에 남은 구멍을 모델(`src/body.py`) "
      "자리에 뚫기 위한 것이고, 쓰는 법은 **[`jigs/README.md`](jigs/README.md)**에 있습니다: J-b 모서리 자석 새들(뒤판 윗모서리 4곳), J-d3 뒤판 환기 Ø8 구멍판 "
      "(%d개), J-d4 아랫판 흡기 Ø8 구멍판 (%d개), J-e 깊이 게이지·시험 블록. 2026-10-07부터 뚜껑·끝벽·스피커 안쪽 옆판은 출력이라 그 지그(J-a·J-c·홈 J-d·J-f)는 "
      "없습니다. 모두 PETG 0.2 mm 층, 서포트 없음, **STL 방향 그대로**(돌리지 않음). J-e를 가장 먼저 뽑아 자투리에 시험합니다." % (len(rs), nb, nbot))
    a("")
    if gaps:
        a("**J-b 새들 %d개(틈 %s)는 모두 뽑습니다.** 쓰는 것은 하나지만 합판 실제 두께가 판마다 조금씩 달라 미리 알 수 없으므로, %d개를 다 뽑아 판 모서리에 "
          "손으로 밀어 끼워지는 것 중 가장 좁은 하나를 씁니다(출력하면 틈이 0.1~0.2 좁아져 보통 11.6이나 11.9)." % (len(gaps), " · ".join(gaps), len(gaps)))
        a("")
    a("**필라멘트:** 지그 %d개는 벽 3줄 + 채움 15 %% 기준 %s입니다(`plywood_jigs.est_print` 어림, 슬라이서 값이 기준; 10/7 전 지그 25개 약 510 g · 15시간). "
      "구매 목록 PETG 8 kg은 악기 출력 약 7.0 kg + 실패 여유 약 1 kg(i090)으로 잡혀 있습니다 — 10/7에 뚜껑·끝벽·안쪽 옆판 출력(약 0.63 kg)이 늘고 지그가 "
      "약 0.37 kg 줄어 여유가 약 0.26 kg 줄어듭니다. 악기 출력에서 실패가 많으면 1 kg 스풀(16,150원)을 더 삽니다. 지그 색은 아무거나."
      % (len(rs), ("약 %s g, 약 %s시간" % (f(round(g_req, -1), 0), f(round(hours, 1), 1))) if g_req else "약 0.14 kg"))
    a("")
    return L


def main():
    man = json.load(open(os.path.join(OUT, "manifest.json")))
    _PIG_OUT[0] = _pig_out(man)
    rows = man["print"]
    fg = FG
    L = []
    a = L.append
    a("# Toccata CAD — 출력용 STL과 전체 조립 (v4 W1+ r4.5 건반 액션 + L2 한 몸 뒷바)")
    a("")
    a("이 폴더의 모든 파일은 `src/build_all.py`가 설계 모델에서 바로 만든 것입니다. 손으로 옮겨 적은 치수는 없습니다.")
    a("- **건반 액션:** `hardware/mechanical/key-action-v4/model/geometry.json`(도면 1~15가 그려지는 같은 모델)")
    a("- **본체·뒷바:** L2 한 몸 뒷바 `spec/body_L2.json`(사용자 요청 2026-10-01, W1 음향 확인 통과). 스피커 각도 등 모든 스피커 수치는 "
      "`src/body.py`의 `ANGLE = %s` 한 줄에서 사양 규칙으로 계산합니다. 그릴 격자·가스켓·보드 구멍은 v3.2 사양(`spec/body_speakers.json`, "
      "`body_centre_unit.json`)에서 옮김. 이전 뒷바: L1 `src/body_L1.py`·`electronics_L1.py`, v3.2 `body_v3_tall.py`(둘 다 쓰지 않음)" % f(fg["angle"], 1))
    a("- **전자 부품 위치:** 회로 rev B(BRD-01·02), 가운데 칸은 사양 `centre_contents` 상자 그대로")
    a("- **추출한 사양:** `spec/*.json`. 항목마다 출처가 달려 있고, 추정값에는 `assumed`가 표시돼 있습니다.")
    a("- **터치스크린:** R31 3판(Waveshare 7-DSI-TOUCH-C, W1 `touchscreen/rev3/design/CAD_SPEC_rev3.md` 3a + `numbers.json`, 사용자 승인 2026-10-01). "
      "화면 뚜껑에 경첩·다리 주머니·리본 구멍을 더하고 받침·받침다리·점검창 덮개·리본 클립을 `07_터치스크린`으로 뽑습니다. 화면은 25°로 서 있고 "
      "접은 상태는 따로 보는 그룹입니다(부록 A10, 아래 '터치스크린 3판').")
    a("")
    a("좌표는 설계 문서와 같습니다. 원점은 A0 왼쪽 경계(x=0), 흰건반 앞끝(y=0), 책상(z=0)이고 단위는 mm입니다. 모듈 Ok는 x = 47 + 164.5·(k−1)에서 시작합니다.")
    a("")
    # ---------------- L2 summary
    a("## L2 한 몸 뒷바 한눈에")
    a("")
    a("| 항목 | L1 (2026-09-30) | L2 (이 모델) |")
    a("|---|---|---|")
    for r_ in key_figures(man):
        a("| %s | %s | %s |" % r_)
    a("")
    a("- **평면:** x−16~1238 × y0~%s 직사각형(R27). 뒷바(y%s~%s)는 모듈 뒷벽 y212 뒤 2.0 mm 공기 틈을 두고 섭니다(D15: 딱딱하게 닿지 않음). "
      "위치는 끝 부속 볼의 방진 브래킷 BRK2 핀이 정합니다." % (f(fg["depth"]), f(fg["y0"], 0), f(fg["depth"])))
    a("- **가운데 유닛** x260~962: 앞벽이 없어 뚜껑을 열면 모듈 USB-C 플러그를 위에서 바로 잡습니다(앞 공간 y214~241). 뚜껑 L(x260~501)·R(x721~962)은 "
      "출력(10/7부터, 전엔 오꾸메) + 자석 3쌍, 가운데 화면 뚜껑(x501.5~720.5, 이음마다 0.5 틈)은 출력 + M3×10 4개입니다. 모두 가운데 유닛 벽·레일·기둥에만 얹혀 모듈에 힘이 가지 않습니다.")
    pc_ = L2["centre"].get("power_2026_10_07", {})
    a("- **전원 (2026-10-07):** LiFePO4 12.8 V 6 Ah 배터리 (76.8 Wh, 140 × 72 × 35, 약 %s kg - 상품 설명)가 가운데 유닛 A칸 바닥의 배터리 틀 안에 있습니다. "
      "버스 12.8 V 공칭 (10.0~14.6 V): 배터리 → XT60 → 퓨즈 5 A ATO → KCD1 → 강압(5.1 V: Pi·허브) + 앰프 (12.8 V에서 약 8 W/채널), 사용 시간 약 %s~%s시간. "
      "퓨즈 홀더는 사용자 ATC/ATO 칼날형 (40.1 × 11.1 × 33.8, 12 AWG 꼬리를 16 AWG와 이음)으로 앞 공간 위 배터리 틀 퓨즈 선반에 옆으로 눕혀 끼움 (덮개 +y). "
      "**퓨즈 갈기:** 스위치를 끄고 뚜껑 L을 들어 홀더를 받침에서 위로 빼고, 선 축으로 90° 돌려 덮개를 위로 약 20 뽑아 5 A ATO 퓨즈를 바꾼 뒤 되돌려 눌러 끼웁니다. "
      "USB-C 입력은 없습니다. **충전:** 스위치를 끄고 뚜껑 L(자석)을 들어 배터리 윗면의 DC 5.5×2.1 충전 선에 LiFePO4 충전기를 꽂습니다 — XT60은 뽑지 않음. "
      "12 V 전원 장치로 시험할 때만 XT60 짝을 뽑고 전원 장치의 XT60 암을 꽂습니다."
      % (f(pc_.get("mass_kg_est", 0.9), 1), f(pc_.get("runtime_h", [3.5, 4.4])[0], 1), f(pc_.get("runtime_h", [3.5, 4.4])[1], 1)))
    a("- **배터리·퓨즈 홀더를 받으면 확인 (도착 점검):** " + " · ".join(pc_.get("on_arrival", [])) + ". 다르면 배터리 틀(05)을 뽑기 전에 고칩니다.")
    a("- **스피커 파트:** 유닛 중심 (x%s / %s, y%s, z%s), 축 (0, −%s, %s) = 수평 위 %s°. 스피커 윗면은 z%s, L1보다 %s 높습니다 — "
      "27° 소리 길 %s(모듈 뒤 윗모서리 위), 그릴 판 아래 모서리 y213 뒤(R18), 앞판 각도 %s°가 정한 값입니다(부록 A9). "
      "**%s° 안(%s):** 윗면 z%s, 뒤 y%s, 플랜지 여유 %s. `src/body.py`의 `ANGLE`만 바꾸면 모든 파일이 다시 만들어집니다."
      % (f(fg["drv_x"]["L"], 1), f(fg["drv_x"]["R"], 1), f(fg["drv"][0]), f(fg["drv"][1]), f(body.SA, 4), f(body.CA, 4), f(fg["angle_v"], 1),
         f(fg["top"]), f(fg["top"] - fg["l1_top"]), f(fg["sp"]["module"]), f(fg["angle"], 1), f(ALT, 0),
         ("처음 L2 선택, 사용자가 2026-10-01 %s°로 바꿈" % f(SEL_ANGLE, 0)) if abs(ALT - EARLIER) < 1e-6 else "사용자가 고른 각도",
         f((pareto_row(ALT) or {}).get("pod_top_z", 0)), f((pareto_row(ALT) or {}).get("back_y", 0), 1),
         f((pareto_row(ALT) or {}).get("flange_corner_clearance_mm", 0))))
    sp_min = min(fg["sp"][k] for k in ("module", "flange", "gasket", "F", "grille_foot"))
    if sp_min >= 3.0:
        sp_txt = ("모듈 뒤 윗모서리 위 %s로 지납니다. 다만 사양의 선은 앞판 면의 Ø94 가장자리 D(−47, 0)에서 시작해 앞에 붙는 가스켓(3)·플랜지(4) 뒤에서 "
                  "출발하므로 그 둘은 선을 걸치고, 아래 모서리만 선보다 %s / %s 아래입니다(사양 표의 값). 실제로 소리가 나오는 가장자리(유닛 프레임 입구 "
                  "D(−45, 7))에서 그은 27° 선은 모듈 뒤 윗모서리 위 %s로 지나고 그릴 아래 띠 말고는 단단한 것에 닿지 않습니다(check_body.py가 광선·3 mm 띠로 확인)"
                  % (f(fg["sp"]["module"]), f(fg["sp"]["flange"]), f(fg["sp"]["gasket"]), f(_real_path_clear(), 2)))
    else:
        sp_txt = ("모듈 뒤 윗모서리 위 %s로 지납니다(W1 ≥3.0). 사양의 선은 앞판 면의 Ø94 가장자리 D(−47, 0)에서 시작해 앞에 붙는 가스켓(3)·플랜지(4) 뒤에서 "
                  "출발하므로 그 둘은 선을 걸치고, 아래 모서리가 선보다 %s(플랜지) / %s(가스켓) 아래입니다. 플랜지 모서리 여유(%s)는 W1 엄격 기준 3.0보다 작지만 "
                  "%s°를 고를 때 W1이 받아들였습니다(모듈 뒤 윗모서리 여유 3 이상 조건%s). 실제로 소리가 나오는 가장자리(유닛 프레임 입구 D(−45, 7))에서 그은 "
                  "27° 선은 모듈 뒤 윗모서리 위 %s로 지나고 그릴 아래 띠 말고는 단단한 것에 닿지 않습니다(check_body.py가 광선·3 mm 띠로 확인)"
                  % (f(fg["sp"]["module"]), f(fg["sp"]["flange"]), f(fg["sp"]["gasket"]), f(fg["sp"]["flange"]), f(fg["angle"], 0),
                     ", 사양 angle_decision %s" % f(AD["w1_flange_corner_accepted_mm"]) if AD.get("w1_flange_corner_accepted_mm") else "",
                     f(_real_path_clear(), 2)))
    a("- **소리 길:** Ø94 구멍 아래 가장자리에서 연주자 쪽 27° 선이 %s. "
      "그릴 판 아래 모서리만 선이 판 밑으로 %s(수직 방향 %s) 지나가는데, 판이 구멍 뚫린 격자이고 아래 링 벽이 없어 W1이 승인한 예외입니다."
      % (sp_txt, f(fg["sp"]["plate_perp"]), f(fg["sp"]["plate_vert"])))
    a("- **D14:** 자석 중심에서 홀 소자(y67, z%s = 센서 바 포켓 바닥 12.19 + 0.75)까지 %s, 가장 가까운 쇠(플랜지 아래 모서리)까지 %s (≥100; 사양 표는 z8까지 재서 %s / %s). "
      "EL·ER 끝 부속을 포함한 홀 소자 88개 모두 같은 y67 줄이라 3D 거리도 같습니다(check_body.py)."
      % (f(body.SENSOR_YZ[1], 1), f(fg["d14_sensor"], 1), f(fg["d14_steel"], 1), f(fg["d14_sensor_z8"], 1), f(fg["d14_steel_z8"], 1)))
    a("- **선 가리기:** 밖에서 선이 보이는 곳은 계획된 구멍뿐입니다 — 뚜껑 L·화면 뚜껑·뚜껑 R의 배기 홈 아래(위와 앉은 눈높이에서 뒤 줄의 12.8 V선·스피커선 L, "
      "뚜껑 R 홈 아래 스피커선 R)와 건반 뒤 2 mm 틈(y212~214, 모듈 플러그 윗면 z18.3). 가리려면 배기 홈 밑에 검은 망사나 스피커 천을 붙이고(홈을 줄여도 "
      "앉은 눈높이 선은 가려지지 않음), 2 mm 틈에 사양의 회색 펠트 띠 2 mm를 끼웁니다. 터치스크린 3판(%s°, 위 끝 z%s)이 앉은 눈높이에서 화면 뚜껑 "
      "배기 홈(y300~325)을 가립니다 (접으면 받침 아래)." % (f(TS.TILT_USE, 0), f(_mbb(man, "TS-CRADLE")[5])))
    a("")
    # ---------------- W1 conditions
    holes, open_lat, open_d94 = grille_stats(man)
    a("## W1 음향 조건 (2026-10-01 통과, 조건부) — 모델에 넣은 방법")
    a("")
    a("| 조건 | 모델 / 조립 |")
    a("|---|---|")
    a("| 폴 벤트: 자석 뒤 가운데 구멍 축 방향 10 mm 이상 비움 (뒤판·윗판·솜 모두) | 축 방향으로 가장 가까운 %s까지 %s mm 비어 있음(check_body.py가 광선과 Ø20 × 10 원기둥으로 확인). 솜은 이 자리에 넣지 않음(스피커 뒤판 메모) |" % (fg["pole_wall"], f(fg["pole"], 1)))
    a("| 흡음솜: 폴리에스터를 상자 전체에 느슨하게 (가운데 포함), 유닛 뒤 10 mm와 폴 벤트 앞은 비움 | 조립 순서 2번(Ø94 구멍으로 넣음). 모델에는 솜이 없음 |")
    a("| 그릴 개구율 40 %% 이상, 구멍 Ø3 이상 | 구멍 %s개, 모두 Ø3 원이 들어가는 칸만 뚫음. 개구율 %s %% (격자), Ø94 앞 %s %% |"
      % (holes if holes is not None else "—", f(open_lat, 1) if open_lat else "—", f(open_d94, 1) if open_d94 else "—"))
    a("| 그릴 판 두께 2 mm 이하 (두꺼우면 구멍 앞 모따기) | 판 2 (w11~13) |")
    a("| 27° 선이 그릴 판 아래 모서리 밑으로 지나감 (판이 격자라는 전제의 예외; W1 승인 때 43°에서 0.94) | %s°에서 선이 판 아래 모서리 밑 %s (수직 %s). "
      "판 아래 2 mm는 막힌 띠(s−50~−48)라 27°에서 유닛 콘 맨 아래 약 1 mm가 가려짐 — 음향 영향은 작음. 격자 칸은 s−48부터 |"
      % (f(fg["angle"], 0), f(fg["sp"]["plate_perp"]), f(fg["sp"]["plate_vert"])))
    a("| 그릴은 나사 4개로 떨리지 않게 | 고정 구멍 4-Ø4.5, 직결피스 8호 19 mm × 4 → 앞판 파일럿 Ø3.4 × 9 |")
    a("| 각도: W1은 43°로 진행, 40°도 음향상 가능(모듈 모서리 여유 3 이상) → 사용자 %s° 선택 (2026-10-01, W1 전달), 플랜지 모서리 여유 %s도 W1이 받아들임 "
      "| ANGLE = %s: 윗면 z%s, 뒤 y%s, 모듈 뒤 윗모서리 여유 %s, 플랜지 모서리 %s, 가운데 귀와 %s°. %s°(처음 선택) 값은 위 '%s° 안' |"
      % (f(SEL_ANGLE, 0), f(AD.get("w1_flange_corner_accepted_mm", fg["sp"]["flange"])), f(fg["angle"], 1), f(fg["top"]), f(fg["depth"]),
         f(fg["sp"]["module"]), f(fg["sp"]["flange"]), f(fg["aim_off"], 1), f(EARLIER, 0), f(ALT, 0)))
    a("| Qtc: 유닛 뺀 부피 기준 (Vas 3 L 가정; 43°에서 W1 1.12 / 솜 1.07), Vas 4 L이면 약 %s라 솜은 필수 | %s°: 유닛 뺀 %s L → Qtc %s, Fc %s~%s Hz; "
      "솜 넣으면 약 %s, Fc %s~%s Hz (W1 전달 값 약 1.13 / 1.09). Vas는 단계 0에서 측정 |"
      % (f(QTS * math.sqrt(1.0 + 4.0 / fg["net_spec"])), f(fg["angle"], 0), f(fg["net_spec"], 3), f(fg["qtc_net"]), f(fg["fc_net"][0], 0),
         f(fg["fc_net"][1], 0), f(fg["qtc_fill"]), f(fg["fc_fill"][0], 0), f(fg["fc_fill"][1], 0)))
    a("| 밀폐 유지 (나사 길이·막힌 구멍) | 고무발 8호 13 mm 이하 + 구멍에 MS 폴리머, 그릴 8호 19 mm 이하, 유닛 M4×12 이하 (L69 인서트는 면까지), 손잡이볼트 "
      "M4×20 (L72, 최대 M4×22) — 이보다 길면 밀폐면을 밂. 안쪽 옆판(10/7부터 출력, 벽 5줄 + 채움 40 %% 이상)의 M4 열 인서트 구멍 Ø%s × %s 막힘: "
      "판 %s 중 뒤에 PETG **%s** 남음 (밀폐 기준 %s 이상) — 인서트(바깥 Ø%s × 길이 %s)는 면까지만 |"
      % (f(body.INS_HOLE[0], 1), f(body.INS_HOLE[1], 1), f(body.T, 1), f(body.T - body.INS_HOLE[1], 1), f(body.INS_BACK_MIN, 1), f(body.INS[0], 0),
         f(body.INS[2], 0)))
    a("")
    # ---------------- folders
    a("## 폴더")
    a("")
    a("| 경로 | 내용 |")
    a("|---|---|")
    a("| `stl/print/` | **출력용 — 이 폴더는 전부 뽑으면 됩니다.** 악기 1대 부품, 조립 공구 1벌(06), 만능기판 지그 2개(09, 사용법 "
      "[`jigs/README.md`](jigs/README.md))만 들어 있고, 파일 이름 끝 개수(`__7개`)만큼 뽑습니다. "
      "베드 위 방향으로 놓여 있습니다. 같은 내용을 한 파일로 묶은 것이 `Toccata_출력STL_전체.zip`입니다 |")
    a("| `stl/print_extra/` | **꼭 뽑지 않아도 되는 것.** 선택 부품(화면 덮개), 대안(PORON 6T를 살 때의 패드 바), 예비 건반 — "
      "아래 '선택·대안·예비' 표 |")
    a("| [`jigs/`](jigs/README.md) | 기판 지그 사용 설명서 `README.md` (손으로 쓴 안내서 — 지그 STL은 빌드가 `stl/print/09_기판지그/`에 씀; 생성 "
      "`src/perfboard_jigs.py`, 확인 `src/check_perfboard_jigs.py`. 합판 지그(08)는 2026-10-16 A안으로 합판이 없어져 만들지 않음 - "
      "`src/plywood_jigs.py`는 기록으로 남김) |")
    a("| `stl/annotated/` | **보기용(출력 금지).** 부품 옆에 치수선과 숫자를 입체로 붙였습니다. 조립 방향으로 놓여 있습니다. |")
    a("| `stl/assembly/` | 모든 부품을 조립 위치 그대로 둔 파일입니다. 그룹별 STL을 한꺼번에 열면 전체가 맞춰집니다 (단 `터치스크린_(접은_상태,_별도_보기).stl`은 접은 자세라 같이 열면 사용 상태 화면과 겹침; "
      "`댐퍼_페달_(바닥)`은 바닥 위치). `Toccata_전체조립.stl`은 한 파일에 전부 들어 있습니다 (접은 화면·페달 빼고) |")
    a("| `Toccata_전체조립.3mf` | 그룹·색 이름이 붙은 전체 조립(슬라이서·3D 뷰어용) |")
    a("| `Toccata_전체조립.glb` | 웹 뷰어용 |")
    a("| `manifest.json` | 부품마다 id, 이름, 종류, 그룹, 외곽 상자, 출력 파일 |")
    a("| `spec/` | 문서에서 뽑은 세부 사양(출처 포함). 뒷바는 `body_L2.json` |")
    a("| `viewer/` | 통합 아티팩트 09 CAD 탭 원본(cad.html·css·js, parts.json) |")
    a("| `src/` | 생성기. `python3 src/build_all.py` 한 번으로 STL·3MF·GLB·manifest·README·뷰어 데이터를 모두 다시 만듭니다(약 10~20초). "
      "검사: `check_interf.py`(건반 액션), `check_body.py`, `check_electronics.py`, `check_perfboard_jigs.py`(기판 지그) |")
    a("")
    # ---------------- print list
    a("## 출력 목록")
    a("")
    a("`stl/print/`의 파일을 **모두, 이름 끝 개수만큼** 뽑으면 악기 1대와 조립 공구 1벌(06)이 됩니다. 꼭 뽑지 않아도 되는 것(선택·대안·예비)은 "
      "`stl/print_extra/`에 따로 두었습니다(이 목록 아래 표). 순서: 단계 0 시편(`key-action-v4/printables/stage0`)으로 시험 → 건반 액션 모듈 1개 → "
      "시험 21 통과 뒤 나머지. 화면 받침(07)은 화면 실물로 뒤 커넥터 방향을, 배터리 틀(05)은 받은 배터리로 크기·선이 나오는 면·높이를 확인한 뒤 뽑습니다. "
      "10/7부터 뚜껑 L·R·끝벽 L·R·스피커 안쪽 옆판 L·R, 10/16부터 나머지 판(스피커 바깥 옆판·뒤판·윗판·아랫판, 가운데 아랫판·뒤판 3토막씩)도 "
      "05에서 출력합니다 - 합판은 없습니다.")
    a("")
    by = collections.OrderedDict()
    by_extra = collections.OrderedDict()
    for r in rows:
        (by_extra if r.get("extra") else by).setdefault(r["folder"], []).append(r)
    tot_q = 0
    tot_g = 0.0
    for folder, rs in by.items():
        a("### %s%s" % (folder, " (악기당 1벌)" if folder.startswith("06") else " (악기당 1벌, 합판 가공용 지그)" if folder.startswith("08")
                         else " (악기당 1벌, 만능기판 자르기·뚫기 지그)" if folder.startswith("09") else ""))
        a("")
        notes = collections.OrderedDict()
        for r in rs:
            notes.setdefault(r["note"], []).append(r)
        keyof = {}
        for i, n in enumerate(notes):
            keyof[n] = chr(ord("a") + i) if i < 26 else "a" + chr(ord("a") + i - 26)
        a("| 파일 | 개수 | 크기 (베드 위, mm) | 속 꽉 채움 질량 g | 재료 | 방법 |")
        a("|---|---|---|---|---|---|")
        for r in rs:
            if not r.get("variant"):
                tot_q += r["qty"]
                tot_g += r["mass_g_solid_petg"] * r["qty"]
            a("| `%s` | %d | %s | %.1f | %s | %s |" % (os.path.basename(r["file"]), r["qty"],
                                                   " × ".join("%.1f" % v for v in r["size_mm"]), r["mass_g_solid_petg"],
                                                   r["material"], keyof[r["note"]]))
        a("")
        for n, k in keyof.items():
            a("- **%s** %s" % (k, n))
        a("")
        if folder.startswith("05"):
            n05 = sum(r["qty"] for r in rs)
            big = max(rs, key=lambda r: max(r["size_mm"]))
            a("05 폴더는 L2 뒷바 출력물 %d종 %d개입니다. 가장 큰 것은 `%s`(%s mm)로 256 판 안에 들어갑니다. "
              "`CU화면뚜껑_터치3판`은 터치스크린 3판의 경첩 볼·다리 주머니·리본 구멍·받침 발이 붙은 뚜껑이라 갈비 면을 베드에 둡니다(07 폴더 부품과 짝)."
              % (len(rs), n05, os.path.basename(big["file"]), " × ".join("%.1f" % v for v in big["size_mm"])))
            a("")
        if folder.startswith("07"):
            a("07 폴더는 R31 터치스크린 3판 출력물입니다. 받침은 윗변을 베드에 세워(높이 %s) 귀가 위로 오고, 아래 벽 앞 턱(유리가 얹히는 면) 밑에만 "
              "트리 서포트가 필요합니다. 선택 부품인 화면 덮개는 `stl/print_extra/선택_화면덮개`에 있습니다. 출력 전에 부록 A10의 '받은 부품으로 확인할 것'을 먼저 봅니다."
              % f(TS.CR["print_height"]))
            a("")
        if folder.startswith("08"):
            L.extend(jig_section(rs, [r for r in rows if r.get("jig") and r.get("extra")]))
        if folder.startswith("09"):
            g9 = sum(r.get("mass_g_print_est") or 0.0 for r in rs)
            a("09 폴더는 2026-10-07 추가: PED 보드 1장을 양면 만능기판(80 × 120, 구멍 30 × 42, 2.54 간격; 한 장에서 70 × 50 두 조각)에서 자르고 고정 구멍을 뚫는 판 "
              "지그 %d개입니다(A16, 10/31: 제어 기판 MB 7장은 80 × 120을 통째로 써서 MB 지그 P-MB는 없어짐). 밑의 Ø0.9 핀 6개를 시트 구멍에 꽂으면 지그가 격자에 "
              "맞고, 네 옆면이 자르는 선(커터칼로 긋고 꺾음), 구멍이 나사 Ø3.2·위치 핀 Ø3.0 안내입니다. "
              "쓰는 법은 [`jigs/README.md`](jigs/README.md) '기판 지그'. 벽 3줄 + 채움 15 %% 기준 약 %s g. 생성 `src/perfboard_jigs.py`, 확인 `src/check_perfboard_jigs.py`."
              % (len(rs), f(round(g9), 0)))
            a("")
    n_main = sum(len(v) for v in by.values())
    n_tool = len(by.get("06_출력공구", []))
    n_jig = sum(len(v) for k_, v in by.items() if k_.startswith("08") or k_.startswith("09"))
    a("`stl/print`는 모두 %d종(악기 %d종 + 공구 %d종%s)이고, 06 공구%s를 뺀 악기 출력 부품은 모두 %d개입니다. 질량은 속을 100%% 채운 PETG(1.27 g/cm³) 기준이라 "
      "실제(슬라이서 채움 %%)보다 큽니다. 악기 출력 부품만 모두 합하면 %.2f kg입니다. 한 파일 묶음 `Toccata_출력STL_전체.zip`에는 `stl/print` 전체(%d종)가 들어 있습니다."
      % (n_main, n_main - n_tool - n_jig, n_tool, " + 기판 지그 %d종" % n_jig if n_jig else "", "와 09 기판 지그" if n_jig else "", tot_q, tot_g / 1000, n_main))
    a("")
    a("예비 건반은 부품표(parts_list.json)대로 `stl/print_extra/예비_건반`에 있습니다(백건 파일마다 +1 = 10개, 흑건 C#·D# +2, F# +1, G# +1, A#·A#0 +2 = 6개). "
      "레버 캐리어와 패드 바는 예비 없이 필요할 때 `stl/print`의 위치별 파일로 뽑습니다. "
      "**서포트 (A12, 2026-10-29):** 슬라이서 서포트는 모두 끕니다. 서포트가 필요한 곳은 부품을 나눠 없앴고(프레임 = 바닥틀 + 레버틀 + 가이드 탭, "
      "레버 = 캐리어 + 덮개, 패드 바 윗면 한 평면), 건반 빔 밑 빗과 기판 앞 보스 밑 기둥만 출력 파일에 들어 있어 0.2 떨어진 채 나오므로 손으로 떼면 됩니다(부록 A12).")
    a("")
    a("**채움:** 표의 질량은 100 % 채움 기준입니다. 건반·레버·패드 바·가림판은 벽 3줄 + 채움 25~40 %면 충분합니다. 끝 부속 볼(cheek), 스피커 앞판, 스피커 통로 틀은 "
      "속이 꽉 찬 덩어리이므로 벽 3~4줄 + 채움 15~40 %로 뽑습니다(볼 하나에 약 200 g 절약). 보드 받침 기둥, 캡스턴 게이지(T2)·핀 게이지(T3)만 채움 100 %입니다.")
    a("")
    a("**PORON 5T:** 업스톱 패드 설계값은 미세셀 우레탄 6T + 펠트 1T이지만, 구매 목록(i124)은 PORON 5T입니다. 그래서 `stl/print/04`의 패드 바는 "
      "**5T용**(쐐기를 패드 면 법선으로 1.0 두껍게 - 패드 면 위치는 설계와 같음)입니다. 6T를 사면 `stl/print_extra/대안_패드바_PORON6T용`의 6종을 대신 뽑습니다. "
      "조립 모델(3MF·GLB·뷰어)은 설계 6T로 그려져 있습니다.")
    a("")
    # ---------------- optional / alternative / spare prints
    a("## 선택·대안·예비 — `stl/print_extra/` (꼭 뽑지 않아도 됨)")
    a("")
    for folder, rs in by_extra.items():
        a("### %s" % folder.replace("@extra/", ""))
        a("")
        a("| 파일 | 개수 | 크기 (베드 위, mm) | 속 꽉 채움 질량 g | 언제 뽑나 |")
        a("|---|---|---|---|---|")
        for r in rs:
            a("| `%s` | %d | %s | %.1f | %s |" % (os.path.basename(r["file"]), r["qty"], " × ".join("%.1f" % v for v in r["size_mm"]),
                                              r["mass_g_solid_petg"], (r["note"] or "").split(" - ")[0].split(". ")[0]))
        a("")
    # ---------------- plywood
    prow, other = plywood_rows(man)
    if prow:
        pc = L2["plywood_cut_list"]
        a("## 합판 재단 (오꾸메 11.5T, 출력하지 않음)")
        a("")
        n_ply = sum(q for (_, _, q, _, _, _) in prow) + len(other)
        area = sum(q * mb[0] * mb[1] for (_, _, q, mb, _, _) in prow) / 1e6
        a("L2 합판 조각은 %d개, 사각 재단 넓이 %s m²입니다 (L1 %s m²). 판매처 무료 재단은 사각 재단만 해 주므로 아래 크기로 받고, '직접 가공'만 톱·드릴로 합니다"
          "(톱날 3 mm는 판매처 재단에서 빠짐). 구멍·홈·자석 자리는 출력 지그 `stl/print/08_합판지그`(쓰는 법 [`jigs/README.md`](jigs/README.md))를 대고 "
          "가진 전동 드릴로 뚫습니다 — 공구는 새로 사지 않습니다. 치수는 이 모델에서 잰 값이고, 사양 표와 다르면 괄호에 사양 값을 적었습니다."
          % (n_ply, f(area, 3), f(pc["L1_area_m2"], 3)))
        a("")
        # 2026-10-15: CNC shops stock birch 12T, not okoume 11.5 - checked in the model by growing every ply face 0.5 (no new overlaps
        # only in these directions)
        a("**자작 12T로 받을 때 (2026-10-15 모델 확인):** 조각 크기는 도면 그대로 두고, 11.5보다 두꺼운 만큼(12T면 0.5 mm)을 아래 목록의 방향으로 보내 "
          "붙입니다. 모델에서 판마다 한 면씩 0.5 늘려 보면 이 방향일 때만 새로 겹치는 부품이 없어, 다시 자르거나 다시 출력할 부품이 없습니다.")
        a("")
        a("- **스피커 바깥 옆판 2장 → 바깥쪽.** 안쪽 면을 뒤판·윗판·아랫판·앞판·통로 틀에 맞춥니다. 전체 폭 1254 → 1255 (볼 핀 사이는 그대로).")
        a("- **뒤판 3장 (스피커 2, 가운데 1) → 뒤쪽.** 안쪽 면 y331을 지킵니다. 뒷면이 y342.5 → 343.0이 되어 옆판·뚜껑·뒤판 출력물의 뒤 끝이 0.5 안쪽에 남습니다.")
        a("- **스피커 윗판 2장 → 아래쪽 (상자 안).** 윗면을 앞판 윗마개 윗면 z%s에 맞춥니다." % f(body.SPK_ZT))
        a("- **아랫판 3장 (스피커 2, 가운데 1) → 아래쪽.** 윗면 z16.5를 지킵니다 (통로 틀 세움벽·배터리 틀·보드 기둥·이음 기둥·뒤판 출력물 탭이 이 면에 얹힘). "
          "밑면이 옆판·끝벽보다 0.5 아래로 나오고, 뒷바 전체가 고무발 위에서 0.5 높아집니다: 뚜껑 윗면이 건반 윗면보다 0.5 위, 방진 브래킷 핀은 소켓에 "
          "7 대신 6.5 물림 (건반 모듈·케이블과 새로 닿는 곳 없음).")
        a("- **반대로 붙이면 안 됨:** 아랫판을 위로 보내면 위 부품들과 0.5 겹쳐 다시 출력해야 하고, 뒤판을 안으로 보내면 출력 끝벽·허브 선반·스피커 윗·아랫판과 겹칩니다.")
        a("- **나사·자석:** 뒤판 윗모서리 자석 자리는 실제 두께에 맞는 J-b 틈(12.0이면 12.2, 11.7~11.8이면 11.9)으로 팝니다. 자리 중심이 뚜껑 자석보다 "
          "최대 0.25 뒤로 가지만 Ø8 자석이라 괜찮습니다. 고무발 나사 13 mm는 합판 안에서 멈추고, 가운데 아랫판 접시머리 나사 끝은 밑면에서 2.5 대신 3.0 위가 됩니다.")
        a("- **실제 두께:** 가공 업체에 실측값을 받고, 받은 판도 두 곳 이상 잽니다. 11.5보다 두꺼운 만큼만 위 목록의 방향으로 보냅니다 (11.6이면 0.1).")
        a("")
        a("**드릴은 %d번 (2026-10-07, 사용자 '드릴을 써야되는 부분을 최소한으로'; 전엔 약 624번):** 뚜껑 L·R, 가운데 끝벽 L·R, 스피커 안쪽 옆판 L·R은 출력으로 "
          "옮겨(05_본체출력물) 홈·구멍·자석 자리·인서트 구멍이 출력에 있습니다. 합판에 남은 것은 **Ø8 관통 %d개** (뒤판 앰프 뒤 %d — 지그 J-d3, 아랫판 강압·Pi 아래 "
          "%d — 지그 J-d4; 구멍 사이 나무 %s, 전 폭 4 mm 홈과 같은 넓이 이상)와 **뒤판 윗모서리 자석 자리 Ø8 × 3.2 4곳**(11.5 두께 가운데 → 벽 1.75; 판을 붙이기 "
          "전에 **J-b 모서리 새들 + Ø8 트위스트 드릴**, 깊이는 J-e 게이지로 척 멈춤)뿐입니다. 톱질은 바깥 옆판 2장의 경사·턱·홈과 뒤판 창. "
          "아래 표의 '직접 가공'에 조각마다 쓰는 지그를 적었습니다."
          % (len(body.BACK_HOLES) + len(body.BOT_HOLES_BUCK) + len(body.BOT_HOLES_PI) + 4,
             len(body.BACK_HOLES) + len(body.BOT_HOLES_BUCK) + len(body.BOT_HOLES_PI), len(body.BACK_HOLES),
             len(body.BOT_HOLES_BUCK) + len(body.BOT_HOLES_PI), f(body.VENT_WEB, 0)))
        a("")
        a("| 조각 | 개수 | 사각 재단 (mm) | 직접 가공 |")
        a("|---|---|---|---|")
        for (k, name, q, mb, sb, ps) in prow:
            same = all(abs(x - y) < 0.05 for x, y in zip(sorted(mb), sorted(sb)))
            size = "%s × %s" % (f(mb[0]), f(mb[1])) + ("" if same else " (사양 %s × %s)" % (f(sb[0]), f(sb[1])))
            try:
                work = ply_work(k)
            except Exception as ex:                                  # keep the build going; the part source still has the cut text
                work = "(계산 실패: %s)" % ex
            a("| %s `%s` | %d | %s | %s |" % (name, k, q, size, work))
        for p in other:
            b = p["bbox"]
            a("| %s `%s` | 1 | %s | |" % (p["name_ko"], p["id"], " × ".join(f(v) for v in sorted([b[3] - b[0], b[4] - b[1], b[5] - b[2]], reverse=True)[:2])))
        a("")
        feet = body.foot_positions()
        nf = collections.Counter(g for g, _, _ in feet)
        a("**나사 자리 (위 표에 조각마다 적음):** 고무발 나사 %d개 (L49 8호 13 mm — 스피커 아랫판 %d × 2 + 가운데 아랫판 %d, 밑면), 접시머리 나사 %d개 "
          "(L77 8호 13 mm — 가운데 아랫판 윗면: %s), 허브 선반 받침 나사 %d개 (L78 M3 × 12 — 가운데 뒤판 안쪽 면). "
          "나사는 모두 출력물·고무발 구멍을 대고 바로 조입니다(직결피스·태핑 피스)."
          % (len(feet), nf.get("스피커 L", 0), nf.get("가운데 유닛", 0), len(csk_spots()),
             " + ".join("%s %d" % (w, n) for w, n in collections.Counter(w for w, _, _ in csk_spots()).items()),
             sum(1 for k_ in body.CC if k_.startswith("PR-SHELFBRK"))))
        a("")
        ok, uw, uh = nesting_check(prow)
        nest = pc["nesting_400x1200"]
        a("**400 × 1200 한 장 배치** (사양 plywood_cut_list, 톱날 %s): %s 사용 %s × %s mm. 가게에 이 배치(왼쪽 위 기준 x, y)대로 잘라 달라고 합니다. "
          "못 하면 600 × 1200을 그대로 삽니다(+22,520원)." % (f(nest["kerf"]), "모델 크기로 다시 놓아도 들어감," if ok else "**모델 크기로는 이 배치에 들어가지 않음 — 다시 배치할 것,**",
                                                         f(uw, 1), f(uh, 1)))
        a("")
        a("| 조각 | x | y | 폭 × 높이 |")
        a("|---|---|---|---|")
        for (pid, x, y, w, h) in nest["layout_xywh"]:
            a("| `%s` | %s | %s | %s × %s |" % (pid, f(x, 1), f(y, 1), f(w, 1), f(h, 1)))
        a("")
        a("| 부품 | 치수 (mm) | 위치 x / y / z |")
        a("|---|---|---|")
        for p in man["parts"]:
            if p["kind"] != "plywood":
                continue
            b = p["bbox"]
            dims = sorted([round(b[3] - b[0], 2), round(b[4] - b[1], 2), round(b[5] - b[2], 2)], reverse=True)
            a("| %s | %s | x%.1f~%.1f / y%.1f~%.1f / z%.1f~%.1f |" % (p["name_ko"], " × ".join(f(d) for d in dims), b[0], b[3], b[1], b[4], b[2], b[5]))
        a("")
        a("고무발(화성고무 피스고무발 28×5, i039) 고정 나사는 직결피스 8호 **13 mm 이하**(L49의 13 mm 옵션)입니다. 발 5 + 합판 11.5 = 16.5라 25 mm는 상자 안으로 "
          "약 8 mm 뚫고 나옵니다. 13 mm면 발의 머리 자리가 2 mm일 때 끝이 합판 안면보다 1.5 안에 머뭅니다(받은 발의 머리 자리 깊이를 재 보고 확인). "
          "스피커 아랫판은 밀폐 상자 바닥이라 나사 구멍마다 MS 폴리머를 한 방울 넣습니다. 스피커 바깥 발은 사양 x−2 / 1224 대신 x6 / 1216 (나사가 판 끝에서 10.5).")
        a("")
    if not prow:
        # 2026-10-16 (A안): no plywood - the former okoume panels are printed (05 folder)
        a("## 판 (2026-10-16부터 모두 출력, 합판 없음)")
        a("")
        a("사용자 결정(A안, 2026-10-16): 합판 가공비가 비싸 남은 오꾸메 10조각도 PETG로 출력합니다. 모양·두께 %s·자리는 같고, 환기 Ø8 구멍·자석 자리·"
          "나사 안내 구멍(8호 Ø%s · 허브 선반 Ø%s, 끝은 45° 원뿔)이 출력에 있어 **드릴·톱질이 없습니다.** 이음은 모두 MS 폴리머입니다(목공본드는 PETG에 "
          "잘 붙지 않음). 판 출력물은 약 2.0 kg · 49시간(벽·채움 어림, 슬라이서 값이 기준)이라 **PETG가 약 2 kg 더 필요합니다** (건반 액션만 "
          "6.55 kg · 뒷바 약 1.1 kg로 가진 8 kg는 이미 다 씀; 상자·가운데 판은 보이므로 검정)." % (f(body.T, 1), f(body.PILOT_D["foot"], 1), f(body.PILOT_D["pan"], 1)))
        a("")
        a("| 판 | 출력 파일 (05_본체출력물) | 크기 (mm) | 출력 |")
        a("|---|---|---|---|")
        for pid in ["SPKL-PLY-SIDEOUT", "SPKL-PLY-BACK", "SPKL-PLY-TOP", "SPKL-PLY-BOTTOM", "CU-PLY-BOTTOM", "CU-PLY-BACK"]:
            p_ = next((q for q in man["parts"] if q["id"] == pid), None)
            if p_ is None:
                continue
            bb = p_["bbox"]
            dims_ = " × ".join(f(v, 2) for v in sorted([bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]], reverse=True))
            files_ = [os.path.basename(r["file"]) for r in rows if pid in r.get("ids", []) or (pid.startswith("SPKL") and pid.replace("SPKL", "SPKR") in r.get("ids", []))]
            how = ("3토막, 반턱 이음 x%s · x%s (겹침 %s)" % (f(body.SPLIT_X[0], 0), f(body.SPLIT_X[1], 0), f(body.LAP, 0))) if pid.startswith("CU-") else \
                  "L·R 한 쌍, 밀폐 상자 벽 (벽 5줄 + 채움 40 % 이상)"
            a("| %s | %s | %s | %s |" % (p_["name_ko"].replace("스피커 파트 L ", "스피커 ").replace(" (출력)", ""), "<br>".join("`%s`" % x for x in files_), dims_, how))
        a("")
        a("**가운데 아랫판·뒤판 잇기:** 토막 셋을 반턱끼리 겹쳐 MS 폴리머로 붙이고, 앞·뒤(뒤판은 위·아래) 모서리를 곧은 자에 맞춰 굳을 때까지 "
          "마스킹테이프로 눌러 둡니다. 다 붙인 길이가 아랫판 679, 뒤판 702인지 잽니다. 아랫판 이음은 뚜껑 이음 기둥(x501~511, 711~721) 곁, "
          "뒤판 왼쪽 이음은 창 아래 띠(뒤판 출력물이 위에 붙음), 오른쪽 이음은 이음 레일 2의 끝면이 덮습니다.")
        a("")
    # ---------------- deviations from the spec
    dev = deviations(man)
    if dev:
        a("## 사양(body_L2.json)과 다르게 만든 곳 (작은 고침)")
        a("")
        a("사양 수치가 실제 모양에서 맞지 않는 곳만 가장 작게 고쳤습니다. 부품 메모(manifest `note`)에도 같은 내용이 있습니다.")
        a("")
        for (names, txt) in dev:
            a("- **%s** — %s" % (names, txt))
        a("")
        a("그 밖에 사양 수치를 조금 바꾸거나 채운 곳 (부품 메모에는 '추정'으로 적힘):")
        a("")
        for (names, txt) in extra_deviations(man):
            a("- **%s** — %s" % (names, txt))
        a("")
    # ---------------- assumed values
    est = grouped_notes(man, "추정")
    if est:
        a("## 문서에 치수가 없어 정한 값 (추정)")
        a("")
        for (name, txt, cnt, nvar) in est:
            more = ""
            if nvar > 1:
                more = " (같은 부품 %d개, 자리만 다름 — 첫 번째 값)" % cnt
            a("- **%s** — %s%s" % (name, txt, more))
        a("")
    a("## 모델에 넣지 않은 것")
    a("")
    a("사용자 요청대로 만능기판은 사각형만 두고, 그 위에는 부피 있는 부품만 넣었습니다. 아래 항목은 크기가 작거나 위치가 조립 때 정해지는 것이라 모델에 없습니다. 구매는 BOM(`hardware/bom/final-bom`)을 따릅니다.")
    a("")
    a("| 무엇 | 개수 | 비고 |")
    a("|---|---|---|")
    for r_ in NOT_MODELLED:
        a("| %s | %s | %s |" % r_)
    a("")
    a("## 구매 목록에 없는 것 (따로 사거나 확인)")
    a("")
    a("10/1 구매 목록 v4(`archive/hardware/bom/toccata-purchase-list-v4.xlsx`)에 L69~L79·C22·C24·C25가 들어갔습니다. '구매 목록 v4 …' 줄은 CAD를 그 상품에 맞춘 것이고 "
      "(L73 Norelem 07653-04 나사산 인서트는 10/7부터 안 씀 — 출력 안쪽 옆판에 사용자 세트의 M4 열 인서트), 나머지 줄은 v4에서 다시 확인할 것입니다. 접시머리 8호 13 mm(L77, 최종 재료 i219)와 허브 선반 "
      "받침 나사 M3 × 12 트러스 태핑(L78, i220)도 v4에 들어가 이제 삽니다 — 위 '모델에 넣지 않은 것' 표.")
    a("")
    for t_ in BUY_GAPS:
        a("- " + {"USB_CABLES": lambda: usb_cable_line(man), "TOUCH_PETG": lambda: touch_petg_line(man), "QUICKSERT": quickserts_line,
                  "UPSTREAM": upstream_line, "PIPOWER": pipower_line}.get(t_, lambda: t_)())
    a("")
    a("## L2에서 더 이상 사지 않는 것")
    a("")
    for t_ in DROPPED:
        a("- " + t_)
    a("")
    a("## 조립 순서 (L2, CAD로 확인한 것)")
    a("")
    a("건반 액션:")
    a("")
    for t_ in KEY_ORDER_NOTES:
        a("- " + t_)
    a("")
    a("뒷바 L2:")
    a("")
    for i, t_ in enumerate(assembly_order(fg), 1):
        a("%d. %s" % (i, t_))
    a("")
    a("## 분해·점검 (어느 것을 들어야 하나)")
    a("")
    a("| 하려는 일 | 여는 것 | 방법 |")
    a("|---|---|---|")
    for r_ in SERVICE:
        a("| %s | %s | %s |" % r_)
    a("")
    ks = L2["key_storage"]
    a("## 예비 건반 칸 (R29) — 본체에서 뺌 (사용자 승인 2026-10-02)")
    a("")
    a("%s. 대안:" % ks["why"])
    a("")
    a("- (a) 따로 출력하는 예비 부품 상자 약 210 × 180 × 65 (256 판에 반씩 2번), 모듈 가방과 같이 들고 다님")
    a("- (b) 가운데 뒤에 붙였다 떼는 보관 칸 (y%s~약 510, 같은 나비나사 결합) — 붙였을 때만 깊이 +170" % f(body.YB))
    a("")
    a("사용자가 보관 칸을 빼기로 했습니다(10/2). 대안 (a)·(b)는 이 모델에 없고, 필요해지면 만듭니다.")
    a("")
    L += touch_section(man)
    a("## 설계 모델에서 CAD로 옮기며 고친 점")
    a("")
    a("| 번호 | 어디 | 무엇을 왜 |")
    a("|---|---|---|")
    for (i, w, t) in ADJUSTMENTS:
        a("| %s | %s | %s |" % (i, w, t))
    a("")
    a("## 조립 그룹")
    a("")
    g = collections.Counter()
    k = collections.defaultdict(collections.Counter)
    for p in man["parts"]:
        g[p["group"]] += 1
        k[p["group"]][p["kind"]] += 1
    a("| 그룹 | 부품 수 | 종류 |")
    a("|---|---|---|")
    for gg, n in g.items():
        a("| %s | %d | %s |" % (gg, n, ", ".join("%s %d" % (kk, v) for kk, v in k[gg].items())))
    a("")
    a("모두 %d개 (조립 파일에 들어가는 것 %d개; 댐퍼 페달 %d개(바닥)와 접은 터치스크린 %d개(별도 보기 그룹)는 한 파일 조립·3MF·GLB에서 뺌)."
      % (len(man["parts"]), sum(1 for p in man["parts"] if p.get("note") not in ("offdesk", "altview")),
         sum(1 for p in man["parts"] if p.get("note") == "offdesk"), sum(1 for p in man["parts"] if p.get("note") == "altview")))
    a("")
    open(os.path.join(OUT, "README.md"), "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
