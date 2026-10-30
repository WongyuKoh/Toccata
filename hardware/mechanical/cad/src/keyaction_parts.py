"""Key action (v4 W1+ r4.5) as Part instances: 7 octave modules O1..O7 + left (A0 A#0 B0) and right (C8)
end parts, world coordinates (A02..A04: left end part x0..47 + cheek x-16..0, module Ok at
x = 47 + 164.5 (k-1), right end part x1198.5..1238)."""
import re

from cadlib import teardrop_y, diff, box, clean, cyl_x, cyl_z, prism_x, prism_y, union, orient, rot_x, rot_y, to_bed
from keyaction import (lever_normalize, BLACK, FEAT, G, L_AXIS, bodies_of, classify, curtain_solid, fixed_groups, frame_split,
                       key_bought, key_solid, lever_body_solid, lever_bought, lever_cover_print, lever_cover_solid, lever_rest_angle,
                       padbar_solids, plug_solid, rotate_about_L, sensorbar_solid, spring_solid, A12, CAGE_SCREWS, SCREW)
from parts import COLORS, Part

MODULE_W = 164.5          # P01
X_O1 = 47.0               # A03
X_RIGHT = 1198.5          # A04
PAD_RANGES = [(3.10, 39.46), (43.86, 81.12), (85.52, 121.73), (126.13, 161.40)]   # P13
EVA_DOVE_NOTCH = [box(-1.0, 4.6, 5.9, 16.1, -1, 4), box(-1.0, 4.6, 197.4, 207.6, -1, 4)]   # female dovetail groove footprints (+0.5)
EXTRA_PRINTS = []          # print-only variants (not in the assembly): (folder, name, solid on bed, qty, material, note)
_SPRING_TPL = {False: ("spring C", 8.525), True: ("spring C#", 21.215)}    # module springs used as end-part templates
SRC = "key-action-v4/model/geometry.json (r4.5)"

R_KEY = rot_y(180)        # top face on the bed (DESIGN 15)
R_LEVER = rot_y(-90)      # left side wall on the bed, engraved right wall up (DESIGN 15)
R_PAD = rot_y(180)        # top face on the bed, wedges up
R_CURTAIN = rot_x(90)     # wide face on the bed, hook lip up
R_PLUG = rot_y(-90)       # end face on the bed
R_NONE = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
R_CAGE = rot_x(-90)       # A12 lever cage: rear wall (y212) on the bed, -y up
R_TAB = rot_y(-90)        # A12 guide tab: -x side on the bed
R_COVER = rot_y(90)       # A12 lever cover: outer (+x) face on the bed, lips up


def bed(m, R):
    return to_bed(orient(m, R))


def octave_note(note, k):
    """C..B of module k -> scientific pitch name (O1 = C1..B1)."""
    return "%s%d" % (note, k)


def _is_black(note):
    return "#" in note


BAYS = {None: [["C", "C#", "D"], ["D#", "E", "F"], ["F#", "G", "G#"], ["A", "A#", "B"]],
        "left": [["A0", "A#0", "B0"]], "right": [["C8"]]}


def collar_plan(side):
    """A5: move each lever-lever collar pair onto the lower-x lever's +x side (same total, same hub gaps)."""
    if side is None:
        col = G["solved"]["collars"]
    else:
        col = G["end_parts"][side]["collars"]
    out = {}
    for bay in BAYS[side]:
        for i, n in enumerate(bay):
            l, r = col[n]
            nxt = col[bay[i + 1]][0] if i + 1 < len(bay) else 0.0
            out[n] = (0.0, round(r + nxt, 3))
    return out


def _roof_y(x0, x1, y0, y1, z):
    """A13: 45 deg gable over a pocket / channel running along y whose flat top at z faced the bed."""
    xm = (x0 + x1) / 2.0
    return prism_y([(x0, z - 0.01), (x1, z - 0.01), (xm, z + (x1 - x0) / 2.0)], y0, y1)


