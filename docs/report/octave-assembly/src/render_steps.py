"""Step renders of one octave module (O4 parts from the CAD GLB) with OpenSCAD.

usage: python3 render_steps.py [step ...]   (no args = all)
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

S = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(S, "parts.json")))
OUT = os.path.join(S, "img")
os.makedirs(OUT, exist_ok=True)
X0 = 540.5                      # module left edge; renders are shifted so the module starts at x = 0


def has(*keys):
    return lambda i: any(k in i for k in keys)


FRAME = has("O4-FRAME")
PINS = has("balancepin")
KEYROD = has("keyrodSUS")
FELTS = has("whitefrontfelt", "blackfrontfelt", "keeperfelt")
BOARD = has("O4-E-MB", "O4-E-ZERO", "O4-E-MUX", "controlboardscrew")
SENSOR = has("O4-E-SB", "O4-SENSORBAR", "SBSCREW")
LEVER = has("O4-LEVER-", "O4-STEEL-", "O4-FELTSTRIP-", "O4-SPRING-")
LEVROD = has("leverrodD4", "O4-PLUG")
BLACK = lambda i: i.endswith("s") and has("O4-KEY-", "O4-CAPSTAN-", "O4-NUT-", "O4-MAGNET-", "O4-RESTFELT-")(i) and "PADBAR" not in i
WHITE = lambda i: (not i.endswith("s")) and has("O4-KEY-", "O4-CAPSTAN-", "O4-NUT-", "O4-MAGNET-", "O4-RESTFELT-")(i)
PADS = has("PADBAR", "upstoppad")
CURTAIN = has("O4-CURTAIN")
EVA = has("O4-EVA")
ALL = lambda i: True

# camera: eye xyz, centre xyz in module coords (x from the module's left edge)
FRONT = (-140, -260, 260, 85, 110, 30)
REAR = (330, 520, 300, 85, 110, 30)
BELOW = (-280, -360, -520, 90, 125, 20)
SIDE = (-230, 430, 260, 80, 150, 30)

# step: (cumulative parts, highlighted (new) parts, ghost parts, camera, size)
STEPS = {
    "s1_frame": (lambda i: FRAME(i) or PINS(i) or KEYROD(i) or FELTS(i), lambda i: PINS(i) or KEYROD(i) or FELTS(i), (), FRONT),
    "s2_board": (lambda i: FRAME(i) or BOARD(i), BOARD, (), BELOW),
    "s3_sensor": (lambda i: FRAME(i) or PINS(i) or KEYROD(i) or FELTS(i) or SENSOR(i), SENSOR, (), FRONT),
    "s4_levers": (lambda i: FRAME(i) or BOARD(i) or SENSOR(i) or LEVER(i), LEVER, ("O4-FRAME",), REAR),
    "s5_levrod": (lambda i: FRAME(i) or BOARD(i) or SENSOR(i) or LEVER(i) or LEVROD(i), LEVROD, ("O4-FRAME",), SIDE),
    "s6_black": (lambda i: not (WHITE(i) or PADS(i) or CURTAIN(i) or EVA(i)), BLACK, (), FRONT),
    "s7_white": (lambda i: not (PADS(i) or CURTAIN(i) or EVA(i)), WHITE, (), FRONT),
    "s8_pads": (lambda i: not (CURTAIN(i) or EVA(i)), PADS, ("O4-FRAME",), REAR),
    "s9_curtain": (lambda i: not EVA(i), lambda i: CURTAIN(i), (), FRONT),
    "s10_done": (ALL, EVA, (), BELOW),
}

def fade(c, k=0.55):
    """parts already in place: mixed toward light grey so the new parts of a step stand out"""
    r, g, b = (int(c[j:j + 2], 16) for j in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(v + (225 - v) * k) for v in (r, g, b))


def scad(sel, new, ghost, explode=None):
    out = []
    for i, p in sorted(P.items(), key=lambda kv: (kv[0] in ghost, kv[0])):   # ghosts last: they write depth
        if not sel(i):
            continue
        f = os.path.join(S, "parts", i + ".stl")
        c = p["color"]
        a = 1.0
        if i in ghost:
            a = 0.22
        t = (-X0, 0, 0)
        if explode and explode(i):
            dx, dy, dz = explode(i)
            t = (t[0] + dx, dy, dz)
        if not new(i):
            c = fade(c)
        line = 'translate([%.2f,%.2f,%.2f]) color("%s",%.2f) import("%s");' % (t[0], t[1], t[2], c, a, f)
        out.append(line)
    return "\n".join(out)


def run(name, src, cam, size=(1500, 950)):
    fn = os.path.join(OUT, name + ".scad")
    open(fn, "w").write(src)
    png = os.path.join(OUT, name + ".png")
    cmd = ["openscad", "-o", png, "--imgsize=%d,%d" % size, "--camera=" + ",".join(str(v) for v in cam),
           "--colorscheme=Tomorrow", "--projection=p", fn]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(name, r.stderr[-1500:])
    return png


def sub(prefix, note):
    return lambda i: any(i == "O4-%s-%s" % (k, note) for k in prefix)


KEYP = ("KEY", "CAPSTAN", "NUT", "MAGNET", "RESTFELT")
LEVP = ("LEVER", "STEEL", "FELTSTRIP", "SPRING")
KEY_EX = {"MAGNET": (0, 0, -14), "CAPSTAN": (0, 0, 16), "NUT": (16, 0, 0), "RESTFELT": (0, 0, -12)}
LEV_EX = {"STEEL": (0, 0, -30), "FELTSTRIP": (0, 0, -50), "SPRING": (18, 0, 0)}


def ex_of(table):
    return lambda i: table.get(i.split("-")[1], (0, 0, 0))


SUBS = {
    # white key D and black key D# from below-front-right (magnet pocket and nut slot face down / +x)
    "k_white": (sub(KEYP, "D"), ex_of(KEY_EX), (265, -235, -150, 35, 110, 28)),
    "k_black": (sub(KEYP, "Ds"), ex_of(KEY_EX), (270, -170, -150, 49, 120, 30)),
    "l_lever": (sub(LEVP, "D"), ex_of(LEV_EX), (230, 70, -60, 40, 175, 10)),
}


def job_sub(name):
    sel, ex, cam = SUBS[name]
    return run(name, scad(sel, lambda i: True, set(), ex), cam, size=(1100, 800))


def job(name):
    if name in SUBS:
        return job_sub(name)
    sel, new, ghost, cam = STEPS[name]
    return run(name, scad(sel, new, set(ghost)), cam)


if __name__ == "__main__":
    names = sys.argv[1:] or list(STEPS) + list(SUBS)
    with ThreadPoolExecutor(6) as ex:
        for png in ex.map(job, names):
            print(png)
