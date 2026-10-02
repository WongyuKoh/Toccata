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
    return [(parts[i], parts[i + 1].strip(" ;")) for i in range(1, len(parts) - 1, 2)]


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
    return ("구매 목록 v4 L72·L73·L74 (스피커 ↔ 가운데 결합): 손잡이볼트 M4×20 (L72, 머리 Ø8 × 6) 4 — 슬리브 끝에서 이음면까지 %s라 인서트에 %s 물림 "
            "(M4×22면 %s = 인서트 길이, 끝이 구멍 바닥 %s 위; %s 이상은 끝이 구멍 바닥에 닿고 더 길면 밑 밀폐 판을 누름 → **최대 M4×22**) + 실리콘 튜브 슬리브 "
            "(L74, 13 mm로 4개) + 나사산 인서트 **L73 = Norelem 07653-04** (셀프 태핑, 스틸, 컷팅 보어형, M4, 겉 Ø%s, 피치 0.8, 길이 %s, 최소 구멍 깊이 %s) 4. "
            "구멍은 **Ø%s × %s** (막힘, 깊이 멈춤: 드릴에 테이프 %s mm) — 오꾸메 자투리에 Ø%s로 먼저 시험, 헐거우면 Ø5.5 (나무는 눌림). "
            "안쪽 옆판(오꾸메 %s) 밑에 지름 부분 %s, 드릴 끝 밑 %s 이상 남아 상자가 밀폐됨. 인서트는 면까지만 (밑 %s mm는 나사 끝 자리)"
            % (f(reach, 0), f(B.TS_LEN - reach, 0), f(22.0 - reach, 0), f(B.QS_HOLE[1] - (22.0 - reach), 0), "M4×%s" % f(reach + B.QS_HOLE[1], 0),
               f(B.INS[0], 1), f(B.INS[2], 0), f(B.QS_MIN_DEPTH, 0), f(B.QS_HOLE[0], 1), f(B.QS_HOLE[1], 0), f(B.QS_HOLE[1], 0), f(B.QS_HOLE[0], 1),
               f(B.T, 1), f(B.T - B.QS_HOLE[1], 1), f(B.QS_MIN_PLY, 1), f(B.QS_HOLE[1] - B.INS[2], 0)))


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
    h, d = E_.C24_HEAD, E_.HUB_DC
    return ("구매 목록 v4 C24 (Coms BT663, USB-C **옆으로 꺾임** 20 cm, A 쪽을 잘라 빨강·검정을 강압 출력에): 꺾인 머리(사진 비례 추정 %s × %s × %s)가 "
            "사양 지킴 자리 Z-PI-PWR 14 × 13 × 9 (x546~560 y249~262 z22~31) 안에 들어감 — 선이 −x(강압 쪽)로 나오게 꽂음 (USB-C는 뒤집으면 +x). "
            "받으면 머리가 x 방향 14보다 길지 않은지 잼 (선이 −x로 나가므로 머리가 길면 −x 쪽으로 늘어남 - x540~546도 비어 있어 18 mm 머리까지 들어감). 허브 DC는 업스트림 B와 같은 −x 끝면(잭 y%s z%s)에 "
            "**ㄱ자 DC 플러그** (머리 12 × 12 × 10, 선이 위로)로 모델. 딸린 어댑터 선의 **곧은 플러그**도 잭 면에서 몰드·부트 끝까지 **%s mm 이하**이고 선을 "
            "바로 위로(R%s) 꺾을 수 있으면 들어감 (더 길면 IH190 젠더에 닿음 — check_electronics.py). 길면 같은 규격 ㄱ자 DC 플러그 선을 사는데, 그때 허브 잭의 "
            "**배럴 바깥/안 지름(5.5 × 2.1 / 5.5 × 2.5 / 3.5 × 1.35)과 배럴 길이**를 재서 맞춤"
            % (f(h[1] - h[0], 0), f(h[3] - h[2], 0), f(h[5] - h[4], 0), f(E_.HUB_DC_YZ[0], 0), f(E_.HUB_DC_YZ[1], 1), f(E_.HUB_DC_STRAIGHT_MAX, 0),
               f(E_.HUB_DC_STRAIGHT[1], 0)))


