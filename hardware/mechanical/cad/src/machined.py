"""Machined (not printed) parts of one octave module for the one-octave bundles: the steel weight blocks and the Ø4 shafts.

They are bought stock cut to length (steel strip i119, SUS304 rods i066 / i067), so stl/print has no file for them. The
bundles get a folder 05_가공부품_출력아님 with one STL per part (model size, for checking and for a slicer-free 3D view)
and a dimensioned cutting sheet 가공도면_무게추·샤프트.svg (sizes, tolerances, quantities, cut plans from the 1 m stock).
Sizes: DESIGN 4장 / 10장 (강철 9 × 19 × 40, 칸 40.0이라 40 −0.1/−0.3, 두께 8.9~9.1), CAD README A4 (봉 161.4 ± 0.2),
tools.md (공구 봉 토막 K 31.6 · L 20.6 · 교정 31.6), final_items i119 (띠 1 m에서 41.3 간격 24개).
"""
import io

FOLDER = "05_가공부품_출력아님"
SHEET = "가공도면_무게추·샤프트.svg"
STRIP_PITCH = 41.3            # 40 block + bandsaw kerf and squaring (final_items i119: 24 per 1 m strip)
ROD = 161.4

# stem in the zip, qty per octave, (kind, dims), what it is
PARTS = [
    ("무게추_강철블록_9x19x40", 12, ("box", (40.0, 19.0, 9.0)),
     "레버 무게 추. SS400 평철 9T×19(i119)를 40으로 절단. 처음 한 번은 1개 더(가짜 레버 T2용)"),
    ("샤프트_건반봉_Ø4x161.4", 1, ("rod", (ROD, 4.0)), "건반 봉. SUS304 Ø4 환봉(i066) 절단"),
    ("샤프트_레버봉_Ø4x161.4", 1, ("rod", (ROD, 4.0)), "레버 봉. SUS304 Ø4 환봉(i067) 절단, 왼쪽 끝에 출력 마개"),
    ("공구봉토막_Ø4x31.6", 2, ("rod", (31.6, 4.0)), "출력 공구 T1a의 K 자리 + 교정봉. 악기당 1벌(봉 4개 중 덜 쓰는 봉의 나머지)"),
    ("공구봉토막_Ø4x20.6", 1, ("rod", (20.6, 4.0)), "출력 공구 T1a의 L 자리. 악기당 1벌"),
]


def solid(kind, dims):
    import trimesh
    if kind == "box":
        m = trimesh.creation.box(extents=dims)
        m.apply_translation([dims[0] / 2, dims[1] / 2, dims[2] / 2])
    else:
        length, d = dims
        m = trimesh.creation.cylinder(radius=d / 2, height=length, sections=72)
        m.apply_transform(trimesh.transformations.rotation_matrix(1.5707963267948966, [0, 1, 0]))
        m.apply_translation([length / 2, 0, d / 2])
    return m


def stl_bytes(m):
    buf = io.BytesIO()
    m.export(buf, file_type="stl")
    return buf.getvalue()


def entries():
    """[(zip file name, stl bytes, qty, note)] in PARTS order."""
    out = []
    for stem, qty, (kind, dims), note in PARTS:
        out.append(("%s__%d개.stl" % (stem, qty), stl_bytes(solid(kind, dims)), qty, note))
    return out


def readme_lines():
    lines = ["", "%s/ — 3D 출력이 아닌 가공 부품 (사서 자르는 것):" % FOLDER]
    for stem, qty, (kind, dims), note in PARTS:
        lines.append("  %d개  %s  %s" % (qty, stem, note))
    lines += [
        "  %s: 치수·공차·수량·1 m 재료에서 자르는 배치. STL은 모델 치수 그대로(확인·보기용, 출력하지 않음)." % SHEET,
        "  강철 블록: 40 −0.1/−0.3(39.7~39.9, 캐리어 칸 40.0), 두께 8.9~9.1만 씀, 모따기 없이 버만 제거. 띠 1 m에서 %.1f 간격 24개." % STRIP_PITCH,
        "  봉: Ø4 h9 SUS304, %.1f ± 0.2, 양 끝 버 제거. 1 m 봉 하나에서 6개(봉 4개 = 모듈 14 + 예비 2 + 끝 부속·공구 토막)." % ROD,
    ]
    return lines


# ------------------------------------------------------------------ cutting sheet (SVG, mm drawn at 3 px/mm)
INK, DIM, MUTE, STEEL, ROD_C = "#1d2433", "#1f5fbf", "#5d6874", "#b9c0cc", "#d5dae1"