def cheek_features(side):
    """left cheek: PJ-313 headphone-jack pocket (spec ka2 cheeks.headphone_jack); both cheeks: floor bridge to the
    key-area floor and two M3 bolt seats for the anti-vibration bracket at z12 (spec ka2 bracket.proposal_v4)."""
    adds, cuts = [], []
    if side == "left":
        adds.append(box(-0.70, 0.21, 0.0, 212.0, 3.0, 5.0))
        cx = -8.34
        cuts.append(teardrop_y(cx, 20.0, -0.5, 2.51, 5.2))
        cuts.append(box(-11.49, -5.19, 2.5, 14.2, 17.4, 22.6))
        cuts.append(box(-11.49, -5.19, 2.5, 14.2, 2.5, 17.41))
        cuts.append(_roof_y(-11.49, -5.19, 2.5, 14.2, 22.6))       # A13: 45 deg roof over the jack pocket (was flat)
        # wire channel for the two C14 AUX cables (W701/W702, about D3.5 each) to the cheek rear face, open below
        cuts.append(box(-12.6, -4.1, 14.19, 212.5, 2.5, 7.5))
        cuts.append(_roof_y(-12.6, -4.1, 14.19, 212.5, 7.5))       # A13: 45 deg roof (the flat top was 8.5 x 198)
        bolts = [-11.80, -4.88]     # A7: centred on the cheek (x-8.34), 1.4 walls outside the 5.6 nut pockets
    else:
        adds.append(box(23.29, 24.19, 0.0, 212.0, 3.0, 5.0))
        bolts = [28.38, 35.30]      # A7: world 1226.88 / 1233.80, centred on the cheek (local 31.84)
    for bx in bolts:
        cuts.append(teardrop_y(bx, 12.0, 199.0, 212.5, 3.4))   # 2026-10-07: to y199 for M3x20 (was y203 for M3x16) - tip y200.6, 1.6 clear
        # M3 nut pocket AF 5.5 + 0.1, thickness 2.4 + 0.2 (same rule as the key nut traps), dropped in from below.
        # A13: 90 deg V roof (was flat at z15.2, a ceiling in the print) - the nut (a corner up) rests on the two
        # slopes with its side corners, which holds it on the bolt axis z12 (V apex 12 + 2.75 + 1.59 = 16.34)
        cuts.append(box(bx - 2.8, bx + 2.8, 204.95, 207.55, 2.5, 13.55))
        cuts.append(prism_y([(bx - 2.8, 13.54), (bx + 2.8, 13.54), (bx, 16.34)], 204.95, 207.55))
    return adds, cuts