def extra_deviations(man):
    """spec adjustments the implementers wrote under '추정' in the notes (not tagged '사양과 다름'), with the model numbers."""
    B = body
    E_ = _elec()
    sz = {os.path.basename(r["file"]).split("__")[0]: r["size_mm"] for r in man["print"]}
    xt = " / ".join("%s %s" % (k[-1], " × ".join(f(v, 1) for v in sz[k])) for k in ("XT30집게_L", "XT30집게_R") if k in sz)
    bk = B.BOT_SLOTS_BUCK
    return [
        ("방진 브래킷 BRK2", "그로밋이 끼는 세움 다리는 z%s~%s (사양은 판 z8~14만 적음): 6 mm 판에는 Ø6 그로밋(중심 z12, 자리 Ø6.5)이 들어가지 않음. "
         "핀을 받치는 판(팔)은 z8~14 그대로" % (f(B.BRK2_Z0), f(B.BRK2_LEG_TOP))),
        ("고무 슬리브", "끝벽만 지나감 (길이 %s, 가운데 쪽으로 %s 나옴) — 사양처럼 3 mm 틈까지 건너면 스피커를 들 때 아래 EVA 띠가 걸림. EVA 띠 구멍 Ø10은 "
         "나사가 실제로 띠를 지나는 곳에만" % (f(B.CU_IX[0] + B.SLV[2] - B.CU_X[0], 1), f(B.SLV[2], 1))),
        ("가운데 아랫판", "강압 아래 흡기 홈 x%s~%s (사양 x482~534): 강압 받침 기둥 Ø7 자리를 피함. 이음 기둥 자리(x500~512, 710~722)는 앞 모서리 R3 없음"
         % (f(bk[0][0]), f(bk[-1][0] + 4))),
        ("뒤판 출력물", "루버 x%s~%s (사양 ~536): 옆 테 2 mm를 남김" % (f(B.BP_LOUV_X[0]), f(B.BP_LOUV_X[1]))),
        ("보드 받침", "사양 STANDOFFS(90 × 60 받침 판) 대신 낱개 기둥 14개 (보드에 먼저 나사, 기둥 밑을 아랫판에 MS 폴리머) — 흡기 홈을 막지 않음. "
         "앰프 2 mm 받침 4개는 허브 선반과 한 몸"),
        ("XT30 집게", "사양 24 × 14 × 10보다 큼 (%s, 베드 위) — 끝벽 Ø14 구멍 둘레에 붙일 면이 필요" % xt),
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
        ("허브 선반 받침 나사", "8호 13 mm 대신 Ø3 × 12~13 둥근머리 목재 나사 (머리 Ø6 이하) — 사양 받침 10 × 8에는 8호(Ø4.2, 머리 Ø8)가 들어가지 않음. "
         "머리 자리 눈물방울 꼭지를 받침 윗면 0.8 아래에서 자름. 나사 축 z%s의 머리(아래 끝 z%s)가 선반 윗면 z%s보다 낮아, 받침 앞 선반 윗면에 머리·드라이버 "
         "길 홈 %s × %s (선반 앞끝 y%s → 받침 y%s, 바닥 %s 남음)"
         % (f(B.SHELF_SCREW_Z, 0), f(B.SHELF_SCREW_Z - 3.0, 1), f(B.CC["PR-HUBSHELF"][5], 1), f(B.SHELF_GROOVE[0], 0), f(B.SHELF_GROOVE[1], 1),
            f(B.CC["PR-HUBSHELF"][2], 0), f(B.CC["PR-SHELFBRK-1"][2], 0), f(B.CC["PR-HUBSHELF"][5] - B.CC["PR-HUBSHELF"][4] - B.SHELF_GROOVE[1], 1))),
        ("보드 받침 기둥 (5 mm)", "나사 구멍 깊이 4.5 → 4.0 (바닥 1.0), 나사 길이 M3×5 (Pi M2.5×6) — 6 mm 이상은 바닥을 뚫고 붙인 기둥을 밀어 올림"),
        ("뒤판 출력물 바닥 탭", "왼쪽 나사 (%s, 325) → (%s, %s) (가운데 아랫판 뒤 모서리 y%s에서 %s), 탭을 y%s까지 앞으로. 오른쪽 나사 (463, 325) → (%s, %s): "
         "J501 받침(같은 출력물, z30~36.4)이 오른쪽 탭 전체를 덮어 머리 위로 9.5만 비어 드라이버가 닿지 않았음 → 탭에서 앞으로 낸 혀 x%s~%s y%s~%s에 나사를 둠 "
         "(드라이버 Ø6 길이 받침·J501 기판 앞 1.0, 퓨즈 받침과 6.5; 받침에 구멍을 뚫으면 받침 앞끝이 2 mm만 남고 붙인 J501 기판 밑이 되어 뺄 수 없음). "
         "J501 받침 밑 삼각 받침 2개 → 바깥 판에서 곧게 오른 받침벽 2개 (x%s, 탭에 이음; 출력 때 공중에 뜨지 않음)"
         % (f(B.BP_TABS[0][2], 0), f(B.BP_TABS[0][2], 0), f(B.BP_TABS[0][3], 0), f(B.YBI, 0), f(B.YBI - B.BP_TABS[0][3], 0), f(B.BP_TAB_Y0, 0), f(B.BP_TABS[1][2], 0), f(B.BP_TABS[1][3], 1),
            f(B.BP_TONGUE[0], 1), f(B.BP_TONGUE[1], 1), f(B.BP_TONGUE[2], 0), f(B.BP_TAB_Y0, 0),
            "/".join("%s~%s" % (f(g, 0), f(g + 2, 0)) for g in B.BP_WEBS))),
        ("합판 환기 홈", "뚜껑 L 홈 6개 y%s~%s, 뒤판 앰프 뒤 홈 8개 x%s~%s — 간격 6.5 → 8 (홈 사이 나무 2.5 → 4)"
         % (f(B.LIDL_SLOTS[0][2], 0), f(B.LIDL_SLOTS[-1][2] + 4, 0), f(B.BACK_SLOTS[0][0], 0), f(B.BACK_SLOTS[-1][0] + 4, 0))),
        ("전자부 단자 자리 (가정)", "강압 입력 −x 끝(y306)·출력 앞면(x529.5); 앰프 전원 y313·스피커 L y318(−x 끝), 스피커 R y293(+x 끝); 허브는 W1 10/1 "
         "제품 사진대로 업스트림 USB 3.0 B 포트(y%s)와 DC 잭(y%s, ㄱ자 플러그)이 같은 −x 끝면 (사양: 업스트림 −x · DC +x). 끝면 안 자리는 받은 허브로 확인"
         % (f(E_.C25_B_PORT[0], 0), f(E_.HUB_DC_YZ[0], 0))),
        ("스피커 꼬리선", "스피커 밖 %s mm (꼬리 150 중): 여유 약 %s mm를 끝벽 Ø14 터널 안에 %s바퀴 느슨하게 감아 둠 — 스피커를 10 mm 들고 15 mm 바깥으로 "
         "밀어도 XT30U-F가 집게에 남고, 그다음 F를 터널로 빼냄 (check_body.py가 확인). 두 가닥을 Ø2 한 줄로 표시"
         % (f(_pig_out(man), 0), f(B.PIG_SLACK_MM, 0), f(__import__("electronics").PIG_COIL[1], 1))),
        ("홀 센서 높이 (D14)", "D14 거리를 사양의 z8이 아니라 홀 소자 높이 z%s (포켓 바닥 12.19 + 0.75)까지 잼 → 사양 %s / %s보다 1~2 mm 짧음 (≥100은 그대로)"
         % (f(B.SENSOR_YZ[1], 1), f(L2["speakers"]["d14"]["to_sensor_row_mm"], 1), f(L2["speakers"]["d14"]["nearest_steel_point_mm"], 1))),
        ("XT30U-M 수 꼬리", "사양 C-XT30 상자보다 0.1 나옴 (집게 홈 + 밖에 보이는 8.1)"),
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


def ply_work(piece):
    """what to cut by hand on each cut-list piece (u = back from the front edge, v = up from the bottom edge, x from the left end)."""
    B = body
    un, vn = B.DUCT_Y[1] - B.Y0, B.DUCT_Z[1] - B.ZB
    if piece == "PLY-POD-SIDE":
        return ("사각으로 받은 뒤 직접 자름 (앞 모서리에서 뒤로 u, 아래 모서리에서 위로 v): ① 앞 아래 통로 홈 %s × %s 따냄 "
                "② 앞 모서리는 v%s까지 두고, 거기서 수평으로 %s 들어간 점 (u%s, v%s)부터 윗변 u%s까지 %s° 사선 (사선 길이 %s, 윗변에 남는 길이 %s). "
                "안쪽 옆판만: M4 나사산 인서트(L73) 구멍 Ø%s × %s (가운데 쪽 면에서, 막힘 — 깊이 멈춤으로 %s까지만: 판 %s 중 지름 부분 밑 %s, 드릴 끝 밑 %s 이상 남아야 "
                "밀폐) L %s / R %s, 스피커선 구멍 Ø6 관통 L %s / R %s"
                % (f(un, 1), f(vn, 1), f(B.Z_FB - B.ZB), f(B.SL_A[0] - B.Y0), f(B.SL_A[0] - B.Y0), f(B.Z_FB - B.ZB), f(B.SL_B[0] - B.Y0),
                   f(B.ANGLE, 1), f(B.SL_LEN), f(B.YB - B.SL_B[0]), f(B.QS_HOLE[0], 1), f(B.QS_HOLE[1], 0), f(B.QS_HOLE[1], 0), f(B.T, 1),
                   f(B.T - B.QS_HOLE[1], 1), f(B.QS_MIN_PLY, 1),
                   "·".join(_uv(p) for p in B.TS_YZ["L"]), "·".join(_uv(p) for p in B.TS_YZ["R"]), _uv(B.WIRE_YZ["L"]), _uv(B.WIRE_YZ["R"])))
    if piece == "PLY-POD-BACK":
        return "없음 (옆판 사이). 안쪽에 흡음솜을 두되 자석 뒤 폴 벤트 축 방향 10 mm는 비움 (W1)"
    if piece == "PLY-POD-TOP":
        return "없음. 앞 모서리(y%s)는 출력 앞판 윗마개에 맞댐" % f(B.TOP_Y0)
    if piece == "PLY-POD-BOTTOM":
        fl = [xy for g, xy, _ in B.foot_positions() if g == "스피커 L"]
        xs = sorted(set(round(x - B.SX0, 1) for x, y in fl))          # from the outer (-x) end of the L bottom; R is the mirror
        ys = sorted(set(round(y - B.RISER[0], 1) for x, y in fl))
        return ("없음. 고무발 나사 자리 4 (8호 13 mm 이하): 바깥 끝에서 %s, 앞 모서리에서 %s (발 Ø28이 옆판 밑까지 나옴; 사양 2.5는 나사가 끝면에 "
                "너무 가까워 옮김). 밀폐 상자 바닥이라 구멍에 MS 폴리머 한 방울"
                % ("·".join(f(v, 1) for v in xs), "·".join(f(v, 1) for v in ys)))
    if piece == "PLY-CU-END":
        mz = B.MAG_END["L"][1] - B.Y0
        pkz = {s_: (B.XT30_POCKET[s_][4] + B.XT30_POCKET[s_][5]) / 2.0 for s_ in "LR"}
        return ("ㄴ자: 앞 아래 통로 홈 %s × %s 따냄. 구멍 관통: XT30 선 Ø%s L %s / R %s (L은 XT30 집게 홈과 같은 축, R은 홈 축보다 %s 아래 — "
                "스피커 옆판 선 구멍보다 L %s · R %s 위), "
                "고무 슬리브 Ø8 ×2 L %s / R %s; 윗모서리 자석 자리 Ø8 × 3.2 (u%s, 두께 가운데 — 두 판을 붙이기 전에 포스트너 비트로)"
                % (f(un, 1), f(vn, 1), f(B.END_HOLE_D, 0), _uv(B.END_HOLE_YZ["L"]), _uv(B.END_HOLE_YZ["R"]), f(pkz["R"] - B.END_HOLE_YZ["R"][1], 1),
                   f(B.END_HOLE_YZ["L"][1] - B.WIRE_YZ["L"][1], 1), f(B.END_HOLE_YZ["R"][1] - B.WIRE_YZ["R"][1], 1),
                   "·".join(_uv(p) for p in B.TS_YZ["L"]), "·".join(_uv(p) for p in B.TS_YZ["R"]), f(mz, 1)))
    if piece == "PLY-CU-BACK":
        x0 = B.CU_X[0]
        s0, s1 = B.BACK_SLOTS[0], B.BACK_SLOTS[-1]
        return ("뒤판 출력물 창: 왼쪽 끝에서 %s~%s (폭 %s), 아래 모서리에서 %s 위부터 윗변까지 (위가 열림) — 톱으로 두 번 세로 자르고 가로로 따냄; "
                "앰프 뒤 환기 홈 %d개 4 × %s (왼쪽 끝에서 %s~%s, 아래에서 %s~%s); 윗모서리 자석 자리 Ø8 × 3.2 4곳 (왼쪽 끝에서 %s)"
                % (f(B.BP_X[0] - x0), f(B.BP_X[1] - x0), f(B.BP_X[1] - B.BP_X[0]), f(B.Z_BOT - B.ZB), len(B.BACK_SLOTS), f(s0[2] - s0[1]),
                   f(s0[0] - x0), f(s1[0] + 4.0 - x0), f(s0[1] - B.ZB), f(s0[2] - B.ZB),
                   "·".join(f(x - x0) for s in "LR" for x in B.MAG_BACK_X[s])))
    if piece == "PLY-CU-BOTTOM":
        x0 = B.CU_IX[0]
        bk, pi = B.BOT_SLOTS_BUCK, B.BOT_SLOTS_PI
        fl = L2["feet"]["positions_xy"]["centre"]
        return ("앞 윗모서리 R3 (이음 기둥 자리 왼쪽 끝에서 %s는 빼고); 흡기 홈 4 × 34: 강압 아래 %d개 (왼쪽 끝에서 %s~%s, 앞 모서리에서 %s~%s), "
                "Pi 아래 %d개 (%s~%s, %s~%s); 고무발 나사 자리 6 (8호 13 mm): 왼쪽 끝에서 %s, 앞 모서리에서 %s"
                % (" · ".join("%s~%s" % (f(a - x0), f(b - x0)) for a, b in B.FILLET_SKIP), len(bk), f(bk[0][0] - x0), f(bk[-1][0] + 4 - x0),
                   f(bk[0][1] - B.RISER[0]), f(bk[0][2] - B.RISER[0]), len(pi), f(pi[0][0] - x0), f(pi[-1][0] + 4 - x0),
                   f(pi[0][1] - B.RISER[0]), f(pi[0][2] - B.RISER[0]),
                   "·".join(f(v) for v in sorted(set(x - x0 for x, y in fl))), "·".join(f(v) for v in sorted(set(y - B.RISER[0] for x, y in fl)))))
    if piece in ("PLY-CU-LID-L", "PLY-CU-LID-R"):
        s = piece[-1]
        x0 = B.LIDS["LID-" + s][0]
        if s == "L":
            sl = B.LIDL_SLOTS
            slots = "배기 홈 %d개 30 × 4 (왼쪽 끝에서 %s~%s, 앞 모서리에서 %s~%s)" % (len(sl), f(sl[0][0] - x0), f(sl[0][1] - x0),
                                                                          f(sl[0][2] - B.Y0), f(sl[-1][2] + 4 - B.Y0))
        else:
            sl = B.LIDR_SLOTS
            slots = "배기 홈 %d개 4 × 40 (왼쪽 끝에서 %s~%s, 앞 모서리에서 %s~%s)" % (len(sl), f(sl[0][0] - x0), f(sl[-1][0] + 4 - x0),
                                                                          f(sl[0][1] - B.Y0), f(sl[0][2] - B.Y0))
        mags = [(x, (B.YBI + B.YB) / 2.0) for x in B.MAG_BACK_X[s]] + [B.MAG_END[s]]
        return ("앞 윗모서리 1×45° 모따기 (건반과 사이의 틈이 그림자 선으로 보이게); %s; 밑면 자석 자리 Ø8 × 3.2 3곳 (왼쪽 끝·앞 모서리에서 %s)"
                % (slots, " · ".join("%s/%s" % (f(x - x0), f(y - B.Y0)) for x, y in mags)))
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
    ("Ø3 × 12~13 둥근머리 목재 나사 (머리 Ø6 이하)", "2", "허브 선반 받침 2개를 뒤판에 (받침 10 × 8에 8호가 들어가지 않음). 구멍 Ø3.4·머리 자리는 모델에 있음. 구매 목록에 없음"),
    ("스텐 직결피스 8호 13 mm 접시머리", "6", "뒤판 출력물 바닥 탭 2 + 보조배터리 받침 4. 구멍(접시 자리)은 모델에 있음. 구매 목록에 없음"),
    ("스텐 직결피스 8호 19 mm (L49)", "8", "그릴 4 × 2 (W1: 떨리지 않게 4개 모두). 25 mm는 앞판 아래 파일럿 끝 2.15 밑 밀폐면을 뚫음 — 19 mm 이하"),
    ("M4×12 유두 렌치볼트 (L70)", "8", "스피커 유닛을 출력 앞판의 L69 인서트(모델에 있음)에. 플랜지 4 + 가스켓 3을 지나 5 들어가 인서트 4를 지나 1 더, "
     "끝은 구멍 Ø5.6 × 6.5 바닥 1.5 위. 인서트는 면까지만 넣고 나사는 M4×12 이하 — 아래 구멍 밑 밀폐면이 2.78"),
    ("보드 나사: M2.5×6 자가 탭 (Pi 5), M3×5 자가 탭 (강압 4·J702 2·PED 2), M3×6 자가 탭 (앰프 4)", "4 / 8 / 4",
     "받침 기둥 구멍은 Pi Ø2.2 × 5, 나머지 × 4 (바닥 1.0) — 더 긴 나사는 바닥을 뚫고 붙인 기둥을 밀어 올림. 앰프는 받침 + 선반 관통"),
    ("AUX 3.5 mm 선 2가닥 W701/W702 (볼 헤드폰 잭 ↔ 동글·J702), 보조배터리 ㄱ자 C-C 선(선택), 페달 선", "—",
     "경로는 조립 때 정해짐. 플러그 자리(Z-J702-PLUG·Z-DONGLE-PLUG·Z-BANK-PLUG)가 비어 있는 것은 check_electronics.py가 확인. "
     "모듈 USB 선, 전원선(PD 입력·퓨즈·20 V·5.1 V), 스피커선, 스피커 꼬리선, XT30, 리본, EXT 선, JST-XH는 모델에 있음"),
    ("흡음솜(폴리에스터), 부싱 천 0.5T (노치·핀 홈·탭 옆), 종이 펀칭, PET 심, MS 폴리머·목공본드", "—",
     "두께가 출력 치수에 이미 들어 있음(노치 R2.55 → 천 뒤 R2.05). 흡음솜 조건은 아래 'W1 음향 조건'"),
]

