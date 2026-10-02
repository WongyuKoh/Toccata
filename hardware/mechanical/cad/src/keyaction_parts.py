"""Key action (v4 W1+ r4.5) as Part instances: 7 octave modules O1..O7 + left (A0 A#0 B0) and right (C8)
end parts, world coordinates (A02..A04: left end part x0..47 + cheek x-16..0, module Ok at
x = 47 + 164.5 (k-1), right end part x1198.5..1238)."""
import re

from cadlib import teardrop_y, diff, box, clean, cyl_x, cyl_z, prism_x, union, orient, rot_x, rot_y, to_bed
from keyaction import (lever_print_support, lever_normalize, BLACK, FEAT, G, L_AXIS, bodies_of, classify, curtain_solid, fixed_groups, frame_solid,
                       key_bought, key_solid, lever_bought, lever_rest_angle, lever_solid, padbar_solids,
                       plug_solid, rotate_about_L, sensorbar_solid, spring_solid)
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
        # wire channel for the two C14 AUX cables (W701/W702, about D3.5 each) to the cheek rear face, open below
        cuts.append(box(-12.6, -4.1, 14.19, 212.5, 2.5, 7.5))
        bolts = [-11.80, -4.88]     # A7: centred on the cheek (x-8.34), 1.4 walls outside the 5.6 nut pockets
    else:
        adds.append(box(23.29, 24.19, 0.0, 212.0, 3.0, 5.0))
        bolts = [28.38, 35.30]      # A7: world 1226.88 / 1233.80, centred on the cheek (local 31.84)
    for bx in bolts:
        cuts.append(teardrop_y(bx, 12.0, 203.0, 212.5, 3.4))
        # M3 nut pocket AF 5.5 + 0.1, thickness 2.4 + 0.2 (same rule as the key nut traps), dropped in from below;
        # roof z15.2 >= 12 + 3.175 so the nut sits on the bolt axis
        cuts.append(box(bx - 2.8, bx + 2.8, 204.95, 207.55, 2.5, 15.2))
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
            print_note=("윗면(z55.5)을 매끈한 PEI에 대고 뒤집어 출력. 트리 서포트는 윗면 뒤끝 턱·숨은 빔·꼬리(y144.5~199) 밑만. "
                        if black else "윗면(z43.5)을 매끈한 PEI에 대고 뒤집어 출력. 트리 서포트는 숨은 빔·꼬리(y146~199) 밑만. ")
                       + "노치 R2.55·핀 홈에 부싱 천 0.5T(i068)를 붙임. 자석 Ø5×2 N35(i098) 압입 + 순간접착제, "
                         "캡스턴 M3×6 버튼헤드(i014) + M3 너트(i011)를 +x 옆 홈으로 (DESIGN 15, D02)",
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
            lv = lever_solid(lb, note, engrave=note, collars=COLL.get(note))
            out.append(Part(
                id="%s-LEVER-%s" % (tag, note.replace("#", "s")), name_ko="레버 캐리어 %s" % wname,
                name_en="lever carrier " + wname, kind="print", group="%s 레버" % label,
                solid=T(rotate_about_L(lv, ang)), color=COLORS["lever"], material="PETG",
                print_name="레버캐리어_" + note, print_folder="02_레버캐리어",
                print_solid=bed(union([lv, lever_print_support(lb)]), R_LEVER),
                print_note="−x 옆면을 베드에 눕혀 출력(칼라는 모두 +x 쪽, A5), 음 이름 새김(Arial Black, 0.4)이 위. "
                           "강철 칸 가운데(y169.4~170.6)의 떼는 지지대는 파일에 들어 있음(먼 옆벽과 0.2 틈, 뿌리 0.4): "
                           "떼어 내고 사포질한 뒤 접착. 허브 구멍 Ø3.9로 출력 → Ø4.0 드릴(i126). 강철 블록은 강철 띠 9T×19(i119)를 "
                           "40 −0.1/−0.3으로 잘라(칸 길이 40.0, 두께 8.9~9.1만) MS 폴리머로 접착 (DESIGN 15, D07)",
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

    # ---- frame (+ printed sub parts)
    ea, ec = cheek_features(side) if side else ([], [])
    fr = frame_solid(fx, plan, extra_cuts=ec, extra_adds=ea)
    fname = {"module": "프레임_모듈", "left": "끝부속프레임_왼쪽", "right": "끝부속프레임_오른쪽"}[side or "module"]
    out.append(Part(id="%s-FRAME" % tag, name_ko={"module": "프레임 (모듈)", "left": "끝 부속 프레임 왼쪽 (A0~B0, 볼 포함)",
                                                  "right": "끝 부속 프레임 오른쪽 (C8, 볼 포함)"}[side or "module"],
                    name_en="frame " + (side or "module"), kind="print", group="%s 프레임" % label, solid=T(fr),
                    color=COLORS["frame"], material="PETG 회색", print_name=fname, print_folder="03_프레임",
                    print_solid=bed(fr, R_NONE),
                    print_note="바로 세워 출력. 윗판 밑(y146.5~209)은 바닥·선반에서 올라오는 트리 서포트. 키퍼 훅 밑(y11~15 · y77~81, "
                               "z28.6)과 매단 위치 핀도 서포트. 핀 보스 구멍 Ø3.9 눈물방울 → Ø4.0 드릴. 밸런스 핀 구멍 Ø1.95(막힌 z11.3)는 "
                               "Ø1.9~2.0 드릴로 다듬고 핀 압입. 서포트 약 88 g (DESIGN 15)"
                               + (". 볼(cheek)은 속이 꽉 찬 덩어리: 벽 3줄 + 채움 15 % gyroid로 약 200 g 절약" if side else ""),
                    source=SRC))
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
    for nm, m in padbar_solids(fx, ranges, names, free=True).items():
        out.append(Part(id="%s-PADBAR-%s" % (tag, nm.split("_")[-1]), name_ko=nm.replace("_", " "), name_en="pad bar",
                        kind="print", group="%s 프레임" % label, solid=T(inst[nm]), color=COLORS["padbar"], material="PETG",
                        print_name=nm, print_folder="04_센서바·패드바·가림판·마개", print_solid=bed(m, R_PAD),
                        print_note="윗면을 베드에(쐐기가 위). 뒤 계단(y167~185)은 베드에서 1.5 떠 있으니 그 밑과 잎 혀 밑에 서포트"
                                   "(윗 틈 0.2, 인터페이스 1층; 이 면은 윗판 자리 z67.35라 매끈하게). 잎 혀는 자유 상태(설치 때 0.3 눌림)로 "
                                   "출력, 둘레 틈 0.6. 칸 이름은 윗면에 0.4 새김 (P13, DESIGN 15). 쐐기는 설계 패드 PORON 6T + 펠트 1T 기준",
                        source=SRC))
    if tag in ("O1", "EL", "ER"):
        for nm, m in padbar_solids(fx, ranges, names, free=True, wedge_extra=1.0).items():
            EXTRA_PRINTS.append(("04b_패드바_PORON5T용", nm + "_PORON5T용", bed(m, R_PAD), 7 if side is None else 1, "PETG",
                                 "구매 목록의 PORON 5T(i124)를 쓸 때의 패드 바: 쐐기를 패드 면 법선으로 1.0 두껍게(설계 6T와 같은 패드 면). "
                                 "6T를 사면 04 폴더 파일을 씀. 출력 방법은 04 패드 바와 같음"))

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
        eva = diff(box(0.5, 164.0, 0.5, 211.5, 0.0, 3.0), [box(46.25, 118.25, 144.5, 196.5, -1, 4)] + EVA_DOVE_NOTCH)
        enote = ("163.5 × 211, 기판 구멍 자리(x46.25~118.25 y144.5~196.5)와 왼쪽 끝 암 도브테일 홈 밑 두 곳"
                 "(x0.5~4.6 · y5.9~16.1, y197.4~207.6)을 오려 냄 — 이웃 모듈의 수 꼬리가 밑에서 들어감")
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