def _t(x, y, s, size=13, anchor="start", color=INK, weight=400):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return ('<text x="%.1f" y="%.1f" font-size="%s" text-anchor="%s" fill="%s" font-weight="%d">%s</text>'
            % (x, y, size, anchor, color, weight, s))


def _dim_h(x0, x1, y, label, ext_from=None):
    out = []
    if ext_from is not None:
        out += ['<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.7"/>' % (x, ext_from, x, y + 4, MUTE)
                for x in (x0, x1)]
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" marker-start="url(#a)" marker-end="url(#a)"/>'
               % (x0, y, x1, y, DIM))
    out.append(_t((x0 + x1) / 2, y - 5, label, 13, "middle", DIM, 600))
    return out


def _dim_v(x, y0, y1, label, ext_from=None):
    out = []
    if ext_from is not None:
        out += ['<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="0.7"/>' % (ext_from, y, x - 4, y, MUTE)
                for y in (y0, y1)]
    out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1" marker-start="url(#a)" marker-end="url(#a)"/>'
               % (x, y0, x, y1, DIM))
    out.append('<text x="%.1f" y="%.1f" font-size="13" text-anchor="middle" fill="%s" font-weight="600" transform="rotate(-90 %.1f %.1f)">%s</text>'
               % (x - 6, (y0 + y1) / 2, DIM, x - 6, (y0 + y1) / 2, label))
    return out


def _rect(x, y, w, h, fill, stroke=INK, sw=1.4):
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" stroke="%s" stroke-width="%s"/>' % (x, y, w, h, fill, stroke, sw)