BUY_GAPS = [
    "M3×16 버튼헤드 ISO 7380 볼트 4개 + M4 와셔 (방진 브래킷 BRK2): M3×10은 볼 속 너트에 닿지 않음 (L1 그대로)",
    "직결피스 8호 13 mm 접시머리 6개 (뒤판 출력물 바닥 탭 2, 보조배터리 받침 4): L49는 둥근머리",
    "QUICKSERT",
    "Ø3 × 12~13 둥근머리 목재 나사 2개 (머리 Ø6 이하): 허브 선반 받침 → 뒤판",
    "구매 목록 v4에 있음 — L69 M4 열압입 인서트 (ShenzenAV M4x4x6, 바깥 Ø6 × 4) 8 + 예비 2와 L70 M4×12 8 + 예비 2: 스피커 유닛을 출력 앞판에 "
    "(L1의 직결피스 8호 16 mm 대신). 모델 인서트도 Ø6 × 4 (구멍 Ø5.6 × 6.5 그대로, 지름 0.4 물림)",
    "구매 목록 v4에 있음 — L71 M3 열압입 인서트 (ShenzenAV M3x4x4.5, 바깥 Ø4.5 × 높이 4) 6개 = 화면 뚜껑 이음 레일 4 + 예비 2. 모델 인서트 Ø4.5 × 4 "
    "(구멍 Ø4 × 4.5 그대로, 지름 0.5 물림; 길이 4 = 자리파기 계산 값 그대로). M3×10 4개는 기존 줄",
    "터치스크린 3판 부품은 구매 목록 v4에 있음 (135 화면 Waveshare 7-DSI-TOUCH-C, 49 GUOCONN 22P 0.5 mm 300 mm B형 + 50 A형 보험, 51~54 실리콘 점퍼 "
    "F/F·M/M 빨강·검정 20 cm, 75 M3×20 × 4, 76 M2.5×6 × 4) — 모델과 개수가 같음. 글만 고칠 것: 49줄 '경로 약 271 mm(여유 29)' → 모델 254 / W1 계산 256 "
    "(여유 약 44); 62줄 M3×10 설명의 'R31 CU 뚜껑 앞 모서리 2곳'은 L2에서 화면 뚜껑 4개(레일 인서트)",
    "캡톤테이프(26줄)를 화면 받침 안 리본 누름 패드 자리(xr26.75~39.45 u8~16)에도 씀 (사양 C-7)",
    "TOUCH_PETG",
    "열수축튜브: Waveshare MX1.25→2.54 3핀 선이 120.54 mm보다 짧으면 3핀 이음이 경첩 고리 안에 오므로 감쌈 (사양 G-4, 22 × 6 구멍 통과)",
    "USB_CABLES",
    "ㄱ자 USB-C to C 케이블 0.3 m (보조배터리 → 뒤판 케이블 통과 Ø12 → PD 입력): 사양 bom_changes +2,060원",
    "UPSTREAM",
    "PIPOWER",
    "흡음솜 (폴리에스터): 스피커 상자마다 약 35 g을 상자 전체에 느슨하게 (W1). 기존 줄 양으로 되는지 확인",
    "보조배터리 고정 끈 (벨크로 20 mm): 받침에 끈 구멍만 있음",
    "센서 바 나사는 버튼헤드(머리 1.65)로: 캡볼트면 눌린 C·A0·C8 건반 밑과 0.48",
]

