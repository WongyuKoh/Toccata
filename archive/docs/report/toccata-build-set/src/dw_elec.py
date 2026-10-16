"""Wiring diagrams (pixel-space SVG)."""


def _t(x, y, s, cls="st", anchor="start"):
    s = str(s).replace("&", "&amp;").replace("<", "&lt;")
    return f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}">{s}</text>'


# Pico 2 pins a key module uses: (name, physical pin number). build.page_elec's pin table uses the same tuples.
PIN_3V3 = ("3V3 OUT", 36)
PIN_AGND = ("AGND", 33)
PIN_GND = ("GND", 38)


FS_S = 12        # px, font-size of .sch .st-s (asserted against SCH_CSS below)


def _tw(s, fs):
    """rough rendered width (px) of a label: Hangul ~1 em, space ~0.3 em, other glyphs ~0.6 em."""
    return sum(fs * (1.0 if ord(c) >= 0x1100 else 0.3 if c == " " else 0.6) for c in str(s))


def _dot(x, y, cls, r=2.5):
    """junction dot: a branch that ends on a bus (a bare crossing has no dot)."""
    return f'<circle class="{cls}" cx="{x}" cy="{y}" r="{r}"/>'


def module_schematic():
    W, H = 1100, 560
    o = [f'<svg class="sch" viewBox="0 0 {W} {H}" role="img" aria-label="건반 모듈 배선도" xmlns="http://www.w3.org/2000/svg">']
    VY, GY = 40, 520            # 3V3 / GND rail y
    VX, GX = 80, 72             # sensor-column 3V3 / GND vertical bus x
    BO = 6                      # 3V3 branch at y-BO, GND branch at y+BO (room for the cap symbol between them)
    # power rails
    o.append(f'<line class="w-vcc" x1="40" y1="{VY}" x2="700" y2="{VY}"/>')
    o.append(f'<line class="w-gnd" x1="40" y1="{GY}" x2="700" y2="{GY}"/>')
    o.append(_t(40, 30, f"3V3 버스 (피코 {PIN_3V3[1]}번 핀 {PIN_3V3[0]})", "st-b"))
    o.append(_t(40, 545, f"GND 버스 (피코 {PIN_AGND[1]}번 {PIN_AGND[0]} · MUX EN만 {PIN_GND[1]}번 {PIN_GND[0]})", "st-b"))
    # sensors
    n = 12
    y0, dy = 70, 36
    y_last = y0 + (n - 1) * dy
    for i in range(n):
        y = y0 + i * dy
        x = 120
        o.append(f'<rect class="ic" x="{x}" y="{y-11}" width="46" height="22" rx="3"/>')
        o.append(_t(x + 23, y + 4, f"H{i+1}", "st-c", "middle"))
        # vcc / gnd branches: each starts on its own vertical bus (GND crosses the 3V3 bus without a dot)
        o.append(f'<line class="w-vcc t" x1="{VX}" y1="{y-BO}" x2="{x}" y2="{y-BO}"/>')
        o.append(f'<line class="w-gnd t" x1="{GX}" y1="{y+BO}" x2="{x}" y2="{y+BO}"/>')
        o.append(_dot(VX, y - BO, "jv") + _dot(GX, y + BO, "jg"))
        o.append(f'<line class="w-sig" x1="{x+46}" y1="{y}" x2="520" y2="{y}"/>')
        o.append(_t(x + 52, y - 4, f"C{i}", "st-s"))
        # decoupling cap between the two branches (plates horizontal, leads to 3V3 above / GND below)
        cx_ = x - 24
        o.append(f'<line class="cap" x1="{cx_-5}" y1="{y-1.5}" x2="{cx_+5}" y2="{y-1.5}"/><line class="cap" x1="{cx_-5}" y1="{y+1.5}" x2="{cx_+5}" y2="{y+1.5}"/>'
                 f'<line class="w-vcc t" x1="{cx_}" y1="{y-BO}" x2="{cx_}" y2="{y-1.5}"/><line class="w-gnd t" x1="{cx_}" y1="{y+1.5}" x2="{cx_}" y2="{y+BO}"/>')
        o.append(_dot(cx_, y - BO, "jv", 2) + _dot(cx_, y + BO, "jg", 2))
    o.append(f'<line class="w-vcc" x1="{VX}" y1="{VY}" x2="{VX}" y2="{y_last-BO}"/>')
    o.append(f'<line class="w-gnd" x1="{GX}" y1="{y0+BO}" x2="{GX}" y2="{GY}"/>')
    o.append(_dot(VX, VY, "jv") + _dot(GX, GY, "jg"))
    o.append(_t(GX + 8, y_last + 11 + 16, f"DRV5055A3 ×{n} (O1은 15개, O7은 13개)", "st-s"))
    o.append(_t(GX + 8, y_last + 11 + 32, "각 센서 VCC–GND 사이 100 nF", "st-s"))
    # mux
    mx, my = 520, 60
    o.append(f'<rect class="ic2" x="{mx}" y="{my}" width="150" height="440" rx="6"/>')
    o.append(_t(mx + 75, my + 24, "CD74HC4067", "st-b", "middle"))
    o.append(_t(mx + 75, my + 42, "16채널 아날로그 MUX", "st-s", "middle"))
    for i in range(16):
        yy = 70 + i * 26 if i >= n else None
    for i, lab in enumerate(["SIG", "S0", "S1", "S2", "S3", "EN", "VCC", "GND"]):
        yy = my + 80 + i * 40
        o.append(_t(mx + 142, yy + 4, lab, "st-s", "end"))
        o.append(f'<circle class="pin" cx="{mx+150}" cy="{yy}" r="3"/>')
    o.append(_t(mx + 10, my + 400, "C12–C15: 빈 채널은", "st-s"))
    o.append(_t(mx + 10, my + 416, "GND에 묶음 (O1/O7 제외)", "st-s"))
    # pico
    px, py = 820, 60
    o.append(f'<rect class="ic3" x="{px}" y="{py}" width="190" height="440" rx="8"/>')
    o.append(_t(px + 95, py + 24, "Raspberry Pi Pico 2", "st-b", "middle"))
    o.append(_t(px + 95, py + 42, "USB-MIDI 장치 \"Toccata O2\"", "st-s", "middle"))
    pins = [("GP26 / ADC0", "SIG"), ("GP2", "S0"), ("GP3", "S1"), ("GP4", "S2"), ("GP5", "S3"), (PIN_GND[0], "EN"), (PIN_3V3[0], "VCC"), (PIN_AGND[0], "GND")]
    prow = lambda i: py + 80 + i * 40          # same row pitch as the MUX pins
    for i, (pn, ml) in enumerate(pins):
        yy = prow(i)
        o.append(f'<circle class="pin" cx="{px}" cy="{yy}" r="3"/>')
        o.append(_t(px + 10, yy + 4, pn, "st-s"))
        cls = "w-sig" if i == 0 else ("w-ctl" if i < 5 else ("w-gnd" if ml in ("EN", "GND") else "w-vcc"))
        o.append(f'<line class="{cls}" x1="{mx+150}" y1="{yy}" x2="{px}" y2="{yy}"/>')
    o.append(_t(px + 95, py + 420, "USB → 전원 있는 허브 → Pi 5", "st-s", "middle"))
    # rails join the Pico 3V3 OUT row and the AGND row (the rows come from the same pins list)
    y_vcc = prow([p for p, _ in pins].index(PIN_3V3[0]))
    y_agnd = prow([p for p, _ in pins].index(PIN_AGND[0]))
    o.append(f'<line class="w-vcc" x1="700" y1="{VY}" x2="760" y2="{VY}"/><line class="w-vcc" x1="760" y1="{VY}" x2="760" y2="{y_vcc}"/>')
    o.append(f'<line class="w-gnd" x1="700" y1="{GY}" x2="780" y2="{GY}"/><line class="w-gnd" x1="780" y1="{GY}" x2="780" y2="{y_agnd}"/>')
    o.append(_dot(760, y_vcc, "jv") + _dot(780, y_agnd, "jg"))
    o.append("</svg>")
    return "".join(o)