def sheet_svg(date):
    S = 3.0                                  # px per mm in the detail views
    W, H = 1180, 1000
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'font-family="Apple SD Gothic Neo, Noto Sans KR, Malgun Gothic, sans-serif">' % (W, H, W, H),
         '<defs><marker id="a" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         '<path d="M0,1 L10,5 L0,9 z" fill="%s"/></marker></defs>' % DIM,
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         _rect(10, 10, W - 20, H - 20, "none", INK, 1.6),
         _t(30, 48, "가공 부품 — 무게 추(강철 블록)와 샤프트(Ø4 봉) · 옥타브 모듈 1개", 22, weight=700),
         _t(30, 72, "3D 출력이 아니라 사서 자르는 부품입니다. 단위 mm · 축척 3 : 1(부분도) · Toccata v4 W1+ · CAD %s" % date, 13, color=MUTE)]

    # --- 1. steel block: front (40 x 9), top (40 x 19), side (19 x 9)
    o.append(_t(30, 110, "① 무게 추 — 강철 블록 9 × 19 × 40", 16, weight=700))
    fx, fy = 60, 172
    o.append(_rect(fx, fy, 40 * S, 19 * S, STEEL))
    o += _dim_h(fx, fx + 40 * S, fy - 14, "40 −0.1 / −0.3  (39.7 ~ 39.9)")
    o += _dim_v(fx - 16, fy, fy + 19 * S, "19")
    o.append(_t(fx, fy + 19 * S + 18, "윗면 (40 × 19)", 12, color=MUTE))
    gy = fy + 19 * S + 44
    o.append(_rect(fx, gy, 40 * S, 9 * S, STEEL))
    o += _dim_v(fx - 16, gy, gy + 9 * S, "9")
    o.append(_t(fx + 40 * S + 14, gy + 9 * S / 2 + 4, "두께 8.9 ~ 9.1만 씀 (캘리퍼스)", 12, color=DIM))
    o.append(_t(fx, gy + 9 * S + 18, "앞면 (40 × 9)", 12, color=MUTE))
    sx = fx + 40 * S + 70
    o.append(_rect(sx, fy, 9 * S, 19 * S, STEEL))
    o += _dim_h(sx, sx + 9 * S, fy - 14, "9")
    o.append(_t(sx, fy + 19 * S + 18, "옆면 (19 × 9)", 12, color=MUTE))
    nx = 470
    notes = ["재료: SS400 평철 9T × 19 (i119, 1 m 띠 4장)",
             "길이 40 −0.1/−0.3: 레버 캐리어의 강철 칸이 40.0이라 딱 맞게",
             "두께 8.9 ~ 9.1: 칸 9.2, 접착층 한쪽 0.10 (MS 폴리머)",
             "모서리 모따기 없음, 자른 면의 버만 줄로 제거",
             "두 19 × 40 옆면 = 접착면: 붙이기 전에 #120 사포 → 알코올",
             "수량: 옥타브당 12 · 처음 한 번 +1 (가짜 레버 T2에 끼움)",
             "악기 전체: 88 + 예비 2 = 90 (블록 하나 53.7 g)"]
    for k, s in enumerate(notes):
        o.append(_t(nx, 150 + k * 22, "· " + s, 13))

    # --- 2. shafts
    y2 = 380
    o.append(_t(30, y2, "② 샤프트 — SUS304 Ø4 봉 (건반 봉 · 레버 봉 · 공구 봉 토막)", 16, weight=700))
    L = 161.4
    k2 = 5.6                                    # px/mm for the long rod (fits the sheet)
    rx, ry = 60, y2 + 60
    o.append(_rect(rx, ry, L * k2, 4 * k2, ROD_C))
    o += _dim_h(rx, rx + L * k2, ry - 18, "161.4 ± 0.2")
    o += _dim_v(rx - 16, ry, ry + 4 * k2, "Ø4 h9")
    o.append(_t(rx, ry + 4 * k2 + 26, "건반 봉 1 + 레버 봉 1 (옥타브당) · 양 끝 버 제거(허브·칼라를 긁지 않게) · 레버 봉 왼쪽 끝에 출력 마개 Ø4 × 1.2를 눌러 끼움", 12, color=MUTE))
    ty = ry + 4 * k2 + 70
    for k, (ln, lab) in enumerate(((31.6, "31.6 — T1a K 자리 / 교정봉 (2개)"), (20.6, "20.6 — T1a L 자리 (1개)"))):
        x = rx + k * 330
        o.append(_rect(x, ty, ln * k2, 4 * k2, ROD_C))
        o += _dim_h(x, x + ln * k2, ty - 18, "%.1f" % ln)
        o.append(_t(x, ty + 4 * k2 + 22, lab, 12, color=MUTE))
    o.append(_t(rx + 680, ty + 10, "공구 봉 토막: 악기당 1벌, 봉 4개 중 덜 쓰는 봉의 나머지에서", 12, color=MUTE))
    o.append(_t(rx + 680, ty + 30, "끝 부속 봉(왼 약 45 · 45.9, 오른 약 21 · 22.2)은 이 묶음 밖", 12, color=MUTE))

    # --- 3. cut plans from the 1 m stock
    y3 = 690
    o.append(_t(30, y3, "③ 1 m 재료에서 자르기", 16, weight=700))
    k3 = 1.05                                   # px/mm, 1000 mm = 1050 px
    bx, by = 60, y3 + 30
    o.append(_t(bx, by - 6, "강철 띠 9T × 19 × 1000 — %.1f 간격으로 24개 (블록 40 + 톱날·끝 맞춤 1.3)" % STRIP_PITCH, 12, color=MUTE))
    o.append(_rect(bx, by, 1000 * k3, 19 * k3 * 1.6, "#eef1f5", MUTE, 1))
    for i in range(24):
        x = bx + i * STRIP_PITCH * k3
        if i < 12:
            o.append(_rect(x, by, 40 * k3, 19 * k3 * 1.6, STEEL, INK, 0.9))
        else:
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#f7f8fa" stroke="%s" stroke-width="0.8" '
                     'stroke-dasharray="3 2"/>' % (x, by, 40 * k3, 19 * k3 * 1.6, MUTE))
    o.append(_t(bx + 12 * STRIP_PITCH * k3 / 2, by + 19 * k3 * 1.6 + 18, "한 옥타브 12개 (칠한 칸) · 점선 칸 = 다음 옥타브", 12, "middle", DIM))
    ry3 = by + 90
    o.append(_t(bx, ry3 - 6, "Ø4 봉 1000 — 161.4 × 6 = 968.4 (톱날 1.2씩 넣어도 약 24 남음)", 12, color=MUTE))
    o.append(_rect(bx, ry3, 1000 * k3, 4 * k3 * 4, "#eef1f5", MUTE, 1))
    x = bx
    for i in range(6):
        o.append(_rect(x, ry3, L * k3, 4 * k3 * 4, ROD_C, INK, 0.8))
        o.append(_t(x + L * k3 / 2, ry3 + 12, "161.4", 11, "middle", INK))
        x += (L + 1.2) * k3
    o.append(_t(bx, ry3 + 4 * k3 * 4 + 20, "건반 봉(i066)과 레버 봉(i067)은 같은 규격 · 한 옥타브는 2개 (건반 봉 1 + 레버 봉 1)", 12, color=DIM))
    o.append(_t(W - 30, H - 26, "원본: hardware/mechanical/cad/src/machined.py · DESIGN 4·10장 · tools.md · final_items i066 i067 i119", 11, "end", MUTE))
    o.append("</svg>")
    return "\n".join(o)