DROPPED = [
    "토글 래치 매미고리 L64 × 2 (−4,800원): 도브테일 블록과 함께 없어짐",
    "오꾸메 합판 600 × 1200 (가운데 유닛용, −22,520원): 모든 판이 400 × 1200 한 장에 들어감. 가게가 아래 배치대로 자르지 못하면 600 × 1200을 그대로 삼",
    "직결피스 8호 16 mm (스피커 유닛 4 × 2): M4 인서트 + M4×12로 바뀜. 8호 13 mm 둥근머리는 L1 46개 → L2 14개",
    "L1 출력물: CU 트레이, CU 뚜껑 v2, 모서리 받침 12, 예비 건반 칸막이, 작은 부품 상자(+뚜껑), 도브테일 블록 4, XT30 받침 2, L1 브래킷 2, I/O 판 "
    "→ PETG 양은 대략 같음 (사양: L2 뒷바 출력물 약 1.1 kg, 모자라면 1 kg 스풀 +16,150원)",
    "R31 공식 Touch Display 2와 그 받침(2판): 사용자가 Waveshare 7-DSI-TOUCH-C로 바꿈 (2026-10-01). 3판 부품은 아래 '터치스크린 3판' 구매 줄",
    "R31 2판의 FIT0997 22→15핀 리본: 3판은 22핀 ↔ 22핀 GUOCONN FFC (구매 목록 v4 49·50줄)",
    "사양 bom_net_krw: %s원 (위 추가분 포함)" % format(L2["bom_net_krw"], ",").replace("-", "−"),
]