def build_unit(parts, plan, tag, x0, label, notes_world, side=None):
    """one module or end part. parts are in local x; x0 = world x of local 0."""
    out = []
    B = bodies_of(parts)
    fx = fixed_groups(parts)
    COLL = collar_plan(side)
    T = lambda m: m.translate((x0, 0, 0))

    # ---- keys + levers + springs
    for body, bp in B.items():
        if not body.startswith("key "):
            continue
        note = body.split(" ", 1)[1]
        wname = notes_world.get(note, note)
        black = _is_black(note)
        k = key_solid(bp, parts, note)
        pname = ("흑건_" if black else "백건_") + note
        out.append(Part(
            id="%s-KEY-%s" % (tag, note.replace("#", "s")), name_ko=("흑건 " if black else "백건 ") + wname,
            name_en=("black key " if black else "white key ") + wname, kind="print",
            group="%s %s" % (label, "흑건" if black else "백건"), solid=T(k), color=COLORS["black_key" if black else "white_key"],
            material="PETG " + ("검정" if black else "흰색"),
            print_name=pname, print_folder="01_건반",
            print_solid=bed(k, R_KEY),
            print_note=("윗면(z55.5)을 매끈한 PEI에 대고 뒤집어 출력. " if black else "윗면(z43.5)을 매끈한 PEI에 대고 뒤집어 출력. ")
                       + "서포트: Bambu Studio 서포트 켬, 트리(자동), '빌드 플레이트에서만' - 숨은 빔·꼬리(y146~199)만 바닥에서 "
                         "%s mm 떠 있어(위에 레버가 0.7 위) 트리 서포트가 그 밑에만 생기고 한 덩어리로 떨어짐. 건반 안쪽의 천장"
                         "(앞 멈춤 바닥, 걸쇠 가로대, 밸런스 블록 위 칸)은 45° V로 채워 서포트가 생기지 않음 (A13). "
                         "노치 R2.55·핀 홈에 부싱 천 0.5T(i068)를 붙임. 자석 Ø5×2 N35(i098) 압입 + 순간접착제, "
                         "캡스턴 M3×6 버튼헤드(i014)는 빔의 Ø2.7 구멍에 바로 돌려 넣음 - 너트 없음 (A13, DESIGN 15, D02)"
                         % ("27" if black else "15"),
            source=SRC))
        for nm, m in key_bought(bp, parts, note).items():
            kind = {"capstan": "bought", "nut": "bought", "magnet": "bought", "rest felt": "consumable"}[nm]
            ko = {"capstan": "캡스턴 나사 M3×6 버튼헤드 SUS304", "nut": "M3 육각너트 강철", "magnet": "네오디뮴 자석 Ø5×2 N35",
                  "rest felt": "쉼 펠트 1.5T + 종이 펀칭"}[nm]
            col = {"capstan": "stainless", "nut": "stainless", "magnet": "magnet", "rest felt": "felt"}[nm]
            out.append(Part(id="%s-%s-%s" % (tag, nm.upper().replace(" ", ""), note.replace("#", "s")),
                            name_ko="%s (%s)" % (ko, wname), name_en="%s %s" % (nm, wname), kind=kind,
                            group="%s 구매품" % label, solid=T(m), color=COLORS[col], source=SRC))
        lb = B.get("lever " + note)
        if lb:
            lb = lever_normalize(lb)
            ang = lever_rest_angle(lb)
            lv = lever_body_solid(lb, note, engrave=note, collars=COLL.get(note))
            cv = lever_cover_solid(lb)
            out.append(Part(
                id="%s-LEVER-%s" % (tag, note.replace("#", "s")), name_ko="레버 캐리어 %s" % wname,
                name_en="lever carrier " + wname, kind="print", group="%s 레버" % label,
                solid=T(rotate_about_L(lv, ang)), color=COLORS["lever"], material="PETG",
                print_name="레버캐리어_" + note, print_folder="02_레버캐리어",
                print_solid=bed(lv, R_LEVER),
                print_note="−x 옆면을 베드에 눕혀 출력(칼라는 모두 +x 쪽, A5), 음 이름 새김(Arial Black, 0.4)이 위. 서포트 없음: "
                           "강철 칸의 +x 벽은 레버 덮개(따로 출력)라 칸 위가 열려 있음 (A12, 옛 떼는 지지대 없음). "
                           "허브 구멍 Ø3.9로 출력 → Ø4.0 드릴(i126). 강철 블록은 강철 띠 9T×19(i119)를 40 −0.1/−0.3으로 잘라"
                           "(칸 길이 40.0, 두께 8.9~9.1만) 두 19×40 면에 MS 폴리머를 바르고 +x 쪽에서 칸에 넣은 뒤 레버 덮개를 덮어 "
                           "고무줄로 눌러 24 h (DESIGN 15, D07)",
                source=SRC))
            out.append(Part(
                id="%s-LEVERCOVER-%s" % (tag, note.replace("#", "s")), name_ko="레버 덮개 %s (+x 옆벽 + 립)" % wname,
                name_en="lever cover " + wname, kind="print", group="%s 레버" % label,
                solid=T(rotate_about_L(cv, ang)), color=COLORS["lever"], material="PETG",
                print_name="레버덮개", print_folder="02_레버캐리어",
                print_solid=bed(lever_cover_print(), R_COVER),
                print_note="바깥면(+x)을 베드에, 립 3개(위 앞·위 뒤·아래)가 위. 서포트 없음, 층 0.1 mm 권장(판 0.7). 레버 캐리어의 +x 옆벽을 "
                           "따로 뽑은 것 (A12): 강철을 넣은 칸 위에 덮어 강철 +x 면과 MS 폴리머로 붙임 - 위 앞 립 앞끝이 캐리어 앞 뚜껑(y153)에, "
                           "위 뒤 립 뒤끝이 칸 뒷벽(y190)에 닿아 자리가 잡힘. 앞끝 0.8과 뒤끝은 캐리어 앞벽·뒷벽 옆면에 같이 붙음. "
                           "모든 레버 덮개가 같은 모양",
                source=SRC))
            for nm, m in lever_bought(lb, "rest").items():
                if nm == "steel":
                    out.append(Part(id="%s-STEEL-%s" % (tag, note.replace("#", "s")),
                                    name_ko="강철 블록 9T×19×40 (강철 띠 i119 절단, %s)" % wname, name_en="steel block " + wname,
                                    kind="bought", group="%s 구매품" % label, solid=T(m), color=COLORS["steel"], source=SRC))
                else:
                    out.append(Part(id="%s-FELTSTRIP-%s" % (tag, note.replace("#", "s")),
                                    name_ko="캐리어 밑 펠트 띠 2T (메리노 울 펠트 i106, %s)" % wname, name_en="carrier felt strip " + wname,
                                    kind="consumable", group="%s 구매품" % label, solid=T(m), color=COLORS["felt"], source=SRC))
        sb = B.get("spring " + note)
        ssrc = SRC
        if sb:
            sp = spring_solid(sb)
        else:
            # end parts carry no spring bodies: same spring at the same pose relative to the lever (module C / C#)
            tb, txl = _SPRING_TPL[black]
            xl = G["end_parts"][side]["levers"][note] if side else None
            sp = spring_solid([p for p in G["parts"] if p["body"] == tb], dx=(xl - txl)) if xl is not None else None
            ssrc = SRC + " (끝 부속: 모듈 %s 스프링을 레버 x %.3f로 옮김)" % (tb.split()[1], xl or 0)
        if sp is not None:
            out.append(Part(id="%s-SPRING-%s" % (tag, note.replace("#", "s")),
                            name_ko="미스미 토션스프링 C-UA90R5-3-0.5, 다리 22.3/8.0 절단 (%s)" % wname,
                            name_en="torsion spring MISUMI C-UA90R5-3-0.5 " + wname, kind="bought",
                            group="%s 구매품" % label, solid=T(sp), color=COLORS["spring"], source=ssrc))

    # ---- frame (+ printed sub parts). A12 (2026-10-29): the frame is three kinds of print - bed, lever cage, guide tabs
    ea, ec = cheek_features(side) if side else ([], [])
    FS = frame_split(fx, plan, extra_cuts=ec, extra_adds=ea, side=side)
    unit_ko = {"module": "모듈", "left": "끝부속_왼쪽", "right": "끝부속_오른쪽"}[side or "module"]
    unit_name = {"module": "(모듈)", "left": "끝 부속 왼쪽 (A0~B0, 볼 포함)", "right": "끝 부속 오른쪽 (C8, 볼 포함)"}[side or "module"]
    joint = ("레버틀을 바닥틀에 얹을 때: 핀 발이 바닥틀의 홈 둑 사이에 들어가고, 바닥 밑에서 M3×10 자가 탭 나사 4개"
             "(앞 핀 2·3번 발, 뒤 선반 밑 2)로 조임 - 나사만으로 떼었다 붙였다 할 수 있고, 본드(MS 폴리머)를 같이 바르면 더 단단함"
             if side is None else
             "레버틀을 바닥틀에 얹을 때: 끝 핀·윗판 끝·봉 보스·뒷벽 끝이 볼 안쪽 면의 홈(깊이 약 1.1)에 들어가고, 안쪽 핀 발은 바닥틀 홈 둑 사이에 들어감 - "
             "볼 홈 면과 바닥에 MS 폴리머를 발라 붙임")
    out.append(Part(id="%s-FRAME" % tag, name_ko="프레임 바닥틀 %s" % unit_name, name_en="frame bed " + (side or "module"),
                    kind="print", group="%s 프레임" % label, solid=T(FS["bed"]), color=COLORS["frame"], material="PETG 회색",
                    print_name="프레임_바닥틀_" + unit_ko, print_folder="03_프레임",
                    print_solid=bed(FS["bed"], R_NONE),
                    print_note="바로 세워(바닥면을 베드에) 출력, 서포트 없음 (A13: 천장이 없음 - 밸런스 레일 밑 리본 길은 40° 뾰족 지붕, "
                               "암 도브테일 홈은 45° 지붕" + ("" if side else
                               ", 기판 자리는 바닥이 막혀 기판이 기둥 4개 위에 올라감 (위에서 M3×6 나사 2개 + 위치 핀 2개)")
                               + (", 볼의 잭 홈·선 홈은 45° 지붕, 너트 홈은 90° V 지붕" if side else "") + "). " +
                               ". 가이드 탭 자리(깊이 5.3, 둘레 틈 0.15)에 가이드 탭을 순간접착제로. 밸런스 핀 구멍 Ø1.95(막힌 z11.3)는 Ø1.9~2.0 드릴로 다듬고 핀 압입. "
                               + joint + (". 볼(cheek)은 속이 꽉 찬 덩어리: 벽 3줄 + 채움 15 % gyroid" if side else ""),
                    source=SRC, note="A12: 옛 한 몸 프레임의 아래 반쪽 (바닥·레일·밸런스 레일)"))
    out.append(Part(id="%s-CAGE" % tag, name_ko="프레임 레버틀 %s" % unit_name, name_en="frame lever cage " + (side or "module"),
                    kind="print", group="%s 프레임" % label, solid=T(FS["cage"]), color=COLORS["frame"], material="PETG 회색",
                    print_name="프레임_레버틀_" + unit_ko, print_folder="03_프레임",
                    print_solid=bed(FS["cage"], R_CAGE),
                    print_note="뒷벽 바깥면(y212)을 베드에 눕혀 출력 - 핀·윗판·선반이 모두 세워진 벽이 되어 서포트 없음 (A12). 윗판↔핀 이음이 한 층 안에 "
                               "있어 층간이 아님(옛 바로 세운 출력보다 강함). 핀 보스 구멍 Ø3.9 눈물방울(뾰족 끝이 위) → Ø4.0 드릴. 넓은 첫 층이라 "
                               "문 닫고 베드 70~80 °C, 모서리가 뜨면 브림 3 mm. 높이 %s" % ("67.5" if side is None else "65.5"),
                    source=SRC, note="A12: 옛 한 몸 프레임의 위 반쪽 (윗판·핀·뒷벽·선반)"))
    for note, kind, ts in FS["tabs"]:
        wname = notes_world.get(note, note)
        out.append(Part(id="%s-TAB-%s" % (tag, note.replace("#", "s")), name_ko="가이드 탭 %s (%s)" % ("흑건" if kind == "black" else "백건", wname),
                        name_en="guide tab " + wname, kind="print", group="%s 프레임" % label, solid=T(ts), color=COLORS["frame"],
                        material="PETG 회색", print_name="프레임_가이드탭_" + ("흑건" if kind == "black" else "백건"), print_folder="03_프레임",
                        print_solid=bed(ts, R_TAB),
                        print_note="옆면을 베드에 눕혀 출력 (서포트 없음, 키퍼 훅이 판 안에 있음). 키퍼 훅은 탭 폭 전체(설계 5.2 → 탭 폭)로 넓힘 - "
                                   "키퍼 펠트 2T(5.2 폭)는 훅 밑 가운데에 붙임. 촉(깊이 5)은 앞 1.0이 짧아 거꾸로 꽂히지 않음: 바닥틀 자리에 "
                                   "순간접착제를 한 방울 넣고 끝까지 꽂음 (A12; 옛 프레임의 탭 + 훅, 훅 밑 서포트가 없어짐). 부러지면 탭만 다시 뽑아 바꿈",
                        source=SRC, note="A12"))
    sbm = sensorbar_solid(fx, side)
    out.append(Part(id="%s-SENSORBAR" % tag, name_ko="센서 바" + ("" if side is None else (" 끝 부속 " + {"left": "왼쪽", "right": "오른쪽"}[side])),
                    name_en="sensor bar", kind="print", group="%s 프레임" % label, solid=T(sbm), color=COLORS["sensorbar"],
                    material="PETG 회색", print_name="센서바" + ("" if side is None else "_" + {"left": "왼쪽", "right": "오른쪽"}[side]),
                    print_folder="04_센서바·패드바·가림판·마개", print_solid=bed(sbm, R_NONE),
                    print_note="v3 방향(포켓이 위). 홀센서 DRV5055 LPG를 포켓에 눕혀 넣고 왼쪽 끝을 M3×10(i058) 2개로 받침 기둥에 자가 탭",
                    source=SRC))
    for i, (sx, sy) in enumerate(FEAT["sb_screws"]):
        scr = union([cyl_z(sx, sy, 3.6, 13.6, 3.0), cyl_z(sx, sy, 13.6, 15.25, 5.7)])
        out.append(Part(id="%s-SBSCREW%d" % (tag, i + 1), name_ko="스텐 유두 렌치볼트 M3 × 10 버튼헤드 ISO 7380 (센서 바·기판 → 받침 기둥 자가 탭, i058)",
                        name_en="M3x10 socket cap screw (sensor bar)", kind="bought", group="%s 구매품" % label,
                        solid=T(scr), color=COLORS["stainless"], source="DESIGN P36 / v3 P111 (3.0, 61.9)·(3.0, 74.6); BOM i058",
                        note="버튼헤드(머리 Ø5.7 × 1.65, 꼭대기 z15.25)로 삼. 캡볼트(DIN 912, 머리 3.0)면 끝까지 눌린 C·A0·C8 건반 밑과 0.48밖에 안 남음"))
    cur = curtain_solid(fx)
    out.append(Part(id="%s-CURTAIN" % tag, name_ko="가림판 띠" + ("" if side is None else (" 끝 부속 " + {"left": "왼쪽", "right": "오른쪽"}[side])),
                    name_en="cover curtain strip", kind="print", group="%s 프레임" % label, solid=T(cur),
                    color=COLORS["curtain"], material="PETG 검정", print_name="가림판띠" + ("" if side is None else "_" + {"left": "왼쪽", "right": "오른쪽"}[side]),
                    print_folder="04_센서바·패드바·가림판·마개", print_solid=bed(cur, R_CURTAIN),
                    print_note="넓은 면을 베드에, 걸이 립은 위로 (DESIGN 15)", source=SRC))
    plg = plug_solid(fx)
    out.append(Part(id="%s-PLUG" % tag, name_ko="레버 봉 끝 마개", name_en="lever rod end plug", kind="print",
                    group="%s 프레임" % label, solid=T(plg), color=COLORS["plug"], material="PETG",
                    print_name="레버봉끝마개", print_folder="04_센서바·패드바·가림판·마개", print_solid=bed(plg, R_PLUG),
                    print_note="끝면을 베드에 (원판 Ø4.0 × 1.2). 이음 쪽 핀 보스 구멍에 핀 면과 같게 눌러 끼움 (D18)",
                    source=SRC))
    if side is None:
        ranges = PAD_RANGES
        names = ["패드바_칸%d" % (i + 1) for i in range(4)]
    else:
        xs = [p["x"] for p in fx.get("padbar", [])]
        ranges = [(min(a for a, b in xs), max(b for a, b in xs))]
        names = ["패드바_끝부속_" + {"left": "왼쪽", "right": "오른쪽"}[side]]
    inst = padbar_solids(fx, ranges, names, free=False)
    # the purchase list buys PORON 5T (i124): the print file in stl/print is the 5T pad bar (wedge 1.0 thicker along the pad
    # normal, same pad face as the design 6T); the design-6T pad bar goes to stl/print_extra as the alternative
    free5 = padbar_solids(fx, ranges, names, free=True, wedge_extra=1.0)
    for nm, m in padbar_solids(fx, ranges, names, free=True).items():
        out.append(Part(id="%s-PADBAR-%s" % (tag, nm.split("_")[-1]), name_ko=nm.replace("_", " "), name_en="pad bar",
                        kind="print", group="%s 프레임" % label, solid=T(inst[nm]), color=COLORS["padbar"], material="PETG",
                        print_name=nm, print_folder="04_센서바·패드바·가림판·마개", print_solid=bed(free5[nm], R_PAD),
                        print_note="윗면(한 평면 z67.35 = 윗판 자리)을 베드에, 쐐기·잎 혀 돌기가 위. 서포트 없음 (A12: 윗면 계단을 없애고 앞부분을 "
                                   "1.0 두께로 내림, 잎 혀를 윗면과 같은 높이로 올림 - 윗판 밑 0.6 홈이 혀 길을 비움). 잎 혀는 자유 상태(설치 때 0.3 눌림)로 "
                                   "출력, 둘레 틈 0.6. 칸 이름은 윗면에 0.4 새김 (P13, DESIGN 15). 쐐기는 구매 목록의 PORON 5T(i124) + 펠트 1T 기준 "
                                   "(설계 6T보다 쐐기를 패드 면 법선으로 1.0 두껍게 - 패드 면은 같음; 조립 모델은 설계 6T로 그림)",
                        source=SRC))
    if tag in ("O1", "EL", "ER"):
        for nm, m in padbar_solids(fx, ranges, names, free=True).items():
            EXTRA_PRINTS.append(("@extra/대안_패드바_PORON6T용", nm + "_PORON6T용", bed(m, R_PAD), 7 if side is None else 1, "PETG",
                                 "대안: PORON 6T(설계값)를 사면 stl/print/04의 패드 바 6종 대신 이것을 뽑음 (쐐기가 1.0 얇음, 패드 면은 같음). "
                                 "구매 목록대로 5T를 쓰면 뽑지 않음. 출력 방법은 04 패드 바와 같음"))

    # ---- bought / consumable prisms from the model
    for p in fx.get("bought", []):
        n = p["part"]
        m = prism_x(p["side"], *p["x"])
        kind, ko, col = "bought", n, "stainless"
        if "felt" in n:
            kind, col = "consumable", "felt"
            ko = {"white front felt 3T": "백건 앞 펠트 (메리노 울 2T i106 + 하네나이트 1T i125)", "keeper felt": "키퍼 펠트 2T (i106)",
                  "black front felt": "흑건 앞 펠트 (메리노 울 2T i106 + 하네나이트 1T i125)"}.get(re.sub(r" (A#0|A0|B0|C8|A#|C#|D#|F#|G#|[A-G])$", "", n), n)
        elif n.startswith("key rod"):
            ko = "건반 봉 SUS304 Ø4 (환봉 i066, 161.4 절단)"
        elif n.startswith("lever rod D4"):
            ko = "레버 봉 SUS304 Ø4 (환봉 i067, 161.4 절단)"
        elif n.startswith("balance pin"):
            xs = p["x"]
            ys = [q[0] for q in p["side"]]
            zs = [q[1] for q in p["side"]]
            m = cyl_z((xs[0] + xs[1]) / 2, (min(ys) + max(ys)) / 2, min(zs), max(zs), 2.0)
            ko = "밸런스 핀 Ø2×12 SUS304 (i121)"
        elif n.startswith("up-stop pad"):
            ko, col = "업스톱 패드 (설계: 미세셀 우레탄 6T + 펠트 1T; 구매 목록은 PORON 5T i124 → 04b 패드 바)", "pad"
            kind = "consumable"
        elif n.startswith("control-board screw"):
            ko = "스텐 렌치볼트 M3 × 6 (제어 기판, i059)"
            # A13: screwed from above through the board (z9.0..10.6) into the post's pilot - head on the board
            sx = (p["x"][0] + p["x"][1]) / 2
            sy = sum(q[0] for q in p["side"]) / len(p["side"])
            m = union([cyl_z(sx, sy, 10.6, 13.6, 5.5), cyl_z(sx, sy, 4.6, 10.61, 3.0)])
        elif n.startswith("control board"):
            ko, col, kind = "제어 기판 (만능기판 70×50, 1.6T)", "pcb_perf", "electronics"
            holes = [cyl_z(c["circle"][0], c["circle"][1], 8.0, 12.0, 3.0) for c in plan if c["part"].startswith("control-board locating pin")]
            holes += [cyl_z(c["circle"][0], c["circle"][1], 8.0, 12.0, 3.2) for c in plan if c["part"].startswith("control-board screw")]
            m = diff(m, holes)
        elif n.startswith("sensor board"):
            ko, col, kind = "센서 기판 %s (스트립보드 6행, 1.6T)" % n.split()[2], "pcb_perf", "electronics"
            m = diff(m, [cyl_z(sx, sy, 6.0, 10.0, 3.2) for (sx, sy) in FEAT["sb_screws"]])
        elif n.startswith("board part: RP2040"):
            ko, col, kind = "RP2040-Zero (핀 헤더 위)", "pcb_blue", "electronics"
        elif n.startswith("board part: USB-C receptacle"):
            ko, col, kind = "RP2040-Zero USB-C 리셉터클", "metal", "electronics"
        elif n.startswith("board part: CD74HC4067"):
            ko, col, kind = "CD74HC4067 16채널 먹스 모듈 (핀 헤더 위)", "pcb_green", "electronics"
        elif n.startswith("board part: J301 16-core ribbon"):
            ko, col, kind = "16심 리본 케이블 (기판 밑)", "cable", "electronics"
        elif n.startswith("USB-C plug"):
            ko, col, kind = "USB-C 케이블 플러그 (모듈 → 허브)", "cable", "electronics"
        elif n.startswith("board components") or n.startswith("board part: J30") or n.startswith("J4") \
                or n.startswith("lead ") or n.startswith("underside wire"):
            continue            # keep-out envelopes / small circuit parts: omitted (user request)
        if kind == "electronics":
            continue            # boards / modules / cables come from electronics.py (spec/electronics_modules.json)
        mnote = re.search(r" (A#0|A0|B0|C8|A#|C#|D#|F#|G#|[A-G])$", n)
        if mnote:
            nn = mnote.group(1)
            ko = "%s (%s)" % (ko, notes_world.get(nn, nn))
            base = re.sub(r"[^A-Za-z0-9]+", "", n[:mnote.start()])[:24] + "-" + nn.replace("#", "s")
        else:
            base = re.sub(r"[^A-Za-z0-9]+", "", n)[:28]
        out.append(Part(id="%s-B-%s" % (tag, base), name_ko=ko, name_en=n, kind=kind,
                        group="%s %s" % (label, "전자부" if kind == "electronics" else "구매품"), solid=T(m),
                        color=COLORS[col], source=SRC))
    # EVA bottom sheet z0..3 under the frame floor (S01)
    # BOM i061 cut pieces: module 163.5 x 211, end parts 63 x 211 / 39.5 x 211 (whole footprint incl. the cheek);
    # the module sheet is cut open under the control-board hatch so the board stays serviceable from below
    if side is None:
        eva = diff(box(0.5, 164.0, 0.5, 211.5, 0.0, 3.0), EVA_DOVE_NOTCH
                   + [cyl_z(sx, sy, -1, 4, 7.0) for (sx, sy, _k) in CAGE_SCREWS])
        enote = ("163.5 × 211, 왼쪽 끝 암 도브테일 홈 밑 두 곳(x0.5~4.6 · y5.9~16.1, y197.4~207.6)을 오려 냄 — 이웃 모듈의 수 꼬리가 "
                 "밑에서 들어감. A12: 레버틀 나사 머리 자리 Ø7 4곳 (%s)도 뚫음. A13: 기판 자리 구멍은 없음 (바닥틀이 막혀 기판은 위에서)"
                 % ", ".join("x%.1f y%.1f" % (sx, sy) for (sx, sy, _k) in CAGE_SCREWS))
    elif side == "left":
        eva = box(-16.0, 47.0, 0.5, 211.5, 0.0, 3.0)
        enote = "63 × 211 (볼 포함): 볼 밑의 잭 넣는 홈·선 홈·너트 홈을 덮음"
    else:
        eva = diff(box(0.0, 39.5, 0.5, 211.5, 0.0, 3.0), EVA_DOVE_NOTCH)
        enote = "39.5 × 211 (볼 포함): 볼 밑의 너트 홈을 덮고, 암 도브테일 홈 밑 두 곳(x0~4.6 · y5.9~16.1, y197.4~207.6)을 오려 냄"
    out.append(Part(id="%s-EVA" % tag, name_ko="EVA 고밀도 폼 3T 바닥 (i061)", name_en="EVA bottom sheet 3T", kind="consumable",
                    group="%s 구매품" % label, solid=T(eva), color=COLORS["rubber"], source="S01 (DESIGN 5); BOM i061",
                    note=enote))
    return out


def build_all():
    parts = []
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    for k in range(1, 8):
        nw = {n: octave_note(n, k) for n in notes}
        parts += build_unit(G["parts"], G["plan"], "O%d" % k, X_O1 + MODULE_W * (k - 1), "O%d" % k, nw, None)
    E = G["end_parts"]
    parts += build_unit(E["left"]["parts"], E["left"]["plan"], "EL", 0.0, "끝 부속 왼쪽", {}, "left")
    parts += build_unit(E["right"]["parts"], E["right"]["plan"], "ER", X_RIGHT, "끝 부속 오른쪽", {}, "right")
    return parts
