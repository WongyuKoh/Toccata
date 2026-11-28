"""Tab 'uno' (01b 아두이노 버전): the Arduino Uno + laptop version next to the Raspberry Pi version.

Reads hardware/pcb/uno (build_uno.py output: sheets.json, *.csv, schematic/*.svg) and hardware/pcb/src/uno_sheets.py
(pin map, ribbon, cut lengths, parts), copies the sheets + CSVs to docs/report/toccata-v4/uno/, writes section.html,
assets.txt and meta.json here.  usage: python3 docs/report/toccata-v4/src/tabs/uno/build_section.py
"""
import html
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
ROOT = os.path.normpath(os.path.join(V4, "..", "..", ".."))
PCB = os.path.join(ROOT, "hardware", "pcb")
UNO = os.path.join(PCB, "uno")
sys.path.insert(0, os.path.join(PCB, "src"))
import uno_sheets as U  # noqa: E402

E = html.escape
DST = os.path.join(V4, "uno")


def tbl(head, rows, mono=()):
    h = "".join(f"<th>{E(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f'<td class="num">{E(str(c))}</td>' if i in mono else f"<td>{E(str(c))}</td>"
                                 for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def zbar(src):
    return ('<span class="zbar" role="group" aria-label="확대"><button type="button" data-z="1" aria-pressed="true">맞춤</button>'
            '<button type="button" data-z="2" aria-pressed="false">2배</button><button type="button" data-z="3" aria-pressed="false">3배</button>'
            f'<a class="mono" href="{src}" target="_blank" rel="noopener">크게 보기 (SVG) ↗</a></span>')


def fig(fid, code, meta, cap):
    src = "uno/" + meta["file"]
    return (f'<figure class="sheet csheet" id="{fid}"><div class="cap"><span><b>{E(code)} · {E(meta["title"])}</b> '
            f'<span class="mono">개정 {E(meta["rev"])}</span></span>{zbar(src)}</div>'
            f'<div class="dwimg"><img src="{src}" alt="{E(code + " " + meta["title"])}" loading="lazy" decoding="async" width="1680" height="1188"></div>'
            f'<figcaption class="small muted">{E(cap)}</figcaption></figure>')


def main():
    meta = json.load(open(os.path.join(UNO, "sheets.json"), encoding="utf-8"))
    bad = [k for k, v in meta.items() if v["errors"] or v["overlaps"]]
    if bad:
        raise SystemExit(f"uno sheets have problems: {bad} - run hardware/pcb/src/build_uno.py")
    os.makedirs(DST, exist_ok=True)
    assets = []
    for v in meta.values():
        shutil.copyfile(os.path.join(UNO, "schematic", v["file"]), os.path.join(DST, v["file"]))
        assets.append("uno/" + v["file"])
    for c in ("pins_uno.csv", "ribbon_uno.csv", "changes_uno.csv", "netlist_uno.csv"):
        shutil.copyfile(os.path.join(UNO, c), os.path.join(DST, c))
        assets.append("uno/" + c)
    B = U.power_budget()
    import sheets as _S
    PB = _S.budget()["run"]               # Pi version (SCH-06 budget): [light, heavy] hours
    cmp_rows = [
        ["건반 읽기", "옥타브마다 RP2040-Zero 1개 (8개)", "Arduino Uno 1개가 88건반 + 페달"],
        ["메인 프로그램 (음원·게임)", "Raspberry Pi 5 (본체 안)", "노트북 (macOS · Windows · Linux)"],
        ["화면", "7인치 터치 화면 (본체 위)", "노트북 화면"],
        ["연결", "USB 선 8개 → 허브 → Pi", "리본 10심 7개 → 버스 기판 UB → 우노 → USB 1개 → 노트북"],
        ["건반을 읽는 횟수 (계산)", "옥타브마다 약 9,000회/초", "약 600~700회/초 (ADC 하나를 나눠 씀)"],
        ["바닥까지 ADC 폭 (백·흑)", "722 · 906 코드 (12비트)", "약 166 · 212 코드 (10비트, 5 V)"],
        ["센서 전원", "3.3 V (제로마다)", "5.1 V (전지 → XL4016, UB에서 나눔)"],
        ["소리", "Pi → USB 동글 → J701 → 앰프", "노트북 이어폰 단자 → 3.5 mm 연장선 → J701 → 앰프"],
        ["전지로 치는 시간 (계산)", f"약 {PB[1]:.1f}~{PB[0]:.1f} h", f"약 {B['run'][1]:.0f}~{B['run'][0]:.0f} h (Pi·허브·화면이 빠짐)"],
        ["펌웨어 · 프로그램", "firmware/ (RP2040) · sw/ (Pi)", "firmware/uno · sw/toccata-bridge (노트북)"],
    ]
    pins = [["D0 · D1", "USB 시리얼 (노트북, 115200)", "—"]]
    pins += [[U.UNO_S[k], f"먹스 S{k} (7 포트 공통)", f"R80{k+1} 1 kΩ"] for k in range(4)]
    pins += [[U.UNO_EN[m], f"O{m} 먹스 EN (LOW = 켜짐)", f"R81{m} 1 kΩ"] for m in range(1, 8)]
    pins += [["A0", "SIG 버스 (먹스 7개 출력 합침)", "R841~R847 1 kΩ → R808 2.2 kΩ"],
             ["A1", "댐퍼 페달 (CC64)", "R805 1 kΩ · R806 100 kΩ · C801 100 nF"],
             ["A2", "버스 5 V 감시 (½ 분압, 약 2.55 V)", "R831 · R832 10 kΩ"],
             ["D13", "보드 LED (상태)", "—"], ["5V", "연결 금지 — +5V_B와 묶지 않음", "—"], ["GND", "UB GND (듀폰 2가닥)", "—"]]
    rib = [[str(i + 1), n, t] for i, (n, t) in enumerate(zip(U.BUS, U.BUS_TXT))]
    mods = [[f"O{m}", f"W80{m}", f"{U.CUTS[m]}", f"J80{m}", U.UNO_EN[m], f"{24+12*(m-1)}~{35+12*(m-1)}",
             {1: "C12~C14 → A0·A#0·B0", 7: "C12 → C8"}.get(m, "—")] for m in range(1, 8)]
    s = []
    s.append('<section class="page" id="p-uno" hidden aria-labelledby="uno-h">')
    s.append('<h2 id="uno-h">01b 아두이노 버전 — 노트북에서 실행</h2>')
    s.append('<p class="lede">Pi 버전(<a href="#circuit">01 회로도</a>, 개정 E)과 <b>건반·센서·출력물·전지·앰프·스피커는 같고</b>, '
             '건반을 읽는 칩과 메인 프로그램이 도는 곳만 다른 두 번째 구성입니다. RP2040-Zero 8개와 Raspberry Pi 5 대신 '
             'Arduino Uno 1개가 88건반과 페달을 모두 읽어 USB로 노트북에 보내고, 피아노 음원과 리듬게임은 노트북에서 돕니다. '
             '두 버전은 기판 몇 군데만 달라 어느 쪽으로든 다시 바꿀 수 있습니다.</p>')
    s.append('<p class="small muted">도면 U-01~U-04 (개정 U1, 2026-11-23) — 그린 선으로 연결을 다시 계산해 의도한 넷리스트와 맞춘 결과 연결 오류 0 · 글자 겹침 0. '
             '원본: <code>hardware/pcb/src/uno_sheets.py</code> → <code>hardware/pcb/uno/</code>. 아직 실제로 만들어 보지 않은 설계라 '
             '첫 조립 때 아래 ‘처음 켤 때 확인’을 지켜 주세요.</p>')
    s.append('<h3 id="uno-cmp">두 버전 비교</h3>')
    s.append(tbl(["", "라즈베리파이 버전 (개정 E)", "아두이노 버전 (U1)"], cmp_rows))
    s.append('<div class="note"><b>세기 표현은 Pi 버전보다 거칩니다.</b> 우노의 ADC 하나로 88개를 차례로 읽어 한 건반을 약 1.5 ms마다 봅니다. '
             '센 타건은 그 사이에 바닥까지 가므로, 펌웨어는 두 번 읽은 자석 위치 차이로 속도를 구합니다. 리듬게임과 시연에는 충분하지만 '
             '아주 여린 소리·아주 센 소리의 구분은 Pi 버전보다 덜 섬세합니다.</div>')
    s.append('<h3 id="uno-sys">연결 구조</h3>')
    s.append(fig("uno-u01", "U-01", meta["U-01"], "모듈 7개는 리본 10심으로 버스 기판 UB에 별 모양으로 모이고(Pi 버전의 USB 선·허브 자리), UB와 우노는 듀폰 점퍼로, 우노와 노트북은 USB 선 하나로 잇습니다. 전원·스피커 쪽은 Pi 버전 그대로입니다."))
    s.append('<h3 id="uno-sch">회로도</h3>')
    s.append(fig("uno-u02", "U-02", meta["U-02"], "옥타브 제어 기판: 제로를 빼고 먹스 EN을 GND 대신 J303.8에. 모듈 7장이 모두 같고, 번호는 UB 포트가 정합니다."))
    s.append(fig("uno-u03", "U-03", meta["U-03"], "버스 기판 UB + 우노: S0~S3 공통, EN 포트마다, SIG는 포트마다 1 kΩ를 거쳐 하나로 → A0. 페달은 A1, 버스 감시는 A2."))
    s.append(fig("uno-u04", "U-04", meta["U-04"], "전원·오디오: 5.1 V는 Pi·허브·화면 대신 UB(센서·먹스)로만. 소리는 노트북 이어폰 단자에서 J701로."))
    s.append('<h3 id="uno-pins">핀 · 선</h3>')
    s.append('<div class="u-grid"><div><h4>Arduino Uno 핀 배정</h4>' + tbl(["우노 핀", "쓰임", "UB 부품"], pins, mono=(0,)) + '</div>'
             '<div><h4>버스 리본 10심 (빨간 줄 = 1번)</h4>' + tbl(["핀", "넷", "뜻"], rib, mono=(0, 1)) + '</div></div>')
    s.append('<h4>모듈별 리본</h4>')
    s.append(tbl(["모듈", "리본", "자르는 길이 (mm)", "UB 포트", "우노 EN", "MIDI 음", "EXT"], mods, mono=(0, 1, 2, 3, 4, 5)))
    s.append('<p class="small muted">자르는 길이 = 그 모듈의 USB 선이 지나던 CAD 경로(허브 포트까지) + 80 mm를 50 mm 단위로 올림. 합 '
             f'{sum(U.CUTS.values())} mm → 10심 리본 약 4 m. 받기: <a href="uno/pins_uno.csv" download>pins_uno.csv</a> · '
             '<a href="uno/ribbon_uno.csv" download>ribbon_uno.csv</a> · <a href="uno/netlist_uno.csv" download>netlist_uno.csv</a></p>')
    s.append('<h3 id="uno-parts">바꾸는 부품</h3>')
    s.append('<div class="u-grid"><div><h4>새로 필요한 것</h4>' + tbl(["물건", "수량"], U.CHANGES_IN) + '</div>'
             '<div><h4>Pi 버전에서 빠지는 것</h4>' + tbl(["물건", "대신"], U.CHANGES_OUT) + '</div></div>')
    s.append('<p class="small muted">그대로 쓰는 것: 센서 기판 SB × 7, 끝 부속 EL·ER, 페달 센서 PS, MB 기판·먹스·J301·J302·R301~R304, '
             '전지·퓨즈·스위치·XL4016·앰프·스피커·잭, 모든 출력물. 가격은 아직 확인하지 않았습니다(<a href="uno/changes_uno.csv" download>changes_uno.csv</a>).</p>')
    s.append('<h3 id="uno-setup">세팅 순서</h3>')
    s.append('<ol class="u-steps">'
             '<li><b>옥타브 기판 바꾸기</b> — 제로를 헤더째 뽑고, 먹스 EN–GND 선을 끊어 J303.8로. 제로 자리에 J303 패드 10개를 두고 W80m 리본을 납땜(U-02).</li>'
             '<li><b>UB 만들기</b> — 만능기판 조각에 J801~J807 박스 헤더, 저항 19 + 2.2 kΩ + 10 kΩ 2개, 페달 부품(Pi 버전 PB에서 옮김), J809(U-03). 리본 UB 쪽 끝에 IDC 소켓을 눌러 끼우고 O 번호를 적습니다.</li>'
             '<li><b>전원</b> — XL4016 출력을 무부하로 5.10~5.15 V에 맞춘 뒤 W810으로 UB J809에(U-04). Pi·허브·화면 전원선은 만들지 않습니다.</li>'
             '<li><b>우노 펌웨어</b> — Arduino IDE에서 <code>firmware/uno/toccata_uno/toccata_uno.ino</code>를 열어 보드 “Arduino Uno”로 올립니다(<code>firmware/uno/README.md</code>).</li>'
             '<li><b>노트북 설치</b> — 저장소 루트에서 <code>./sw/setup-laptop.sh</code> (FluidSynth · Python 패키지).</li>'
             '<li><b>실행</b> — 우노 USB를 꽂고 전지 스위치를 켠 뒤(건반은 모두 올린 채) <code>./sw/toccata-bridge</code> → 다른 창에서 '
             '<code>./sw/toccata-midi synth</code>(피아노 소리) 또는 <code>./sw/toccata-game</code>(리듬게임). 브리지가 가상 MIDI 입력 “Toccata Uno”를 만듭니다.</li>'
             '</ol>')
    s.append('<h3 id="uno-check">처음 켤 때 확인</h3>')
    s.append('<ul>'
             '<li>켜는 순서: 노트북 USB → 전지 스위치. 끌 때는 반대. 버스가 꺼지면 우노가 A2로 알아채고 핀을 놓습니다.</li>'
             '<li>우노 5V 핀을 +5V_B에 잇지 않습니다. GND만 함께 씁니다.</li>'
             '<li>리본 1번(빨간 줄)이 J303.1·J80m.1(GND)인지 통전으로 확인한 뒤 꽂습니다.</li>'
             '<li>노트북을 충전하며 칠 때 ‘웅’ 소리가 나면 3.5 mm 접지 고리 차단기를 연장선에 끼우거나 충전기를 뺍니다.</li>'
             '<li>브리지가 포트를 열면 우노가 다시 시작하며 쉼 값을 읽습니다 — <b>브리지를 켤 때 건반을 모두 올려 둡니다.</b></li>'
             '<li>브리지 창에서 <code>s</code> + Enter로 건반별 쉼 값·남은 메모리·초당 스캔 수를 봅니다(실측 스캔 수는 여기서 처음 확인). 쉼 값이 5 V 기준 범위 밖이면 그 모듈 리본·센서를 확인합니다.</li>'
             '<li>Arduino IDE가 “메모리 부족” 경고를 띄웁니다(전역 변수 75 %). 정상이며, 남은 메모리는 <code>s</code> 상태표에 나옵니다.</li>'
             '<li>Pi 버전으로 되돌리기: 제로를 다시 꽂고 EN을 GND에, USB 선·허브·Pi를 다시 연결합니다. 펌웨어는 버전마다 따로라 서로 건드리지 않습니다.</li>'
             '</ul>')
    s.append('<div class="note">Pi 버전 기판 그대로도 노트북에서 돌릴 수 있습니다 — 허브 업스트림 선(W209)을 Pi 대신 노트북에 꽂으면 '
             '옥타브 보드 8개가 USB-MIDI로 바로 보이고(브리지 불필요), 같은 <code>./sw/toccata-midi synth</code> · <code>./sw/toccata-game</code>로 칩니다.</div>')
    s.append('</section>')
    with open(os.path.join(HERE, "section.html"), "w", encoding="utf-8") as f:
        f.write("\n".join(s) + "\n")
    with open(os.path.join(HERE, "assets.txt"), "w", encoding="utf-8") as f:
        f.write("# written by build_section.py\n" + "\n".join(assets) + "\n")
    with open(os.path.join(HERE, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"tab": "uno", "notes": "Arduino Uno + laptop version (U1). Source hardware/pcb/src/uno_sheets.py -> build_uno.py -> "
                   "hardware/pcb/uno; this script copies sheets + CSVs to uno/.", "generated": "2026-11-23"}, f, ensure_ascii=False, indent=1)
    print("uno tab:", len(assets), "assets")


if __name__ == "__main__":
    main()