def system_diagram():
    W, H = 1100, 360
    o = [f'<svg class="sch" viewBox="0 0 {W} {H}" role="img" aria-label="전체 신호 흐름" xmlns="http://www.w3.org/2000/svg">']
    mods = ["O1 A0–B1", "O2 C2–B2", "O3 C3–B3", "O4 C4–B4", "O5 C5–B5", "O6 C6–B6", "O7 C7–C8", "PED 페달 3개"]
    for i, m in enumerate(mods):
        y = 18 + i * 37
        o.append(f'<rect class="ic3" x="20" y="{y}" width="150" height="28" rx="5"/>')
        o.append(_t(95, y + 19, m, "st-c", "middle"))
        o.append(f'<line class="w-usb" x1="170" y1="{y+14}" x2="250" y2="165"/>')
    o.append('<rect class="ic2" x="250" y="130" width="110" height="70" rx="6"/>')
    o.append(_t(305, 160, "USB 허브", "st-b", "middle"))
    o.append(_t(305, 178, "10포트·자체 전원", "st-s", "middle"))
    o.append('<line class="w-usb" x1="360" y1="165" x2="400" y2="165"/>')
    o.append('<rect class="ic" x="400" y="105" width="150" height="120" rx="8"/>')
    o.append(_t(475, 132, "Raspberry Pi 5", "st-b", "middle"))
    o.append(_t(475, 152, "Pianoteq 9 Stage", "st-s", "middle"))
    o.append(_t(475, 170, "ALSA hw:, 48 kHz", "st-s", "middle"))
    o.append(_t(475, 188, "8개 입력 병합 1곳", "st-s", "middle"))
    o.append(_t(475, 206, "+ Pi DAC+ (HAT)", "st-s", "middle"))
    o.append('<line class="w-pwr" x1="475" y1="300" x2="475" y2="225"/>')
    o.append('<rect class="ic3" x="400" y="300" width="150" height="30" rx="5"/>')
    o.append(_t(475, 320, "Pi 27 W USB-C 전원", "st-c", "middle"))
    o.append('<line class="w-i2s" x1="550" y1="150" x2="640" y2="150"/>')
    o.append(_t(595, 142, "RCA 라인", "st-s", "middle"))
    o.append('<rect class="ic2" x="640" y="105" width="170" height="100" rx="8"/>')
    o.append(_t(725, 132, "KABD-430 DSP 앰프", "st-b", "middle"))
    o.append(_t(725, 152, "100 Hz 크로스오버", "st-s", "middle"))
    o.append(_t(725, 170, "2×30 W + 60 W", "st-s", "middle"))
    o.append(_t(725, 188, "MP 핀 = 스피커 뮤트", "st-s", "middle"))
    amp_pwr_x, adp_y = 725, 300                            # amp's 24 V drop (x) / top of the adapter boxes (y)
    o.append(f'<line class="w-pwr" x1="{amp_pwr_x}" y1="{adp_y}" x2="{amp_pwr_x}" y2="205"/>')
    o.append(f'<rect class="ic3" x="650" y="{adp_y}" width="150" height="30" rx="5"/>')
    o.append(_t(725, 320, "24 V 5 A 어댑터", "st-c", "middle"))
    (hx0, hy0), (hx1, hy1) = (550, 200), (870, 262)       # headphone line: DAC+ corner of the Pi box -> jack box
    o.append(f'<line class="w-spk" x1="{hx0}" y1="{hy0}" x2="{hx1}" y2="{hy1}"/>')
    # label centred in the free span between the line start (Pi box edge) and the amp's 24 V drop (x 725),
    # its glyph tops 6 px below the line at the label's right end (the line falls to the right)
    hp_lab = "헤드폰 출력 (DAC+)"
    hcx, hw = (hx0 + amp_pwr_x) / 2, _tw(hp_lab, FS_S)
    assert hx0 < hcx - hw / 2 and hcx + hw / 2 < amp_pwr_x, "headphone label does not fit between the Pi box and the 24 V line"
    hy_r = hy0 + (hy1 - hy0) * (hcx + hw / 2 - hx0) / (hx1 - hx0)
    hby = hy_r + 6 + 0.9 * FS_S
    assert hby + 0.3 * FS_S < adp_y, "headphone label runs into the adapter boxes"
    o.append(_t(f"{hcx:.1f}", f"{hby:.1f}", hp_lab, "st-s", "middle"))
    o.append('<line class="w-ctl" x1="920" y1="276" x2="760" y2="205"/>')
    o.append(_t(868, 232, "잭 스위치 → PC817", "st-s", "middle"))
    for lab, y in [("위성 L · DMA105-4", 60), ("위성 R · DMA105-4", 110), ("서브 · RSS210HF-4", 160)]:
        o.append(f'<line class="w-spk" x1="810" y1="155" x2="880" y2="{y+14}"/>')
        o.append(f'<rect class="ic" x="880" y="{y}" width="200" height="28" rx="5"/>')
        o.append(_t(980, y + 19, lab, "st-c", "middle"))
    o.append('<rect class="ic" x="870" y="250" width="210" height="28" rx="5"/>')
    o.append(_t(975, 269, "헤드폰 잭 NMJ6HCD2 (6.35 mm)", "st-c", "middle"))
    o.append("</svg>")
    return "".join(o)