KEY_ORDER_NOTES = [
    "건반 모듈은 서로 도브테일(뿌리 6 → 끝 9, 깊이 4, 암은 밑이 열림)로 위에서 내려 끼웁니다. 뒤 꼬리는 높이 14라 빼려면 약 14 mm 들어야 합니다. "
    "모듈은 도브테일 때문에 위로만 빠지므로 앞으로 밀지 않습니다.",
    "제어 기판은 모듈을 뒤집어 바닥 구멍으로 밑에서 넣고 M3×6 2개로 매단 보스에 조입니다(바닥 EVA는 이 구멍 자리를 오려 냄).",
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
    return [
        "**고무발** — 스피커 아랫판마다 4개, 가운데 아랫판 6개 (화성고무 28×5, 8호 **13 mm 이하**; 모두 통로 뒤 y≥248, 스피커 바깥 발은 사양 x−2/1224에서 "
        "x6/1216으로 옮김). 스피커 아랫판은 밀폐 상자 바닥이므로 나사 구멍마다 MS 폴리머 한 방울 (16 mm 이상은 상자 안으로 뚫림).",
        "**스피커 상자 (책상 밖에서)** — 옆판 2 + 아랫판 + 뒤판 + 윗판을 목공본드로 잇고, 출력 통로 틀을 옆판 사이 앞에 넣어 세움벽 밑을 아랫판 앞 모서리"
        "(y241)에 붙임. 출력 앞판(%s°)을 앞벽·턱 위에 MS 폴리머로 붙이고 둘레를 밀봉한 뒤 새는 곳이 없는지 확인. 안쪽 옆판에 L73 나사산 인서트 2개 (Norelem 07653-04 M4, 겉 6.5 × 길이 6, "
        "구멍 Ø5.8 × 8 막힘 — 밑 오꾸메 1.5 이상, 옆판 면까지만; 상자를 붙이기 전에 판에서 뚫음), 앞판 유닛 자리에 L69 인서트 4개 (인두, 면까지), "
        "통로 지붕 밑(z27)에 핀 소켓 블록 (%s)과 케이블 집게 3개, 바깥 옆판 홈에 통로 옆 마개. 스피커 꼬리선(XT30U-F 150)을 안쪽 옆판 Ø6 구멍으로 약 %s mm "
        "빼고 본드로 밀봉. Ø94 구멍으로 흡음솜을 상자 전체에 느슨하게 넣고(유닛 뒤 10 mm·폴 벤트 축 10 mm는 비움), 유닛(가스켓 3T + M4×12 × 4 → 앞판 "
        "인서트; 더 긴 나사 금지), 그릴(8호 19 mm × 4; 25 mm 금지)." % (f(B.ANGLE, 0), pin, f(_PIG_OUT[0], 0)),
        "**가운데 유닛** — 아랫판 + 끝벽 2 + 뒤판을 목공본드로 (끝벽 Ø8 구멍에 고무 슬리브). 뒤판 창에 뒤판 출력물을 끼우고 바닥 탭 2개를 접시 8호 13 mm로: "
        "왼쪽 (%s, %s), 오른쪽은 J501 받침 앞으로 나온 혀의 (%s, %s) — J501 받침 바로 밑(탭 뒤쪽)에는 드라이버가 닿지 않으므로 혀의 구멍을 씀. "
        "J501 기판은 그 뒤 받침 위에 MS 폴리머. 이음 레일·기둥 2개(M3 인서트를 먼저 인두로)를 뒤판 안면·아랫판에 MS 폴리머로. 보드는 받침 기둥에 먼저 나사(M3×5, Pi M2.5×6)로 단 뒤 기둥 밑을 "
        "아랫판에 MS 폴리머 (스스로 자리 잡음). 퓨즈 받침, 보조배터리 받침(접시 8호 13 × 4), 허브를 뒤판에 붙여 바닥에 놓고 허브 선반(받침 2를 뒤판에 "
        "Ø3 × 12 둥근머리 목재 나사 — 드라이버는 선반 윗면의 머리 길 홈을 따라 앞에서), 앰프를 선반 받침에(M3×6). 이 나사들은 모두 곧은 드라이버(Ø6 × 80)로 "
        "닿음 (check_body.py). XT30 집게 2개를 끝벽 안쪽 Ø14 구멍에 맞춰 MS 폴리머 (판 구멍과 끝벽 구멍이 같은 축), "
        "끝벽 L 안면에 케이블 집게 2개(y262~282·286~306, z48~58). 뚜껑 자석 12개(극이 서로 당기게). 전원선·5.1 V선·스피커선 배선 (스피커선 L은 끝벽 "
        "집게에 끼우고 y%s에서 끝벽을 떠나 보조배터리 앞을 건넘)." % (f(B.BP_TABS[0][2], 0), f(B.BP_TABS[0][3], 0), f(B.BP_TABS[1][2], 0),
                                                         f(B.BP_TABS[1][3], 1), f(__import__("electronics").SPKL_WALL_Y, 0)),
        "**책상에서: 건반 쪽** — 모듈과 끝 부속을 도브테일로 잇고, 볼 뒤 M3 자리에 방진 브래킷 BRK2 (그로밋 2 + M3×16 × 2, 스피커를 올리기 전에 조임). "
        "모듈 USB-C 선을 꽂아 통로 자리(y%s~%s) 책상 위에 눕힘. 스피커 밑에 올 O1·O7 선과 EL·ER 리드·JST-XH는 이때 통로 안쪽으로 가지런히." % (
            f(B.DUCT_Y[0], 0), f(B.DUCT_Y[1], 0)),
        "**가운데 유닛 놓기** — 모듈 뒤 2 mm 틈(y212~214)을 두고 놓음. 앞벽이 없어 앞 공간(y214~241)이 선 위로 옴.",
        "**스피커 놓기** — EVA 3T 띠 2줄을 스피커 안쪽 옆판에 미리 붙임. 스피커를 브래킷 핀보다 약 10 mm 위, 제자리보다 약 15 mm 바깥에 들고, 꼬리의 "
        "XT30U-F를 입구(가운데 쪽)부터 끝벽 Ø14 구멍(L z%s · R z%s)에 넣고 뒤끝을 드라이버 손잡이로 밀어 끝벽(11.5)과 집게 판(3)을 지나게 한 뒤, "
        "가운데 안에서 잡아 집게 홈에 곧게 당겨 넣고 눌러 끼움(L은 홈과 구멍이 같은 축, R은 구멍이 %s 낮음 - 둘 다 곧게 지나감). 스피커를 안쪽으로 밀어 EVA가 끝벽에 닿게 하면서 남는 꼬리(여유 약 %s mm)를 끝벽 구멍 안에 느슨하게 감아 넣고, 핀에 곧게 "
        "내려 끼움 (L 둥근 / R x 방향 긴 소켓, 핀 끝과 소켓 바닥 사이 2 mm). 가운데 안에서 M4 나비나사 2개씩 (머리는 고무 슬리브에만 닿음). 앰프 선 "
        "XT30U-M 꽂기 — 집게 홈에는 축 방향 멈춤이 없어(홈 뒤가 터널로 열려 있어야 스피커를 뗄 수 있음) 홈 안의 F에 M을 대고 밀면 F가 터널로 밀려 들어감: "
        "F를 홈 입구로 가운데 쪽에 당겨 꺼내고(꼬리 여유 약 %s mm), 손으로 M을 끝까지 꽂은 뒤, 짝을 다시 가져와 F 앞면을 홈 입구에 맞춰 위에서 걸림 턱 "
        "밑으로 눌러 끼움 (M은 입구 밖으로 나옴)." % (f(eh["L"][1], 1), f(eh["R"][1], 1),
                                                   f((B.XT30_POCKET["R"][4] + B.XT30_POCKET["R"][5]) / 2.0 - eh["R"][1], 1),
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
        "**뚜껑** — 뚜껑 L·R (자석 3쌍씩). 화면 뚜껑은 얹기 전에 리본을 기둥 x583으로 내려 안 쓰는 micro-HDMI 위로 Pi 5 CAM/DISP 1(x589, 입구 −x)에 "
        "2.7 꽂고 잠그며, 점퍼를 GPIO 2번(빨강 5 V)·6번(검정 GND)에 꽂음 → 이음 레일 위에 얹고 M3×10 × 4 (자리파기 5.5, 머리 자리 z67.35; 양쪽 이음에 0.5씩 "
        "틈). 고무발(5)과 모듈 EVA(3)의 눌림 차이로 뚜껑이 건반 윗면과 ±0.5 어긋나면 얇은 받침으로 맞춤.",
        "**받침다리 펴기·접기** — 화면을 22°(뒤꿈치가 멈춤 블록에 닿음)까지 앞으로 기울여 댄 채 다리를 내림: 다리가 수평 아래 약 40°에서 발이 경사에 먼저 "
        "닿고, 손을 놓으면 화면이 25°로 돌아가며 발이 경사를 타고 뒷벽까지 미끄러짐. 25°에서 그대로 내리면 발이 뒷벽 위 모서리를 약 0.66 긁음 "
        "(check_body.py가 22°·25° 두 경우를 돌려 봄). 접을 때도 22°에서 다리를 올려 받침 뒤 클립에 끼운 뒤 화면을 뒤로 눕힘.",
    ]


_PIG_OUT = [0.0]            # set in main() from the manifest (pigtail length outside the pod)

SERVICE = [
    ("패드 바", "없음", "뒷바가 y214부터라 패드 바(y146.5~185) 위가 비어 있음"),
    ("O2·O3 모듈", "뚜껑 L (자석)", "앞 공간에서 USB-C 부트를 위로 뽑고 모듈을 곧게 들어 올림"),
    ("O5 모듈", "뚜껑 R (자석)", "같음"),
    ("O4 모듈", "화면 뚜껑 (M3×10 4개, 화면째)",
     "사양 B (O4 정비): 화면을 뒤로 접고(다리는 클립에) → M3×10 4개(앞 y246, 뒤 y322)를 풂 → 뚜껑을 화면째 천천히 듦(리본을 꽂은 채 약 96 mm) → "
     "Pi 5 CAM/DISP 1 잠금 막대를 올려 리본을 뺌(화면 쪽 ZIF는 받침 안이라 건드리지 않음) → GPIO 2·6 점퍼를 뺌 → 뚜껑을 옆에 두고 앞 공간에서 플러그를 뽑음. "
     "되돌릴 때 리본 B형 방향 확인 후 잠금, 점퍼 2번 빨강·6번 검정, 나사 4개"),
    ("O1·O7 모듈, EL·ER 끝 부속", "그쪽 스피커", "허브에서 선을 뽑고 스피커를 들어낸 뒤 (아래 줄), 모듈을 곧게 들어 올림"),
    ("O6 모듈", "스피커 R (또는 뒷바 전체)", "플러그가 가운데 끝벽 R / 스피커 이음 밑"),
    ("스피커 하나", "뚜껑 L 또는 R",
     "XT30 짝을 홈 입구로 가운데 쪽에 당겨 꺼내 손으로 XT30U-M을 뽑고 F는 다시 홈에 눌러 끼움 (홈에는 축 방향 멈춤이 없음 - 짝은 홈 밖에서 꽂고 뽑음) → "
     "나비나사 2개 풀기 → 스피커를 약 10 mm 들어 핀에서 빼고, 통로 지붕 밑 케이블 집게에 끼운 선(EL·ER 리드·헤드폰 선)이 있으면 이때 모두 빼냄 "
     "(집게는 스피커에 붙어 있어 선이 같이 들림) → 약 15 mm 바깥으로 밂 (끝벽 구멍 안에 감긴 꼬리가 풀려 나오고 XT30U-F는 "
     "집게에 남음) → 가운데 안에서 XT30U-F를 집게 홈에서 끝벽 쪽으로 곧게 밀어 터널에 넣고(드라이버 손잡이로), 벌어진 틈에서 꼬리를 당겨 끝벽 구멍 "
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
     "없고 사양 centre_contents 상자(쌍 1368개 검사, 문제 0)를 그대로 씀: 보조배터리(A칸 x271.5~395.5) · I/O·PED·퓨즈(B) · 강압·J702(D) · "
     "Pi 5·동글(E) · 허브·앰프 선반(F x668~950.5). 보드는 사양의 받침 판(90×60) 대신 낱개 받침 기둥(보드에 먼저 나사, 기둥 밑을 아랫판에 MS 폴리머)이라 "
     "아랫판 흡기 홈을 막지 않음. 앰프 2 mm 받침은 허브 선반과 한 몸."),
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
     "%s → %s m² (400 × 1200 한 장). L1 뒷바는 src/body_L1.py · electronics_L1.py · check_*_L1.py(쓰지 않음)."
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
    ("A4", "구멍 크기",
     "레버 허브·핀 보스 구멍은 설계대로 Ø3.9로 출력(핀 보스는 눈물방울) → Ø4.0 드릴. 밸런스 핀 구멍 Ø1.95 막힌 구멍(z11.3까지, 가벼운 압입; 안 들어가면 Ø2.0으로 다듬음), 센서 바 받침 기둥 자가 탭 자리 Ø2.75(관통), 센서 바 쪽 Ø3.4, 제어 기판 보스 Ø2.5 막힌 구멍(z15.4까지), 캡스턴 자리 Ø2.8 + 끝 여유 Ø3.3, 너트 홈 맞변 5.6 × 2.6."),
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
         "%s m², 조각 %d (400 × 1200 한 장)" % (f(L2["plywood_cut_list"]["area_m2"], 3), ply)),
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
         "오꾸메 뚜껑 L·R과 틈 0이면 세 장이 나란히 들어가지 않음 (L2 설계). 화면 쪽 좌표는 모두 그대로; 받침과 뚜껑 끝 사이 %s (사양 %s)"
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
         "기둥 폭 10이라 나사를 가운데에 두려면 %s 옮겨야 함 (사양의 '안쪽으로 2'는 계산 실수). 인서트 L71 Ø4.5가 기둥 안에 다 들어감"
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
    "**레일 인서트 길이 (G-9):** 4로 모델 = 구매 목록 L71 (M3x4x4.5, 높이 4) — 자리파기 그대로. 다른 인서트로 바꾸면 자리파기 = 11.5 − (10 − 인서트 물림)으로 다시.",
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
    for pid in ("CU-SCREENLID", "TS-CRADLE", "TS-LEG", "TS-WINCOVER", "TS-RCLIP", "TS-SCREENCOVER", "TS-M3X20-HINGE-L", "TS-M3X20-HINGE-R", "TS-M3X20-LEG",
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
      "오꾸메 + 자석 3쌍, 가운데 화면 뚜껑(x501.5~720.5, 이음마다 0.5 틈)은 출력 + M3×10 4개입니다. 모두 가운데 유닛 벽·레일·기둥에만 얹혀 모듈에 힘이 가지 않습니다.")
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
    a("- **선 가리기:** 밖에서 선이 보이는 곳은 계획된 구멍뿐입니다 — 뚜껑 L·화면 뚜껑·뚜껑 R의 배기 홈 아래(위와 앉은 눈높이에서 뒤 줄의 20 V선·스피커선 L, "
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
      "M4×20 (L72, 최대 M4×22) — 이보다 길면 밀폐면(1.5~3.5 mm)을 뚫음. 안쪽 옆판의 L73 인서트 구멍 Ø%s × %s: 판 %s 중 밑에 **%s 이상** 남아야 함 "
      "(지름 부분 밑 %s, 드릴 끝 %s 밑 %s) — L73 나사산 인서트는 길이 %s (Norelem 07653-04, 최소 구멍 깊이 %s = 구멍 깊이) |"
      % (f(body.QS_HOLE[0], 1), f(body.QS_HOLE[1], 0), f(body.T, 1), f(body.QS_MIN_PLY, 1), f(body.T - body.QS_HOLE[1], 1), f(body.QS_POINT, 1),
         f(body.T - body.QS_HOLE[1] - body.QS_POINT, 1), f(body.INS[2], 0), f(body.QS_MIN_DEPTH, 0)))
    a("")
    # ---------------- folders
    a("## 폴더")
    a("")
    a("| 경로 | 내용 |")
    a("|---|---|")
    a("| `stl/print/` | **출력용.** 베드 위 방향으로 놓인 부품. 모양이 같은 부품은 파일 하나이고, 파일 이름 끝에 개수를 붙였습니다(`__7개`) |")
    a("| `stl/annotated/` | **보기용(출력 금지).** 부품 옆에 치수선과 숫자를 입체로 붙였습니다. 조립 방향으로 놓여 있습니다. `08_합판재단/`은 합판 조각(재단·구멍 자리) |")
    a("| `stl/assembly/` | 모든 부품을 조립 위치 그대로 둔 파일입니다. 그룹별 STL을 한꺼번에 열면 전체가 맞춰집니다 (단 `터치스크린_(접은_상태,_별도_보기).stl`은 접은 자세라 같이 열면 사용 상태 화면과 겹침; "
      "`댐퍼_페달_(바닥)`은 바닥 위치). `Toccata_전체조립.stl`은 한 파일에 전부 들어 있습니다 (접은 화면·페달 빼고) |")
    a("| `Toccata_전체조립.3mf` | 그룹·색 이름이 붙은 전체 조립(슬라이서·3D 뷰어용) |")
    a("| `Toccata_전체조립.glb` | 웹 뷰어용 |")
    a("| `manifest.json` | 부품마다 id, 이름, 종류, 그룹, 외곽 상자, 출력 파일 |")
    a("| `spec/` | 문서에서 뽑은 세부 사양(출처 포함). 뒷바는 `body_L2.json` |")
    a("| `viewer/` | 통합 아티팩트 09 CAD 탭 원본(cad.html·css·js, parts.json) |")
    a("| `src/` | 생성기. `python3 src/build_all.py` 한 번으로 STL·3MF·GLB·manifest·README·뷰어 데이터를 모두 다시 만듭니다(약 10~20초). "
      "검사: `check_interf.py`(건반 액션), `check_body.py`, `check_electronics.py` |")
    a("")
    # ---------------- print list
    a("## 출력 목록")
    a("")
    by = collections.OrderedDict()
    for r in rows:
        by.setdefault(r["folder"], []).append(r)
    tot_q = 0
    tot_g = 0.0
    for folder, rs in by.items():
        a("### %s%s" % (folder, " (04 대신 쓰는 변형)" if folder.startswith("04b") else (" (악기당 1벌)" if folder.startswith("06") else "")))
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
              "트리 서포트가 필요합니다. `화면덮개_선택`은 접은 화면을 덮을 때만 뽑습니다. 출력 전에 부록 A10의 '받은 부품으로 확인할 것'을 먼저 봅니다."
              % f(TS.CR["print_height"]))
            a("")
    a("04b 변형과 06 공구를 뺀 악기 출력 부품은 모두 %d개, 파일은 모두 %d종입니다. 질량은 속을 100%% 채운 PETG(1.27 g/cm³) 기준이라 실제(슬라이서 채움 %%)보다 큽니다. 모두 합하면 %.2f kg입니다." % (tot_q, len(rows), tot_g / 1000))
    a("")
    a("예비는 부품표(parts_list.json)를 따릅니다: 백건 파일마다 +1(10개), 흑건은 C#·D# +2, F# +1, G# +1, A#·A#0 +2(6개). 레버 캐리어와 패드 바는 예비 없이 필요할 때 위치별 파일로 뽑습니다.")
    a("")
    a("**채움:** 표의 질량은 100 % 채움 기준입니다. 건반·레버·패드 바·가림판은 벽 3줄 + 채움 25~40 %면 충분합니다. 끝 부속 볼(cheek), 스피커 앞판, 스피커 통로 틀은 "
      "속이 꽉 찬 덩어리이므로 벽 3~4줄 + 채움 15~40 %로 뽑습니다(볼 하나에 약 200 g 절약). 보드 받침 기둥, 캡스턴 게이지(T2)·핀 게이지(T3)만 채움 100 %입니다.")
    a("")
    a("**PORON 5T:** 업스톱 패드 설계값은 미세셀 우레탄 6T + 펠트 1T입니다(04 폴더의 패드 바 쐐기가 이 기준). 구매 목록(i124)은 PORON 5T이므로, 5T를 쓰면 `04b_패드바_PORON5T용` 파일(쐐기를 패드 면 법선으로 1.0 두껍게)을 뽑습니다. 6T를 사면 04 폴더 파일을 씁니다.")
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
          "(톱날 3 mm는 판매처 재단에서 빠짐). 치수는 이 모델에서 잰 값이고, 사양 표와 다르면 괄호에 사양 값을 적었습니다." % (n_ply, f(area, 3), f(pc["L1_area_m2"], 3)))
        a("")
        a("**폭 4 mm 홈(뚜껑 L·R 배기 홈, 뒤판 환기 홈, 가운데 아랫판 흡기 홈, 모두 %d개)은 직소 날(약 7 mm)이 들어가지 않습니다.** Ø4 구멍을 한 줄로 "
          "뚫어 잇고 줄로 다듬거나, 트리머에 4 mm 일자 비트를 씁니다. 홈 사이 나무는 4 mm입니다. **자석 자리 Ø8 × 3.2**(끝벽·뒤판 윗모서리 11.5 두께 가운데 → "
          "벽 1.75)는 판을 붙이기 전에 자투리 판 두 장 사이에 물려 포스트너 비트로 뚫습니다."
          % (len(body.LIDL_SLOTS) + len(body.LIDR_SLOTS) + len(body.BACK_SLOTS) + len(body.BOT_SLOTS_BUCK) + len(body.BOT_SLOTS_PI)))
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
    a("10/1 구매 목록 v4(`hardware/bom/toccata-purchase-list-v4.xlsx`)에 L69~L79·C22·C24·C25가 들어갔습니다. '구매 목록 v4 …' 줄은 CAD를 그 상품에 맞춘 것이고 "
      "(L73은 Norelem 07653-04 나사산 인서트로 바뀜), 나머지 줄은 v4에서 다시 확인할 것입니다.")
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