SCH_CSS = """
.sch{width:100%;height:auto;display:block;min-width:720px}
.sch .st,.sch .st-s,.sch .st-b,.sch .st-c{fill:var(--ink);font-family:"IBM Plex Sans KR",system-ui,sans-serif}
.sch .st-s{font-size:12px;fill:var(--ink-2)} .sch .st-b{font-size:14px;font-weight:600} .sch .st-c{font-size:12.5px}
.sch .ic{fill:var(--card);stroke:var(--ink);stroke-width:1.2}
.sch .ic2{fill:var(--tint-blue);stroke:var(--ink);stroke-width:1.2}
.sch .ic3{fill:var(--tint-green);stroke:var(--ink);stroke-width:1.2}
.sch .pin{fill:var(--ink)}
.sch line{stroke-width:1.6}
.sch .w-vcc{stroke:#c2410c}.sch .w-gnd{stroke:var(--ink-2)}.sch .w-sig{stroke:#1f5fbf}.sch .w-ctl{stroke:#7c3aed}
.sch .w-usb{stroke:#0f766e;stroke-width:2}.sch .w-i2s{stroke:#1f5fbf;stroke-width:2.5}.sch .w-spk{stroke:var(--ink);stroke-width:2}
.sch .w-pwr{stroke:#c2410c;stroke-width:2.5}.sch .t{stroke-width:1.1}.sch .cap{stroke:var(--ink);stroke-width:1.6}
.sch .jv{fill:#c2410c}.sch .jg{fill:var(--ink-2)}
"""
assert f".sch .st-s{{font-size:{FS_S}px" in SCH_CSS, "FS_S out of step with SCH_CSS"
