#!/usr/bin/env python3
"""Toccata v4 W1+ r4.4 -- the three printed bench tools (open issue 5), parametric from the single model.

    T1  bench jig  (base + loose stepped HEIGHT BLOCK)      -- sets the key height by rest-felt punchings
    T2  capstan bench gauge = printed DUMMY LEVER on the jig -- sets the capstan crown to the SETTLED rest crown (r4.4 fix 2b:
        the key on the jig sinks on its notch cloth / rest felt exactly as in the frame, so the target is the model's settled
        crown 30.89 / 30.91, not the key-frame z_c 31.0 - that turned every capstan out 0.11 / 0.09 mm)
    T3  balance-pin height gauge (press + go/no-go)         -- presses the D2 pin to z23.30 +- 0.1

Datums (never the desk):
  * T1/T2 reproduce the FRAME seats of one key: key rod K (bore = the frame cradle bottom), rest shelf z_shelf,
    lever rod L, all printed on a base whose underside is the frame underside (model z3.0 = print z0), so a jig
    printed like the frame rounds its heights to the same layers.
  * T3 registers on the balance-rail top (z_rail_low) and the rail front face (rail_front_y), i.e. the frame seat
    the pin is pressed into; its stop face is 4.30 above that.

Why a dummy lever (T2) and not the r4.3 '2.5 step on the beam top':
  * on the bench the key is FRONT-heavy: something must hold its tail on the rest shelf.  The rest felt is a soft
    Hertz contact (model K = 30 N/mm^1.5): pressing with a finger (0.3..5 N instead of the service ~1.06 N rest
    reaction) moves the key front by -0.15..+0.5 mm, i.e. up to 2 punchings.  The dummy lever hangs on the L rod stub
    and loads the capstan with the service lever moment (weight + torsion spring) -> the rest felt carries its
    service load, whatever the key.
  * the beam top z28.5 is a support-side (rough) surface of the printed key; the dummy lever instead reads the crown
    against the jig datum through a 5.5x (white) / 3.6x (black) lever amplification: 1/8 turn = 0.34 / 0.22 mm at the
    pointer blade, felt with a fingernail against a fixed ledge.  A calibration rod on two zero pads (z_c - 4.0)
    calibrates the whole jig + dummy chain.

Env MODEL_DIR (default ../ = the final/ folder that holds model_v4.py + geometry.json), OUT_DIR (default: this folder).
Writes (next to this file): tools_geometry.json, tools.md, stl/*.stl, scad/*.scad, png/*.png.
Coordinates: X = x - x_pin(key) (the key's balance-pin / block centre), y and z = model (z from the desk).
"""
import os, sys, json, math, subprocess, struct, decimal
sys.dont_write_bytecode = True          # never write caches into MODEL_DIR (backups stay untouched)

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.abspath(os.environ.get("MODEL_DIR", os.path.join(HERE, "..")))
OPENSCAD = os.environ.get("OPENSCAD", "/opt/homebrew/bin/openscad")
OUT = os.path.abspath(os.environ.get("OUT_DIR", HERE))          # outputs (default: next to this file)
sys.path.insert(0, MODEL_DIR)
import model_v4 as m          # noqa: E402

P = m.P
GEO = json.load(open(os.path.join(MODEL_DIR, "geometry.json")))
SOL = GEO["solved"]


# ============================================================================ number formatting (issue 5 rule)
def fmt(v, nd=2):
    """round half away from zero at the shown precision (one helper for every table)."""
    q = decimal.Decimal(1).scaleb(-nd)
    d = decimal.Decimal(repr(float(v))).quantize(q, rounding=decimal.ROUND_HALF_UP)
    s = format(d, "f")
    return "0" + s[2:] if s.startswith("-0") and float(d) == 0 else s


def r(v, nd=3):
    return float(fmt(v, nd))


# ============================================================================ model values the tools reproduce
K = tuple(P["K"])                      # key rod centre (y, z)
L = tuple(P["L"])                      # lever rod centre (y, z)
Z_DATUM = P["z_floor"][0]              # frame underside = jig underside (print z0)
Z_PLATE = P["z_floor"][1]              # frame floor top = jig plate top = height-block seat
Z_SHELF = SOL["z_shelf"]
CAPS = SOL["caps"]                     # capstan y white / black
Z_C_KEY = P["z_c"]                     # capstan crown top in the key frame (design pose, a = 0)


def _settled_crowns():
    """r4.4 fix 2b (verifier printables major): the key and the (dummy) lever settled on the jig = the frame seats: 4-DOF rest
    state of the representative keys (white D, black C#) -> crown top in the world."""
    keys_ = m.key_table(P)
    out = {}
    for n_, col_ in (("D", "white"), ("C#", "black")):
        A_ = m.Action(P, keys_[n_], CAPS[col_], SOL["levers"][n_])
        st_ = m.Dyn(A_, Z_SHELF).run(300.0)["state"]
        out[col_] = dict(crown=m.key_point_world(A_, st_, (CAPS[col_], Z_C_KEY))[1], A=A_, st=st_, key=n_)
    return out


SETTLE = _settled_crowns()
# one plane for both colours (0.01 grid): the dummy-lever floor and the zero pads' rod top
Z_C = round((SETTLE["white"]["crown"] + SETTLE["black"]["crown"]) / 2, 2)
TOP_W, TOP_B = P["key_top"], P["black_top"]
Y_FRONT_W, Y_FRONT_B = 0.0, P["y_black_front"] + 1.0
PIN_Y, PIN_D = P["pin_y"], P["pin_d"]
PIN_TOP = P["block_step_z"] + P["pin_engage"]
PIN_LEN = P["pin_len"]
RAIL_Y0 = P["rail_front_y"]
Z_RAIL = max(max(z for _, z in p["side"]) for p in GEO["parts"] if p["part"].startswith("balance rail (lowered"))
RAIL_LIP, RAIL_H, _ = m.rail_saddle(P)          # saddle lip z, half-width at the lip
RIDGE_Y0 = K[0] - (RAIL_H + 0.8)                 # frame cradle ridge starts here (y)
# r4.4 fix 2: the rail is pocketed (lower) behind y_pocket under the black-key blocks; T3's rear foot stays in front of it
_POCK = ((GEO.get("r44") or {}).get("key_shift") or {}).get("pocket") or {}
Y_POCKET = min([q["y"] for q in _POCK.values() if q] + [1e9])
REST_Y = P["rest_pad_y"]
SHELF_Y0 = P["shelf_y"][0]
Y_TAIL_END = P["y_tail_end"]
Y_KEY_REAR = P["y_skin_end"]
BLACK_STEP = P["black_skin_step"]
STEEL = dict(y0=P["y_steel_front"], y1=P["y_steel_front"] + P["steel_len"], z0=P["z_sb"], z1=P["z_st"],
             w=P["steel_w"], m=P["steel_w"] * P["steel_h"] * P["steel_len"] * m.RHO_ST)
CLR = P["cradle_clear"]                          # 1.3 nominal = 1.0 after +-0.3 FDM
TOL = m.TOL
PUNCH = 0.1                                      # paper punching under the rest felt
TURN8 = 0.5 / 8                                  # M3 pitch 0.5 -> 1/8 turn
HB_WIN = 0.15                                    # height-block window (>= half a punching step at the front)
PIN_TOL = 0.1                                    # P32: pin top z23.30 +- 0.1
RHO = m.RHO_PETG


def key_offsets():
    """per key: balance-pin x and the key envelopes relative to it (X = x - x_pin)."""
    keys = m.key_table(P)
    out = {}
    for n in m.ORDER:
        kd = keys[n]
        b0, b1 = m.block_x(P, kd)
        xp = (b0 + b1) / 2
        xl = SOL["levers"][n]
        tw = m.tail_w(P, kd["black"])
        out[n] = dict(black=kd["black"], x_pin=xp, head=(kd["head"][0] - xp, kd["head"][1] - xp),
                      tail=(kd["tail"][0] - xp, kd["tail"][1] - xp), block=(b0 - xp, b1 - xp), lever=xl - xp,
                      beam=(xl - xp - P["beam_w"] / 2, xl - xp + P["beam_w"] / 2),
                      thin_tail=(xl - xp - tw / 2, xl - xp + tw / 2),
                      y_cap=CAPS["black" if kd["black"] else "white"])
    return out


KO = key_offsets()


def all_key_parts():
    """side_rest polygons of every key the jig must take: the 12 module keys + the end-part keys (A0 A#0 B0 C8), X
    relative to that key's balance pin (from the fixed 'balance pin D2 <key>' prisms)."""
    srcs = [GEO["parts"]] + [GEO["end_parts"][sd]["parts"] for sd in ("left", "right")]
    out = {}
    for parts in srcs:
        pins = {p["part"][len("balance pin D2 "):]: (p["x"][0] + p["x"][1]) / 2 for p in parts if p["part"].startswith("balance pin D2 ")}
        for p in parts:
            b = p["body"]
            if not b.startswith("key ") or "side_rest" not in p or isinstance(p["side_rest"], str):
                continue
            n = b[4:]
            if n not in pins:
                continue
            xp = pins[n]
            d = out.setdefault(n, dict(x_pin=xp, parts=[]))
            # r4.4 fix 2b: the key as it settles on the jig seats (notch cloth on the K rod, rest felt on the shelf, lever on the
            # capstan) - the colour's settled planar state applied to the design-pose outline
            sc_ = SETTLE["black" if "#" in n else "white"]
            d["parts"].append(dict(part=p["part"], X=(p["x"][0] - xp, p["x"][1] - xp), poly=[tuple(m.key_point_world(sc_["A"], sc_["st"], q)) for q in p["side_rest"]]))
    return out


KEYS_ALL = all_key_parts()


def _env(y0, y1, names=None):
    lo, hi = 1e9, -1e9
    for n, d in KEYS_ALL.items():
        for kp in d["parts"]:
            ys = [q[0] for q in kp["poly"]]
            if max(ys) < y0 or min(ys) > y1 or (names and kp["part"] not in names):
                continue
            lo, hi = min(lo, kp["X"][0]), max(hi, kp["X"][1])
    return lo, hi


ENV = dict(
    at_rod=max(abs(v) for v in _env(RAIL_Y0, Y_KEY_REAR)),            # every key part over the rod / rail zone
    back=_env(Y_KEY_REAR + 0.01, Y_TAIL_END + 0.5),                         # beams, thin tails, rest felts, capstan heads
    head=max(abs(v) for v in _env(-1.0, P["y_head"], ("skin head",))),
)
ENV["back_abs"] = max(abs(ENV["back"][0]), abs(ENV["back"][1]))
END_CAPS = {k: v for sd in ("left", "right") for k, v in SOL["end_parts"][sd]["caps"].items()}


# ============================================================================ service loads (what the dummy lever must reproduce)
def service_loads():
    keys = m.key_table(P)
    res = {}
    for n, col in (("D", "white"), ("C#", "black")):
        A = m.Action(P, keys[n], CAPS[col], SOL["levers"][n])
        b = SOL["b_rest_w" if col == "white" else "b_rest_b"]            # rad
        com = m.rot(A.lev.com, L, -b)
        M = A.lev.m * m.G * (L[0] - com[0]) + P["spring_kt"] * (b - math.radians(P["spring_free_deg"]))
        Fc = M / (L[0] - CAPS[col])
        Wk = A.mk * m.G
        yr = sum(REST_Y) / 2
        R = (Fc * (CAPS[col] - K[0]) - Wk * (K[0] - A.ck[0])) / (yr - K[0])
        res[col] = dict(key=n, M=M, F_cap=Fc, lever_m=A.lev.m, key_m=A.mk, key_com=A.ck, rest_R=R, notch_N=Fc + Wk - R, b_rest=b)
    return res


SERVICE = service_loads()


def front_shift(col, F_cap):
    """key-front height change (mm) when the capstan force is F_cap instead of the service value (felt + notch cloth
    static Hertz laws of the model)."""
    s = SERVICE[col]
    yr = sum(REST_Y) / 2
    yf = Y_FRONT_B if col == "black" else Y_FRONT_W
    Wk = s["key_m"] * m.G

    def zf(Fc):
        R = (Fc * (CAPS[col] - K[0]) - Wk * (K[0] - s["key_com"][0])) / (yr - K[0])
        N = Fc + Wk - R
        df = m.static_set(m.FELT_EFF["rest"], R)
        dn = m.static_set(m.FELT_EFF["cloth"], N)
        k = (yf - K[0]) / (yr - K[0])
        return -dn + (dn - df) * k
    return zf(F_cap) - zf(s["F_cap"])


# ============================================================================ primitive prisms (the single geometry source)
def rect(a0, a1, b0, b1):
    return [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]


def circ(c, rr, n=48):
    return [(c[0] + rr * math.cos(2 * math.pi * i / n), c[1] + rr * math.sin(2 * math.pi * i / n)) for i in range(n)]


def teardrop(c, rr, n=40):
    """horizontal bore printable without support: lower 3/4 circle + 45 deg roof to an apex at rr*sqrt(2) above c."""
    pts = [(c[0] + rr * math.cos(math.radians(a)), c[1] + rr * math.sin(math.radians(a))) for a in [135 + 270 * i / n for i in range(n + 1)]]
    pts.append((c[0], c[1] + rr * math.sqrt(2)))
    return pts


class Tool:
    """prisms in USE coordinates.  kind px: poly (y,z) extruded over X [a0,a1]; pz: poly (X,y) over z [a0,a1];
    py: poly (X,z) over y [a0,a1].  op 'add' / 'sub'.  'ref' prisms (steel, rods, pins) are drawn and checked but not printed."""

    def __init__(self, key, name_ko):
        self.key, self.name_ko = key, name_ko
        self.prims, self.texts = [], []

    def add(self, kind, name, a0, a1, poly, op="add", **kw):
        d = dict(kind=kind, name=name, a0=float(a0), a1=float(a1), poly=[(float(a), float(b)) for a, b in poly], op=op)
        d.update(kw)
        self.prims.append(d)
        return d

    def text(self, s, size, xform, depth=0.6, mode="emboss", halign="center"):
        self.texts.append(dict(s=s, size=size, xform=xform, depth=depth, mode=mode, halign=halign))

    # ---- outlines for the drafter
    def side(self, ops=("add",)):
        out = []
        for p in self.prims:
            if p["op"] not in ops:
                continue
            if p["kind"] == "px":
                poly = p["poly"]
            elif p["kind"] == "pz":
                ys = [b for _, b in p["poly"]]
                poly = rect(min(ys), max(ys), p["a0"], p["a1"])
            else:
                zs = [b for _, b in p["poly"]]
                poly = rect(p["a0"], p["a1"], min(zs), max(zs))
            out.append(dict(name=p["name"], op=p["op"], x=self.xr(p), side=[[r(a), r(b)] for a, b in poly]))
        return out

    def plan(self, ops=("add",)):
        out = []
        for p in self.prims:
            if p["op"] not in ops:
                continue
            if p["kind"] == "pz":
                poly = p["poly"]
            elif p["kind"] == "px":
                ys = [a for a, _ in p["poly"]]
                poly = rect(p["a0"], p["a1"], min(ys), max(ys))
            else:
                xs = [a for a, _ in p["poly"]]
                poly = rect(min(xs), max(xs), p["a0"], p["a1"])
            out.append(dict(name=p["name"], op=p["op"], z=self.zr(p), plan=[[r(a), r(b)] for a, b in poly]))
        return out

    def front(self, ops=("add",)):
        """r4.5 fix round (drafter T09): the (X, z) outline of every prism - a 'py' prism's own polygon (true profile, e.g. the
        tapered readout ledge post), others as their X x z bounding rectangle; with the prism's y range."""
        out = []
        for p in self.prims:
            if p["op"] not in ops:
                continue
            if p["kind"] == "py":
                poly, yr_ = p["poly"], [r(p["a0"]), r(p["a1"])]
            elif p["kind"] == "px":
                zs = [b for _, b in p["poly"]]
                poly, yr_ = rect(p["a0"], p["a1"], min(zs), max(zs)), [r(min(a for a, _ in p["poly"])), r(max(a for a, _ in p["poly"]))]
            else:
                xs = [a for a, _ in p["poly"]]
                poly, yr_ = rect(min(xs), max(xs), p["a0"], p["a1"]), [r(min(b for _, b in p["poly"])), r(max(b for _, b in p["poly"]))]
            out.append(dict(name=p["name"], op=p["op"], kind=p["kind"], y=yr_, front=[[r(a), r(b)] for a, b in poly]))
        return out

    @staticmethod
    def xr(p):
        if p["kind"] == "px":
            return [r(p["a0"]), r(p["a1"])]
        xs = [a for a, _ in p["poly"]]
        return [r(min(xs)), r(max(xs))]

    @staticmethod
    def zr(p):
        if p["kind"] == "pz":
            return [r(p["a0"]), r(p["a1"])]
        zs = [b for _, b in p["poly"]]
        return [r(min(zs)), r(max(zs))]


DIMS = []


def dim(tool, item, value, unit="mm", basis="", note=""):
    i = "T%02d" % (len(DIMS) + 1)
    DIMS.append(dict(id=i, tool=tool, item=item, value=value, unit=unit, basis=basis, note=note))
    return i


# ============================================================================ T1 bench jig
def build_jig():
    J = Tool("bench_jig", "벤치 지그 (받침)")
    Xw = 36.0                                   # half width of the base
    y_front, y_rear = -8.0, 214.0
    J.add("pz", "base plate", Z_DATUM, Z_PLATE, rect(-Xw, Xw, y_front, y_rear))
    # --- rail block = frame balance rail at the pin (top z_rail_low, front face rail_front_y), pin boss, T3 seat
    y_rail1 = round(RIDGE_Y0 - 0.04, 2)
    J.add("px", "rail block (frame rail top / front face)", -Xw, Xw, rect(RAIL_Y0, y_rail1, Z_PLATE, Z_RAIL))
    PIN_HOLE = 1.9
    J.add("pz", "balance pin hole D%.1f (press, like the frame)" % PIN_HOLE, Z_RAIL - (PIN_LEN - (PIN_TOP - Z_RAIL)) - 1.0, Z_RAIL + 0.01,
          circ((0.0, PIN_Y), PIN_HOLE / 2, 24), op="sub")
    J.add("pz", "balance pin D2x12 (spare, pressed with T3)", PIN_TOP - PIN_LEN, PIN_TOP, circ((0.0, PIN_Y), PIN_D / 2, 24), op="ref")
    # --- K posts: rod stub bore centre = K (the frame cradle bottom K_z - 2.0), outside every key tail + 1.3
    kx0 = math.ceil((ENV["at_rod"] + CLR) * 10) / 10
    kx1 = kx0 + 4.0
    k_top = 26.0
    J.add("px", "K post L", -kx1, -kx0, rect(y_rail1, K[0] + 2.6, Z_PLATE, k_top))
    J.add("px", "K post R", kx0, kx1, rect(y_rail1, K[0] + 2.6, Z_PLATE, k_top))
    J.add("px", "K bore D3.9 print -> D4.0 drill (right one blind)", -kx1 - 0.01, kx1 - 1.0, teardrop(K, 1.95), op="sub")
    J.add("px", "K rod stub D4 SUS304 (cut %s)" % fmt(2 * kx1 - 1.0, 1), -kx1, kx1 - 1.0, circ(K, P["rod_k"] / 2, 32), op="ref")
    # --- rest shelf (frame shelf top z_shelf) under the rest felt of every key
    sx = math.ceil(ENV["back_abs"] + 2.0)
    J.add("px", "rest shelf (top = frame shelf)", -sx, sx, rect(SHELF_Y0, 200.0, Z_PLATE, Z_SHELF))
    # --- L posts: lever rod stub bore centre = L; outside the dummy hub (+-6.3) and the black thin tails
    hub_w = 6.3
    lx0, lx1 = hub_w + 0.5, hub_w + 4.5
    ly0 = round(max(Y_TAIL_END + 1.2, L[0] - 3.05), 2)
    ly1 = L[0] + 4.25
    l_top = L[1] + 3.5
    J.add("px", "L post L", -lx1, -lx0, rect(ly0, ly1, Z_PLATE, l_top))
    J.add("px", "L post R", lx0, lx1, rect(ly0, ly1, Z_PLATE, l_top))
    J.add("px", "L bore D3.9 print -> D4.0 drill (right one blind)", -lx1 - 0.01, lx1 - 1.0, teardrop(L, 1.95), op="sub")
    J.add("px", "L rod stub D4 SUS304 (cut %s)" % fmt(2 * lx1 - 1.0, 1), -lx1, lx1 - 1.0, circ(L, P["rod_L"] / 2, 32), op="ref")
    # --- calibration zero pads: a D4 rod laid across them has its top at z_c (crown height), at both capstan y
    z_zero = Z_C - P["rod_k"]
    px0, px1 = math.ceil((ENV["back_abs"] + 2.0) * 10) / 10, None
    px1 = px0 + 4.0
    for col in ("white", "black"):
        yc = CAPS[col]
        prof = [(yc - 3.2, Z_PLATE), (yc + 3.2, Z_PLATE), (yc + 3.2, z_zero + 1.0), (yc + 2.3, z_zero + 1.0), (yc + 2.3, z_zero),
                (yc - 2.3, z_zero), (yc - 2.3, z_zero + 1.0), (yc - 3.2, z_zero + 1.0)]
        J.add("px", "zero pad %s L" % col, -px1, -px0, prof)
        J.add("px", "zero pad %s R" % col, px0, px1, prof)
    cal = 2 * kx1 - 1.0                      # same cut length as the K stub
    J.add("px", "calibration rod D4 (cut %s) on the white zero pads" % fmt(cal, 1), -cal / 2, cal / 2, circ((CAPS["white"], z_zero + 2.0), 2.0, 32), op="ref")
    return J, dict(stub_K=2 * kx1 - 1.0, stub_L=2 * lx1 - 1.0, cal=cal, Xw=Xw, y_front=y_front, y_rear=y_rear, y_rail1=y_rail1, PIN_HOLE=PIN_HOLE, kx=(kx0, kx1), k_top=k_top, sx=sx,
                   lx=(lx0, lx1), ly=(ly0, ly1), l_top=l_top, hub_w=hub_w, z_zero=z_zero, pad_x=(px0, px1))


# ============================================================================ T2 capstan bench gauge (dummy lever)
def build_dummy(jd):
    D = Tool("capstan_gauge", "캡스턴 벤치 게이지 (가짜 레버)")
    hw = jd["hub_w"]
    c = 0.2                                              # steel pocket clearance per side (FDM: pocket prints ~0.1 small)
    s = STEEL
    y_front = round(Y_KEY_REAR + 1.8, 2)                 # 1.8 behind the key's rear lip
    pk = dict(y0=s["y0"] - c, y1=s["y1"] + c, z0=s["z0"] - c, z1=s["z1"] + c)
    z_top = pk["z1"] + 1.2
    y_rear = pk["y1"] + 1.2
    # outer body (X -hw..hw): walls round the pocket, floor = the lever felt plane z_c
    body = [(y_front, Z_C), (y_rear + 4.0, Z_C), (L[0] - 3.2, Z_C), (L[0] - 3.2, L[1] + 6.5), (y_rear, L[1] + 8.5),
            (y_rear, z_top), (y_front, z_top)]
    D.add("px", "body (pocket walls, floor = felt plane z_c)", -hw, hw, body)
    D.add("px", "hub R4.6", -hw, hw, circ(L, 4.6, 48))
    D.add("px", "hub bore D3.9 print -> D4.0 drill", -hw - 0.01, hw + 0.01, circ(L, 1.95, 32), op="sub")
    # pocket open on +X (print top), back wall at -X
    pk_x0 = hw - (s["w"] + 0.4)
    D.add("px", "steel pocket (open on +X)", pk_x0, hw + 0.01, rect(pk["y0"], pk["y1"], pk["z0"], pk["z1"]), op="sub")
    D.add("px", "snap lip top (0.4 over the steel)", hw - 0.6, hw, rect(pk["y0"] + 2.0, pk["y1"] - 2.0, pk["z1"] - 0.4, pk["z1"]), op="add_post")
    D.add("px", "snap lip bottom", hw - 0.6, hw, rect(pk["y0"] + 2.0, pk["y1"] - 2.0, pk["z0"], pk["z0"] + 0.4), op="add_post")
    D.add("px", "steel SS400 9x19x40 (the lever's own block)", pk_x0 + 0.2, pk_x0 + 0.2 + s["w"], rect(s["y0"], s["y1"], s["z0"], s["z1"]), op="ref")
    # beak over the key tail (clear of the black key top) carrying the pointer blade
    z_beak0 = TOP_B + 2.0
    z_led = 65.5
    y_blade = (119.0, 123.0)
    # r4.5 fix round (drafter): the handle bar and its web are separate prisms, so the beak's own underside is z_beak0 (T20) and
    # only the web reaches the body top (0.01 into it for the union)
    beak = [(y_blade[0], z_beak0), (y_front + 7.2, z_beak0), (y_front + 7.2, z_led), (y_blade[0], z_led)]
    D.add("px", "beak (handle) over the key tail", -hw, hw, beak)
    D.add("px", "beak web to the body top (0.01 into the body)", -hw, hw, rect(y_front, y_front + 7.2, z_top - 0.01, z_beak0 + 0.01))
    blade_x1 = hw + 5.5
    D.add("px", "pointer blade (top = ledge at b = 0)", hw - 0.01, blade_x1, rect(y_blade[0], y_blade[1], z_led - 1.6, z_led))
    return D, dict(y_front=y_front, pk=pk, pk_x0=pk_x0, z_top=z_top, y_rear=y_rear, z_beak0=z_beak0, z_led=z_led,
                   y_blade=y_blade, blade_x1=blade_x1, hw=hw)


def add_readout_and_park(J, jd, dd):
    """ledge post beside the blade + parking post that holds the flipped dummy (computed)."""
    x0 = dd["blade_x1"] + 1.1
    y0, y1 = dd["y_blade"][0] - 0.6, dd["y_blade"][1] + 0.6
    z1 = dd["z_led"]
    J.add("py", "readout ledge post (top = blade top at b = 0)", y0, y1,
          [(x0, Z_PLATE), (x0 + 17.0, Z_PLATE), (x0 + 8.0, z1 - 10.0), (x0 + 8.0, z1), (x0, z1)])
    jd["ledge"] = dict(x0=x0, y=(y0, y1), z=z1)


def dummy_side_polys(D, b=0.0):
    out = []
    for p in D.prims:
        if p["op"] == "add" and p["kind"] == "px" and "blade" not in p["name"]:
            out.append([m.rot(q, L, -b) for q in p["poly"]])
    return out


def _dense(poly, step=0.5):
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        k = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        out += [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
    return out


def find_parking(J, D, jd, target_deg=115.0):
    """parking post behind L: the dummy flipped front-up past vertical first touches the post top at ~target_deg,
    with its COM behind L (it stays there by itself).  h(b) = lowest dummy point over the post's y span."""
    import numpy as np
    pts = np.array([q for pg in dummy_side_polys(D, 0.0) for q in _dense(pg)])
    y0, y1 = L[0] + 5.25, L[0] + 9.75
    bs = np.radians(np.arange(60.0, 200.0, 0.1))
    h = []
    for b in bs:
        c, s_ = math.cos(-b), math.sin(-b)
        dy, dz = pts[:, 0] - L[0], pts[:, 1] - L[1]
        y = L[0] + dy * c - dz * s_
        z = L[1] + dy * s_ + dz * c
        sel = (y >= y0) & (y <= y1)
        h.append(z[sel].min() if sel.any() else 1e9)
    h = np.array(h)
    best = None
    for zt in np.arange(10.0, 60.0, 0.5):
        idx = np.nonzero(h <= zt)[0]
        if len(idx) == 0:
            continue
        bt = bs[idx[0]]
        if best is None or abs(math.degrees(bt) - target_deg) < abs(math.degrees(best[1]) - target_deg):
            best = (float(zt), float(bt))
    zt, bt = best
    J.add("px", "parking post (flipped dummy leans on it)", -4.0, 4.0, rect(y0, y1, Z_PLATE, zt))
    jd["park"] = dict(y=(y0, y1), z=zt, b=bt)


# ============================================================================ T1b height block (loose, part of the jig set)
def build_height_block():
    H = Tool("height_block", "높이 블록 (지그와 한 벌, 따로 출력)")
    t = 10.0
    lands = [("W+", 0.0, 8.0, TOP_W + HB_WIN), ("W-", 8.0, 16.0, TOP_W - HB_WIN),
             ("B+", 18.0, 26.0, TOP_B + HB_WIN), ("B-", 26.0, 34.0, TOP_B - HB_WIN)]
    H.add("px", "web", 0.0, t, rect(16.0 - 0.01, 18.0 + 0.01, Z_PLATE, TOP_W - 1.5))
    for nm, v0, v1, zt in lands:
        H.add("px", "land %s top z%s" % (nm, fmt(zt, 2)), 0.0, t, rect(v0, v1, Z_PLATE, zt))
    return H, dict(t=t, lands=lands)


# ============================================================================ T3 balance-pin height gauge
def build_pin_gauge():
    G = Tool("pin_gauge", "밸런스 핀 높이 게이지")
    u0, u1 = -26.0, 26.0
    ch = (PIN_Y - 1.45, PIN_Y + 1.45)          # channel 2.9 wide (pin 2.0 + 0.45 per side; FDM -0.3 still 2.6)
    v_front, v_rear = RAIL_Y0 - 1.8, round(RIDGE_Y0 - 0.44, 2)
    land_f = (RAIL_Y0, ch[0])
    z_land = Z_RAIL
    z_ch = PIN_TOP + 1.2                        # open channel over pressed neighbours (1.2 above their tops)
    z_top = z_land + 14.0
    fence = (RAIL_Y0 - 1.8, RAIL_Y0 - 0.3)
    G.add("px", "front body (y%s-%s, in front of the rail face)" % (fmt(fence[1], 2), fmt(RAIL_Y0, 2)), u0, u1, rect(fence[1], RAIL_Y0 + 0.01, z_land, z_top))
    G.add("px", "front foot = land on the rail top (y%s-%s, T24)" % (fmt(RAIL_Y0, 2), fmt(ch[0], 2)), u0, u1, rect(RAIL_Y0, ch[0], z_land, z_top))
    y_land_r = min(v_rear, round(Y_POCKET - 0.1, 2))     # r4.4 fix 2: the rear foot ends 0.1 in front of the rail pockets (white and black blocks)
    G.add("px", "rear body + land", u0, u1, rect(ch[1], y_land_r, z_land, z_top))
    if y_land_r < v_rear:
        G.add("px", "rear body (0.3 above the rail over the rail pockets from y%s)" % fmt(Y_POCKET, 1), u0, u1, rect(y_land_r - 0.01, v_rear, z_land + 0.3, z_top))
    G.add("px", "roof over the open channel", u0, u1, rect(ch[0] - 0.01, ch[1] + 0.01, z_ch, z_top))
    G.add("px", "fence (registers on the rail front face, 0.3 gap)", u0, u1, rect(fence[0], fence[1] + 0.01, z_land - 4.0, z_top))
    G.add("px", "press block (stop face at the pin top)", -3.0, 3.0, rect(ch[0] - 0.01, ch[1] + 0.01, z_land, z_ch + 0.01))
    G.add("pz", "press bore D2.5 (stop = pin top z%s)" % fmt(PIN_TOP, 2), z_land - 0.01, PIN_TOP, circ((0.0, PIN_Y), 1.25, 32), op="sub")
    go, nogo = PIN_TOP + PIN_TOL, PIN_TOP - PIN_TOL
    for sgn, side in ((1, "right"), (-1, "left")):
        a = sorted((sgn * 20.0, sgn * 26.0))
        b = sorted((sgn * 16.0, sgn * 20.0))
        G.add("px", "GO roof %s (pin top must pass under z%s)" % (side, fmt(go, 2)), a[0], a[1], rect(ch[0] - 0.01, ch[1] + 0.01, go, z_ch + 0.01))
        G.add("px", "NO-GO roof %s (pin top must stop at z%s)" % (side, fmt(nogo, 2)), b[0], b[1], rect(ch[0] - 0.01, ch[1] + 0.01, nogo, z_ch + 0.01))
    G.add("pz", "balance pin D2 (target)", PIN_TOP - PIN_LEN, PIN_TOP, circ((0.0, PIN_Y), 1.0, 24), op="ref")
    return G, dict(u=(u0, u1), ch=ch, v=(v_front, v_rear), fence=fence, land_f=land_f, land_r=(ch[1], y_land_r), z_land=z_land, z_ch=z_ch,
                   z_top=z_top, go=go, nogo=nogo)


# ============================================================================ OpenSCAD writer
def scad_prim(p, eps=0.0):
    pts = ",".join("[%.4f,%.4f]" % q for q in p["poly"])
    h = p["a1"] - p["a0"]
    body = "linear_extrude(height=%.4f) polygon(points=[%s]);" % (h, pts)
    if p["kind"] == "px":        # (a,b)=(y,z) extruded along X from a0
        return "multmatrix([[0,0,1,%.4f],[1,0,0,0],[0,1,0,0],[0,0,0,1]]) %s" % (p["a0"], body)
    if p["kind"] == "pz":
        return "translate([0,0,%.4f]) %s" % (p["a0"], body)
    # py: (a,b)=(X,z) extruded along y from a1 down to a0 (det +1 map)
    return "multmatrix([[1,0,0,0],[0,0,-1,%.4f],[0,1,0,0],[0,0,0,1]]) %s" % (p["a1"], body)


def scad_text(t):
    ext = "linear_extrude(height=%.3f) text(\"%s\", size=%.2f, font=\"Arial:style=Bold\", halign=\"%s\", valign=\"center\");" % (
        t["depth"] + (0.01 if t["mode"] == "deboss" else 0.0), t["s"], t["size"], t["halign"])
    return "multmatrix(%s) %s" % (json.dumps(t["xform"]), ext)


def write_scad(T, xform, path):
    adds = [scad_prim(p) for p in T.prims if p["op"] == "add"]
    post = [scad_prim(p) for p in T.prims if p["op"] == "add_post"] + [scad_text(t) for t in T.texts if t["mode"] == "emboss"]
    subs = [scad_prim(p) for p in T.prims if p["op"] == "sub"] + [scad_text(t) for t in T.texts if t["mode"] == "deboss"]
    s = "// %s (%s) -- generated by make_tools.py from %s; USE coordinates mapped to the print bed\n" % (T.key, T.name_ko, MODEL_DIR)
    s += "$fn=48;\nmultmatrix(%s) union(){\n difference(){\n  union(){\n   %s\n  }\n  %s\n }\n %s\n}\n" % (
        json.dumps(xform), "\n   ".join(adds), "\n  ".join(subs), "\n ".join(post))
    open(path, "w").write(s)


def run_scad(scad, stl):
    r_ = subprocess.run([OPENSCAD, "--backend", "Manifold", "-o", stl, scad], capture_output=True, text=True)
    if r_.returncode != 0 or not os.path.exists(stl):
        raise RuntimeError("openscad failed for %s:\n%s" % (scad, r_.stderr[-2000:]))
    return r_.stderr


def render_png(scad, png, camera=None):
    args = [OPENSCAD, "--backend", "Manifold", "--render", "-o", png, "--imgsize=1100,800", "--colorscheme=Tomorrow", "--projection=p"]
    if camera:
        args += ["--camera=" + camera]
    else:
        args += ["--viewall", "--autocenter"]
    subprocess.run(args + [scad], capture_output=True, text=True)


def read_stl(path):
    data = open(path, "rb").read()
    tris = []
    if data[:5] == b"solid" and b"facet" in data[:400]:
        v = []
        for line in data.decode("ascii", "ignore").splitlines():
            line = line.strip()
            if line.startswith("vertex"):
                v.append(tuple(float(a) for a in line.split()[1:4]))
                if len(v) == 3:
                    tris.append(v)
                    v = []
    else:
        n = struct.unpack("<I", data[80:84])[0]
        for i in range(n):
            o = 84 + i * 50
            f = struct.unpack("<12f", data[o:o + 48])
            tris.append([f[3:6], f[6:9], f[9:12]])
    return tris


def mesh_props(tris):
    V = 0.0
    C = [0.0, 0.0, 0.0]
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for a, b, c in tris:
        v = (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        V += v
        for k in range(3):
            C[k] += v * (a[k] + b[k] + c[k]) / 4.0
            lo[k] = min(lo[k], a[k], b[k], c[k])
            hi[k] = max(hi[k], a[k], b[k], c[k])
    return V, [c_ / V for c_ in C], lo, hi


# ============================================================================ checks against the model keys / frame
def key_side_parts():
    return {n: d["parts"] for n, d in KEYS_ALL.items()}


DESIGNED = {("rest felt", "rest shelf"), ("balance block", "K rod stub"), ("balance block", "balance pin D2x12"),
            ("capstan head", "body (pocket walls")}


def designed(a, b):
    return any(a.startswith(x) and b.startswith(y) for x, y in DESIGNED)


def clearance_sweep(tools):
    """min side-view distance between each tool prism (add + ref rods/pins) and every module key at rest, for
    prisms that overlap in X (key parts shifted to the jig frame)."""
    KP = key_side_parts()
    res = {}
    contact = {}
    for tname, T in tools:
        for p in T.prims:
            if p["op"] == "sub" or p["kind"] not in ("px", "pz", "py") or p["name"].startswith("calibration rod"):
                continue
            xr_ = Tool.xr(p)
            if p["kind"] == "px":
                poly = p["poly"]
            elif p["kind"] == "pz":
                ys = [b for _, b in p["poly"]]
                poly = rect(min(ys), max(ys), p["a0"], p["a1"])
            else:
                zs = [b for _, b in p["poly"]]
                poly = rect(p["a0"], p["a1"], min(zs), max(zs))
            for n, parts in KP.items():
                for kp in parts:
                    if kp["X"][1] <= xr_[0] + 1e-6 or kp["X"][0] >= xr_[1] - 1e-6:
                        continue
                    d = m.poly_dist(kp["poly"], poly)
                    if designed(kp["part"], p["name"]):
                        k_ = (kp["part"], p["name"])
                        contact.setdefault(k_, []).append((d, n))
                        continue
                    key = (tname, p["name"])
                    if key not in res or d < res[key][0]:
                        res[key] = (d, n, kp["part"])
    return res, contact


def pin_gauge_on_frame(G, gd, key="D"):
    """T3 at a module pin: side-view distances to the frame's fixed parts that overlap in x.  Designed seats (lands on
    the rail top, the target pin in the press bore) are returned apart; the fence-to-rail-face gap is the y register."""
    xp = KO[key]["x_pin"]
    out, seat = {}, {}
    for p in GEO["parts"]:
        if p["body"] != "fixed" or "side" not in p or isinstance(p["side"], str):
            continue
        X = (p["x"][0] - xp, p["x"][1] - xp)
        for q in G.prims:
            if q["op"] != "add" or q["kind"] != "px":
                continue
            if X[1] <= q["a0"] or X[0] >= q["a1"]:
                continue
            d = m.poly_dist([tuple(v) for v in p["side"]], q["poly"])
            k = (p["part"], q["name"])
            is_seat = (p["part"].startswith("balance rail") and ("land" in q["name"] or q["name"].startswith("press block"))) or \
                      (p["part"] == "balance pin D2 " + key and q["name"].startswith("press block"))
            tgt = seat if is_seat else out
            if k not in tgt or d < tgt[k]:
                tgt[k] = d
    return out, seat


# ============================================================================ main
def main():
    os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "scad"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "png"), exist_ok=True)
    J, jd = build_jig()
    D, dd = build_dummy(jd)
    add_readout_and_park(J, jd, dd)
    find_parking(J, D, jd)
    H, hd = build_height_block()
    G, gd = build_pin_gauge()

    amp = {c: (L[0] - sum(dd["y_blade"]) / 2) / (L[0] - CAPS[c]) for c in ("white", "black")}
    # ---------------- labels (text) in use coordinates
    zt = Z_PLATE
    def flat(x, y, z, rot=0.0):          # text on a +z face, reading along +X (rot deg about z)
        c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        return [[c, -s_, 0, x], [s_, c, 0, y], [0, 0, 1, z], [0, 0, 0, 1]]
    J.text("TOCCATA BENCH JIG r4.4", 4.0, flat(0.0, 112.0, zt))
    J.text("BASE = FRAME UNDERSIDE z3.0", 3.2, flat(0.0, 104.0, zt))
    J.text("SHELF z%s  K z%s" % (fmt(Z_SHELF, 3), fmt(K[1], 1)), 3.2, flat(0.0, 97.0, zt))
    J.text("CAL W", 3.0, flat(jd["pad_x"][1] + 7.0, CAPS["white"], zt))
    J.text("CAL B", 3.0, flat(jd["pad_x"][1] + 7.0, CAPS["black"], zt))
    J.text("FLUSH=z%s" % fmt(Z_C, 2), 3.0, flat(jd["ledge"]["x0"] + 8.0, jd["ledge"]["y"][1] + 4.5, zt))
    # dummy: +X face of the beak (print top), reading along -y (front to the left when seen from +X)
    def xface(y, z, x):
        return [[0, 0, 1, x], [1, 0, 0, y], [0, 1, 0, z], [0, 0, 0, 1]]
    D.text("CAP %s" % fmt(Z_C, 2), 3.6, xface(137.0, (dd["z_beak0"] + dd["z_led"]) / 2 + 1.6, dd["hw"]), depth=0.5)
    D.text("1/8: W%s B%s" % (fmt(TURN8 * amp["white"], 2)[1:], fmt(TURN8 * amp["black"], 2)[1:]), 2.6, xface(137.0, (dd["z_beak0"] + dd["z_led"]) / 2 - 2.2, dd["hw"]), depth=0.5)
    # height block: debossed on the outer face (u = t), reading along +v
    def uface(v, w, u):
        return [[0, 0, 1, u], [1, 0, 0, v], [0, 1, 0, w], [0, 0, 0, 1]]
    for nm, v0, v1, ztop in hd["lands"]:
        H.text(nm, 3.4, uface((v0 + v1) / 2, ztop - 4.0, hd["t"] - 0.4), depth=0.4, mode="deboss")
    H.text("W 43.5", 2.8, uface(8.0, 12.0, hd["t"] - 0.4), depth=0.4, mode="deboss")
    H.text("B 55.5", 2.8, uface(26.0, 12.0, hd["t"] - 0.4), depth=0.4, mode="deboss")
    # pin gauge: use-top face (w = z_top), debossed (bed face in print), reading along +u
    G.text("PIN 23.30", 3.2, flat(0.0, (gd["fence"][0] + gd["v"][1]) / 2, gd["z_top"] - 0.4), depth=0.4, mode="deboss")
    G.text("GO>|", 2.6, flat(21.5, (gd["fence"][0] + gd["v"][1]) / 2, gd["z_top"] - 0.4), depth=0.4, mode="deboss")
    G.text("|<GO", 2.6, flat(-21.5, (gd["fence"][0] + gd["v"][1]) / 2, gd["z_top"] - 0.4), depth=0.4, mode="deboss")

    # ---------------- use -> print transforms
    Xw = jd["Xw"]
    xf = dict(
        bench_jig=[[1, 0, 0, Xw], [0, 1, 0, -jd["y_front"]], [0, 0, 1, -Z_DATUM], [0, 0, 0, 1]],
        height_block=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -Z_PLATE], [0, 0, 0, 1]],
        # dummy on its -X face: (X, y, z) -> (y - 119, z - 28.9, X + hw)
        capstan_gauge=[[0, 1, 0, -dd["y_blade"][0]], [0, 0, 1, -(L[1] - 4.6)], [1, 0, 0, dd["hw"]], [0, 0, 0, 1]],
        # pin gauge upside down: rotate 180 deg about u: (u, v, w) -> (u + 26, -v + v_rear, -w + w_top)
        pin_gauge=[[1, 0, 0, 26.0], [0, -1, 0, gd["v"][1]], [0, 0, -1, gd["z_top"]], [0, 0, 0, 1]],
    )
    tools = [("bench_jig", J), ("height_block", H), ("capstan_gauge", D), ("pin_gauge", G)]
    mesh = {}
    for key, T in tools:
        sc = os.path.join(OUT, "scad", key + ".scad")
        st = os.path.join(OUT, "stl", "tool_%s.stl" % key)
        write_scad(T, xf[key], sc)
        run_scad(sc, st)
        V, C, lo, hi = mesh_props(read_stl(st))
        mesh[key] = dict(V=V, C=C, lo=lo, hi=hi, stl=os.path.relpath(st, OUT), scad=os.path.relpath(sc, OUT))
        render_png(sc, os.path.join(OUT, "png", "tool_%s.png" % key))
    render_png(os.path.join(OUT, "scad", "bench_jig.scad"), os.path.join(OUT, "png", "view_jig_rear.png"), camera="36,175,20,50,0,300,230")
    render_png(os.path.join(OUT, "scad", "height_block.scad"), os.path.join(OUT, "png", "view_height_block.png"), camera="5,17,25,70,0,120,140")
    # use-pose assembly scad (jig + dummy + key-free) for a visual check
    asm = os.path.join(OUT, "scad", "assembly_use.scad")
    s = "$fn=40;\n"
    for key, T in (("bench_jig", J), ("capstan_gauge", D)):
        adds = [scad_prim(p) for p in T.prims if p["op"] == "add"]
        subs = [scad_prim(p) for p in T.prims if p["op"] == "sub"]
        refs = [scad_prim(p) for p in T.prims if p["op"] == "ref"]
        s += "color(\"%s\") difference(){ union(){ %s } %s }\n" % ("SteelBlue" if key == "bench_jig" else "Orange", " ".join(adds), " ".join(subs))
        s += "color(\"DimGray\") union(){ %s }\n" % " ".join(refs)
    open(asm, "w").write(s)
    render_png(asm, os.path.join(OUT, "png", "assembly_use.png"), camera="20,150,40,55,0,210,420")

    # ---------------- dummy lever moment (100 % infill) vs the service lever
    V_d, C_d, _, _ = mesh["capstan_gauge"]["V"], mesh["capstan_gauge"]["C"], None, None
    m_print = V_d * RHO
    y_com_print = C_d[0] + dd["y_blade"][0]           # print x = y - 119
    z_com_print = C_d[1] + (L[1] - 4.6)
    y_st = (STEEL["y0"] + STEEL["y1"]) / 2
    M_d = (m_print * (L[0] - y_com_print) + STEEL["m"] * (L[0] - y_st)) * m.G
    W_d = (m_print + STEEL["m"]) * m.G
    dummy = {}
    for col in ("white", "black"):
        Fc = M_d / (L[0] - CAPS[col])
        dummy[col] = dict(F_cap=Fc, F_service=SERVICE[col]["F_cap"], dF=Fc - SERVICE[col]["F_cap"], net_up=Fc - W_d,
                          front_err=front_shift(col, Fc), amp=amp[col], per8=TURN8 * amp[col])
    # finger-press alternative (no dummy): tail pressed by a finger at the capstan with 0.3 / 5 N
    for col in ("white", "black"):
        dummy[col]["finger_03"] = front_shift(col, 0.3)
        dummy[col]["finger_5"] = front_shift(col, 5.0)

    # ---------------- parked pose: capstan access
    bpk = jd["park"]["b"]
    pk_polys = dummy_side_polys(D, bpk)
    dz_ = [q for pg in pk_polys for q in _dense(pg)]
    over = [q[1] for q in dz_ if min(CAPS.values()) - 4.0 <= q[0] <= max(CAPS.values()) + 4.0]
    z_over_cap = min(over) if over else None             # None = nothing of the dummy above the capstans
    # parked dummy vs the fixed jig (X-overlapping prisms, excluding the parking post it leans on)
    park_clear = {}
    for p in J.prims:
        if p["op"] != "add" or p["kind"] != "px" or p["name"].startswith("parking"):
            continue
        if p["a1"] <= -dd["hw"] or p["a0"] >= dd["hw"]:
            continue
        park_clear[p["name"]] = min(m.poly_dist(pg, p["poly"]) for pg in pk_polys)
    com_park = m.rot((y_com_print, z_com_print), L, -bpk)

    # ---------------- clearance checks
    sweep, contact = clearance_sweep([("bench_jig", J), ("capstan_gauge", D)])
    tg, tg_seat = pin_gauge_on_frame(G, gd)
    ridge_gap = RIDGE_Y0 - gd["v"][1]
    # crown contact: capstan head top vs the dummy floor
    crown = min(d for d, _ in contact.get(("capstan head", "body (pocket walls, floor = felt plane z_c)"), [(float("nan"), "")]))

    # ---------------- dims
    J_ = "벤치 지그"
    dim(J_, "지그 기준면", Z_DATUM, "z", "지그 밑면 = 프레임 밑면 (z%s, 바닥판 밑)" % fmt(Z_DATUM, 1), "출력 높이 = z − %s; 프레임과 같은 층 높이로 출력하면 같은 층에서 반올림됨" % fmt(Z_DATUM, 1))
    dim(J_, "받침판", "X %s~%s × y %s~%s, z%s~%s" % (fmt(-Xw, 1), fmt(Xw, 1), fmt(jd["y_front"], 1), fmt(jd["y_rear"], 1), fmt(Z_DATUM, 1), fmt(Z_PLATE, 1)), "mm",
        "X = x − 그 건반의 밸런스 핀 x", "윗면 z%s = 프레임 바닥 윗면 = 높이 블록 자리" % fmt(Z_PLATE, 1))
    dim(J_, "레일 블록 (핀 자리 · 핀 게이지 자리)", "y%s~%s, 윗면 z%s, 앞면 y%s" % (fmt(RAIL_Y0, 1), fmt(jd["y_rail1"], 2), fmt(Z_RAIL, 1), fmt(RAIL_Y0, 1)), "mm",
        "프레임 밸런스 레일(낮춘 곳) 윗면·앞면과 같음", "X %s~%s" % (fmt(-Xw, 1), fmt(Xw, 1)))
    dim(J_, "예비 밸런스 핀 구멍", "Ø%s 출력 (압입), y%s, 깊이 z%s까지" % (fmt(jd["PIN_HOLE"], 1), fmt(PIN_Y, 1), fmt(Z_RAIL - (PIN_LEN - (PIN_TOP - Z_RAIL)) - 1.0, 1)), "mm",
        "X 0", "T3으로 꼭대기 z%s — 첫 핀 = 핀 게이지 검증" % fmt(PIN_TOP, 2))
    dim(J_, "K 봉 토막 구멍 (건반 봉)", "중심 (y%s, z%s), Ø3.9 출력 → Ø4.0 드릴, 눈물방울 윗부분" % (fmt(K[0], 1), fmt(K[1], 1)), "mm",
        "프레임 봉 받침 바닥 z%s에 봉이 얹힘 = 봉 중심 K" % fmt(K[1] - 2.0, 2), "기둥 X ±%s~%s, y%s~%s, 윗면 z%s; 오른쪽 구멍은 막힘(벽 1.0) → 봉 토막 %s"
        % (fmt(jd["kx"][0], 1), fmt(jd["kx"][1], 1), fmt(jd["y_rail1"], 2), fmt(K[0] + 2.6, 1), fmt(jd["k_top"], 1), fmt(jd["stub_K"], 1)))
    dim(J_, "쉼 선반", "X ±%s, y%s~200.0, 윗면 z%s" % (fmt(jd["sx"], 1), fmt(SHELF_Y0, 1), fmt(Z_SHELF, 3)), "mm", "프레임 뒤 선반 윗면 (S10)",
        "모든 건반의 쉼 펠트(레버 x ± 4)가 온전히 앉음 — 프레임의 F·F# 부분 착지는 재현하지 않음(아래 주의)")
    dim(J_, "L 봉 토막 구멍 (레버 봉)", "중심 (y%s, z%s), Ø3.9 출력 → Ø4.0 드릴" % (fmt(L[0], 2), fmt(L[1], 1)), "mm", "프레임 레버 봉 L (S11)",
        "기둥 X ±%s~%s, y%s~%s, 윗면 z%s; 오른쪽 막힘 → 봉 토막 %s; 가장 넓은 얇은 꼬리 끝(X %s~%s, y%s)과 대각 %s"
        % (fmt(jd["lx"][0], 1), fmt(jd["lx"][1], 1), fmt(jd["ly"][0], 2), fmt(jd["ly"][1], 2), fmt(jd["l_top"], 1), fmt(jd["stub_L"], 1),
           fmt(ENV["back"][0], 2), fmt(ENV["back"][1], 2), fmt(Y_TAIL_END, 1),
           fmt(math.hypot(max(0.0, jd["lx"][0] - ENV["back_abs"]), jd["ly"][0] - Y_TAIL_END), 2)))
    dim(J_, "영점 받침 (교정)", "백 y%s · 흑 y%s, X ±%s~%s, 홈 바닥 z%s (폭 4.6, 턱 z%s)" % (fmt(CAPS["white"], 2), fmt(CAPS["black"], 2), fmt(jd["pad_x"][0], 1), fmt(jd["pad_x"][1], 1), fmt(jd["z_zero"], 1), fmt(jd["z_zero"] + 1.0, 1)), "mm",
        "Ø4 교정봉 윗면 = z%s = 정착 쉼 캡스턴 꼭대기 (S08; 건반 좌표 z%s)" % (fmt(Z_C, 2), fmt(Z_C_KEY, 1)), "건반 꼬리·빔과 X로 %s 떨어짐" % fmt(jd["pad_x"][0] - ENV["back_abs"], 2))
    dim(J_, "읽기 턱 기둥", "X %s~%s (윗면), y%s~%s, 윗면 z%s" % (fmt(jd["ledge"]["x0"], 1), fmt(jd["ledge"]["x0"] + 8.0, 1), fmt(jd["ledge"]["y"][0], 1), fmt(jd["ledge"]["y"][1], 1), fmt(jd["ledge"]["z"], 1)), "mm",
        "가짜 레버 b = 0에서 바늘 윗면", "(X, z) 단면이 사다리꼴: 윗면 X %s~%s(z%s~%s), 밑은 X %s까지 버팀(z%s) — tools_geometry front; 바늘 끝과 X 틈 1.1 (축 놀음 ±0.5)"
        % (fmt(jd["ledge"]["x0"], 1), fmt(jd["ledge"]["x0"] + 8.0, 1), fmt(jd["ledge"]["z"] - 10.0, 1), fmt(jd["ledge"]["z"], 1), fmt(jd["ledge"]["x0"] + 17.0, 1), fmt(Z_PLATE, 1)))
    dim(J_, "주차 기둥", "X ±4.0, y%s~%s, 윗면 z%s" % (fmt(jd["park"]["y"][0], 2), fmt(jd["park"]["y"][1], 2), fmt(jd["park"]["z"], 1)), "mm",
        "가짜 레버를 뒤로 %s° 젖혀 기댐" % fmt(math.degrees(bpk), 0), "무게중심이 L 뒤 %s → 저절로 넘어오지 않음; 캡스턴 위(y%s~%s)에 %s"
        % (fmt(com_park[0] - L[0], 1), fmt(min(CAPS.values()) - 4.0, 0), fmt(max(CAPS.values()) + 4.0, 0), "아무것도 없음" if z_over_cap is None else "가장 낮은 부분 z" + fmt(z_over_cap, 1)))
    Hn = "높이 블록"
    for nm, v0, v1, ztop in hd["lands"]:
        col = "백" if nm[0] == "W" else "흑"
        dim(Hn, "땅 %s (%s건 %s)" % (nm, col, "높음 한계" if nm[1] == "+" else "낮음 한계"), ztop, "z",
            "받침판 윗면 z%s 위 %s (블록 높이)" % (fmt(Z_PLATE, 1), fmt(ztop - Z_PLATE, 2)), "v%s~%s, 두께 %s" % (fmt(v0, 0), fmt(v1, 0), fmt(hd["t"], 0)))
    dim(Hn, "창 (앞 높이)", "±%s" % fmt(HB_WIN, 2), "mm", "백 %s · 흑 %s" % (fmt(TOP_W, 1), fmt(TOP_B, 1)),
        "펀칭 1장 = 앞 %s → 창 %s ≥ 한 걸음" % (fmt(PUNCH * K[0] / (sum(REST_Y) / 2 - K[0]), 2), fmt(2 * HB_WIN, 2)))
    Dn = "캡스턴 게이지"
    dim(Dn, "허브 구멍", "Ø3.9 출력 → Ø4.0 드릴, 중심 L (y%s, z%s), 허브 R4.6, 폭 X ±%s" % (fmt(L[0], 2), fmt(L[1], 1), fmt(dd["hw"], 1)), "mm", "L 봉 토막", "")
    dim(Dn, "밑면 (펠트 면)", Z_C, "z", "b = 0에서 평면 z%s, y%s~%s" % (fmt(Z_C, 2), fmt(dd["y_front"], 2), fmt(L[0] - 3.2, 2)),
        "캡스턴 꼭대기와 닿는 면 (단단함 — 펠트 눌림 없음); r4.4 고침 2b: 정착 쉼 꼭대기 백 %s · 흑 %s의 가운데 (건반 좌표 z%s 아님)" % (fmt(SETTLE["white"]["crown"], 3), fmt(SETTLE["black"]["crown"], 3), fmt(Z_C_KEY, 1)))
    dim(Dn, "강철 주머니", "y%s~%s, z%s~%s, 깊이 %s (+X 면이 열림)" % (fmt(dd["pk"]["y0"], 1), fmt(dd["pk"]["y1"], 1), fmt(dd["pk"]["z0"], 1), fmt(dd["pk"]["z1"], 1), fmt(dd["hw"] - dd["pk_x0"], 1)), "mm",
        "레버 강철 SS400 9×19×40 한 개 (레버와 같은 자리)", "틈 0.2/면 + 스냅 립 0.4")
    dim(Dn, "앞면", dd["y_front"], "y", "건반 뒤끝 y%s와 %s" % (fmt(Y_KEY_REAR, 1), fmt(dd["y_front"] - Y_KEY_REAR, 1)), "")
    dim(Dn, "부리 (손잡이)", "y%s~%s, z%s~%s" % (fmt(dd["y_blade"][0], 1), fmt(dd["y_front"] + 7.2, 1), fmt(dd["z_beak0"], 1), fmt(dd["z_led"], 1)), "mm",
        "흑건 윗면 z%s와 %s" % (fmt(TOP_B, 1), fmt(dd["z_beak0"] - TOP_B, 1)), "")
    dim(Dn, "바늘", "X %s~%s, y%s~%s, 윗면 z%s (b = 0)" % (fmt(dd["hw"], 1), fmt(dd["blade_x1"], 1), fmt(dd["y_blade"][0], 1), fmt(dd["y_blade"][1], 1), fmt(dd["z_led"], 1)), "mm",
        "읽기 턱 기둥 윗면과 손톱으로 같은 높이", "")
    dim(Dn, "확대비 (바늘 / 캡스턴)", "백 %s · 흑 %s" % (fmt(amp["white"], 2), fmt(amp["black"], 2)), "배", "(L − y바늘) / (L − y캡스턴)",
        "1/8회전(%s) = 바늘 %s / %s mm" % (fmt(TURN8, 4), fmt(dummy["white"]["per8"], 2), fmt(dummy["black"]["per8"], 2)))
    dim(Dn, "모멘트 (L 기준)", "%s (실제 레버 %s)" % (fmt(M_d, 2), fmt(SERVICE["white"]["M"], 2)), "N·mm", "출력 채움 100 % + 강철 1",
        "캡스턴 힘 백 %s (실제 %s) · 흑 %s (실제 %s) N" % (fmt(dummy["white"]["F_cap"], 2), fmt(dummy["white"]["F_service"], 2), fmt(dummy["black"]["F_cap"], 2), fmt(dummy["black"]["F_service"], 2)))
    Gn = "핀 높이 게이지"
    dim(Gn, "발 (레일 윗면에 얹힘)", "z%s, 앞 발 y%s~%s, 뒤 발 y%s~%s, 길이 u −26~26" % (fmt(gd["z_land"], 1), fmt(gd["land_f"][0], 1), fmt(gd["land_f"][1], 2), fmt(gd["land_r"][0], 2), fmt(gd["land_r"][1], 2)), "mm",
        "프레임 밸런스 레일 윗면 (낮춘 곳, 받침 능선 y%s 앞)" % fmt(RIDGE_Y0, 2), "앞 발 = 레일 앞면 y%s부터 (그 앞 y%s~%s는 앞 몸통, 울타리가 레일 앞면에 댐)" % (fmt(RAIL_Y0, 1), fmt(gd["fence"][1], 1), fmt(RAIL_Y0, 1)))
    dim(Gn, "울타리", "y%s~%s, z%s까지" % (fmt(gd["fence"][0], 1), fmt(gd["fence"][1], 1), fmt(gd["z_land"] - 4.0, 1)), "mm", "레일 앞면 y%s에 대어 y를 맞춤 (틈 0.3)" % fmt(RAIL_Y0, 1), "")
    dim(Gn, "누름 구멍", "Ø2.5, 멈춤 면 z%s (발에서 %s)" % (fmt(PIN_TOP, 2), fmt(PIN_TOP - gd["z_land"], 2)), "mm", "밸런스 핀 꼭대기 (P32)", "u 0")
    dim(Gn, "열린 홈", "폭 2.9, 천장 z%s" % fmt(gd["z_ch"], 1), "mm", "이웃 핀 꼭대기 z%s와 %s" % (fmt(PIN_TOP, 2), fmt(gd["z_ch"] - PIN_TOP, 1)), "")
    dim(Gn, "GO 구간", "u ±20~26, 천장 z%s (발에서 %s)" % (fmt(gd["go"], 2), fmt(gd["go"] - gd["z_land"], 2)), "mm", "핀이 밑으로 지나가야 함", "")
    dim(Gn, "NO-GO 구간", "u ±16~20, 천장 z%s (발에서 %s)" % (fmt(gd["nogo"], 2), fmt(gd["nogo"] - gd["z_land"], 2)), "mm", "핀이 여기서 멈춰야 함", "합격 = z%s~%s" % (fmt(gd["nogo"], 2), fmt(gd["go"], 2)))

    # ---------------- print data, mass, time
    prn = dict(
        bench_jig=dict(orient="밑면(z3 기준면)을 베드에 — 서포트 없음 (가로 구멍은 눈물방울)", layer="프레임과 같은 층 높이 (권장 0.2 첫 층 + 0.1)", infill=0.40, walls=3, fill_f=0.62, rate=11.0),
        height_block=dict(orient="밑면을 베드에, 땅이 위", layer="0.1, 높이 37.9~50.8 구간만 0.05 (슬라이서 높이 범위 수정자)", infill=0.25, walls=3, fill_f=0.55, rate=6.0),
        capstan_gauge=dict(orient="−X 옆면(주머니 뒤 벽)을 베드에 — 옆모습이 베드 면에 그려짐, 서포트 없음", layer="0.1", infill=1.00, walls=3, fill_f=1.0, rate=8.0),
        pin_gauge=dict(orient="뒤집어(쓸 때 윗면을 베드에) — 발·멈춤 면·GO/NO-GO 천장이 모두 윗면으로 뽑힘, 서포트 없음", layer="0.1 (첫 층 0.2) — 높이가 모두 0.1 격자", infill=1.00, walls=4, fill_f=1.0, rate=8.0),
    )
    for k_, v in prn.items():
        V = mesh[k_]["V"]
        v["mass_g"] = V * RHO * v["fill_f"] * (1.0 if v["fill_f"] >= 1.0 else 1.0)
        v["time_min"] = 60.0 * v["mass_g"] / v["rate"] + 6.0
        lo, hi = mesh[k_]["lo"], mesh[k_]["hi"]
        v["bbox"] = [hi[i] - lo[i] for i in range(3)]
        v["fits_256"] = max(v["bbox"][0], v["bbox"][1]) <= 256.0 and v["bbox"][2] <= 256.0
    total_g = sum(v["mass_g"] for v in prn.values())
    total_min = sum(v["time_min"] for v in prn.values())

    # ---------------- outputs: json
    tj = dict(
        meta=dict(round="r4.5 circuit 2nd", model_dir=MODEL_DIR, generator="tools/make_tools.py",
                  coords="X = x − x_pin (the key's balance-pin / block centre), y and z = model (z from the desk). Print height of the jig = z − %s." % fmt(Z_DATUM, 1),
                  rounding="round half away from zero (fmt)"),
        model_values=dict(K=K, L=L, z_datum=Z_DATUM, z_plate=Z_PLATE, z_shelf=Z_SHELF, caps=CAPS, z_c=Z_C, z_c_key=Z_C_KEY,
                          crown_settled={c_: SETTLE[c_]["crown"] for c_ in ("white", "black")},
                          crown_err={c_: Z_C - SETTLE[c_]["crown"] for c_ in ("white", "black")}, key_top=TOP_W, black_top=TOP_B,
                          pin_y=PIN_Y, pin_top=PIN_TOP, z_rail_low=Z_RAIL, rail_front_y=RAIL_Y0, cradle_ridge_y0=r(RIDGE_Y0, 3),
                          steel=STEEL, rest_pad_y=REST_Y, shelf_y0=SHELF_Y0, key_rear_y=Y_KEY_REAR, punch_front=r(PUNCH * K[0] / (sum(REST_Y) / 2 - K[0]), 4),
                          turn8=TURN8, key_envelopes_rel_pin=ENV,
                          keys={n: dict(x_pin=r(k["x_pin"], 3), lever=r(k["lever"], 3), head=[r(v, 3) for v in k["head"]], tail=[r(v, 3) for v in k["tail"]],
                                        block=[r(v, 3) for v in k["block"]], y_cap=k["y_cap"]) for n, k in KO.items()}),
        service=SERVICE,
        dummy_lever=dict(m_print_g=m_print, com_print_yz=[y_com_print, z_com_print], steel_g=STEEL["m"], M_Nmm=M_d, W_N=W_d, per_colour=dummy,
                         parked_deg=math.degrees(bpk), parked_com_behind_L=com_park[0] - L[0], parked_min_z_over_capstans=z_over_cap),
        tools={},
        dims=DIMS,
        checks=dict(
            key_clearance_min={"%s | %s" % k: dict(min=r(v[0], 3), key=v[1], key_part=v[2]) for k, v in sorted(sweep.items())},
            designed_contacts={"%s | %s" % k: dict(min=r(min(d for d, _ in v), 3), max=r(max(d for d, _ in v), 3)) for k, v in contact.items()},
            crown_to_dummy_floor=crown,
            pin_gauge_on_frame_D={"%s | %s" % k: r(v, 3) for k, v in sorted(tg.items())},
            pin_gauge_seats_D={"%s | %s" % k: r(v, 3) for k, v in sorted(tg_seat.items())},
            pin_gauge_rear_face_to_cradle_ridge=r(ridge_gap, 3),
        ),
        print=prn, total_mass_g=total_g, total_time_min=total_min,
    )
    for key, T in tools:
        tj["tools"][key] = dict(name_ko=T.name_ko, stl=mesh[key]["stl"], scad=mesh[key]["scad"], png="png/tool_%s.png" % key,
                                volume_mm3=mesh[key]["V"], print_bbox=prn[key]["bbox"],
                                side=T.side(("add", "add_post", "sub", "ref")), plan=T.plan(("add", "add_post", "sub", "ref")), front=T.front(("add", "add_post", "sub", "ref")),
                                labels=[t["s"] for t in T.texts])
    frames = dict(bench_jig="X = x − x_pin of the key on the jig, y / z = model; print height = z − %s" % fmt(Z_DATUM, 1),
                  height_block="X = u: 0 = the face held against the key side, 10 = outer face; y = v: 0 = block front end "
                               "(white: v0 at the key front y0; black: v18 at y58); z = model (block stands on the jig plate z%s)" % fmt(Z_PLATE, 1),
                  capstan_gauge="use pose b = 0 on the jig: X = x − x_pin, y / z = model; side_parked = the flipped pose on the parking post",
                  pin_gauge="X = u = x − x_pin of the target pin, y / z = model (feet on the rail top z%s)" % fmt(Z_RAIL, 1))
    for k_, f_ in frames.items():
        tj["tools"][k_]["frame"] = f_
    tj["tools"]["capstan_gauge"]["side_parked"] = [[[r(a), r(b)] for a, b in pg] for pg in pk_polys]
    tj["tools"]["capstan_gauge"]["parked_b_deg"] = math.degrees(bpk)

    def js(o):
        if isinstance(o, float):
            return round(o, 4)
        if isinstance(o, dict):
            return {str(k): js(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [js(v) for v in o]
        return o
    json.dump(js(tj), open(os.path.join(OUT, "tools_geometry.json"), "w"), ensure_ascii=False, indent=1)

    # ---------------- side-view check figure (matplotlib)
    try:
        side_figure(J, D, G, jd, dd, gd, pk_polys)
    except Exception as e:           # figure is a convenience only
        print("side figure failed:", e)

    gd["ridge_gap"] = ridge_gap
    write_md(tj, jd, dd, hd, gd, dummy, amp, M_d, W_d, m_print, prn, total_g, total_min, sweep, contact, tg, crown, bpk, com_park, z_over_cap)
    # console summary
    print("model:", MODEL_DIR)
    print("dummy lever: M %.2f N mm (service %.2f), F_cap white %.3f / black %.3f N (service %.3f / %.3f), W %.3f N, key-front error %+.3f / %+.3f mm"
          % (M_d, SERVICE["white"]["M"], dummy["white"]["F_cap"], dummy["black"]["F_cap"], SERVICE["white"]["F_cap"], SERVICE["black"]["F_cap"], W_d,
             dummy["white"]["front_err"], dummy["black"]["front_err"]))
    print("finger instead of dummy: 0.3 N -> %+.2f / %+.2f mm, 5 N -> %+.2f / %+.2f mm" % (dummy["white"]["finger_03"], dummy["black"]["finger_03"], dummy["white"]["finger_5"], dummy["black"]["finger_5"]))
    print("amplification white %.2f black %.2f -> 1/8 turn = %.3f / %.3f mm at the blade" % (amp["white"], amp["black"], dummy["white"]["per8"], dummy["black"]["per8"]))
    print("parked at %.1f deg, COM %.1f behind L, lowest dummy point over the capstans %s; parking post top z%.1f; parked vs jig %s" % (math.degrees(bpk), com_park[0] - L[0], z_over_cap, jd["park"]["z"], {k: round(v, 2) for k, v in park_clear.items()}))
    print("crown to dummy floor (designed contact): %.3f" % crown)
    for k, v in sorted(sweep.items(), key=lambda kv: kv[1][0])[:12]:
        print("  clearance %-70s %.2f  (key %s %s)" % (" | ".join(k), v[0], v[1], v[2]))
    for k, v in contact.items():
        print("  designed contact %s: %.3f..%.3f" % (k, min(d for d, _ in v), max(d for d, _ in v)))
    for k, v in sorted(tg.items(), key=lambda kv: kv[1])[:10]:
        print("  T3 on frame (pin D) %-70s %.2f" % (" | ".join(k), v))
    for k_, v in prn.items():
        print("%-14s V %.1f cm3 mass %.1f g time %.0f min bbox %s fits %s" % (k_, mesh[k_]["V"] / 1000, v["mass_g"], v["time_min"], [round(b, 1) for b in v["bbox"]], v["fits_256"]))
    print("total %.1f g, %.0f min" % (total_g, total_min))


# ============================================================================ figure
def side_figure(J, D, G, jd, dd, gd, pk_polys):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP
    fig, ax = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw=dict(height_ratios=[1.4, 1]))
    KP = key_side_parts()
    for n, col, ls in (("D", "#999999", "-"), ("C#", "#553388", "--")):
        for kp in KP[n]:
            ax[0].add_patch(MP(kp["poly"], closed=True, fill=False, ec=col, lw=0.6, ls=ls))
    for p in J.prims:
        if p["kind"] == "px":
            ax[0].add_patch(MP(p["poly"], closed=True, fc={"add": "#8fb3d9", "add_post": "#8fb3d9", "sub": "white", "ref": "#555555"}[p["op"]], ec="#1f4e79", lw=0.6, alpha=0.8 if p["op"] != "sub" else 1.0))
        elif p["kind"] == "py":
            zs = [b for _, b in p["poly"]]
            ax[0].add_patch(MP(rect(p["a0"], p["a1"], min(zs), max(zs)), closed=True, fc="#8fb3d9", ec="#1f4e79", lw=0.6, alpha=0.8))
    for p in D.prims:
        if p["kind"] == "px":
            ax[0].add_patch(MP(p["poly"], closed=True, fc={"add": "#f2b36b", "add_post": "#f2b36b", "sub": "white", "ref": "#666666"}[p["op"]], ec="#8a4b00", lw=0.6, alpha=0.75 if p["op"] != "sub" else 1.0))
    for pg in pk_polys:
        ax[0].add_patch(MP(pg, closed=True, fill=False, ec="#8a4b00", lw=0.6, ls=":"))
    ax[0].set_xlim(-12, 250)
    ax[0].set_ylim(0, 125)
    ax[0].set_aspect("equal")
    ax[0].set_title("T1 jig (blue) + T2 dummy lever (orange; dotted = parked) + key D (grey) / C# (purple dashed) at rest -- side (y, z)")
    ax[0].grid(lw=0.3)
    # T3 on the frame rail at the D pin
    xp = KO["D"]["x_pin"]
    for p in GEO["parts"]:
        if p["body"] == "fixed" and "side" in p and not isinstance(p["side"], str) and (p["x"][0] - xp) < 26 and (p["x"][1] - xp) > -26:
            if any(k in p["part"] for k in ("balance rail", "balance pin", "rod end", "key rod")):
                ax[1].add_patch(MP(p["side"], closed=True, fill=False, ec="#777777", lw=0.6))
    for p in G.prims:
        if p["kind"] == "px":
            ax[1].add_patch(MP(p["poly"], closed=True, fc="#9fd49f", ec="#1b5e20", lw=0.6, alpha=0.6))
        elif p["kind"] == "pz":
            ys = [b for _, b in p["poly"]]
            ax[1].add_patch(MP(rect(min(ys), max(ys), p["a0"], p["a1"]), closed=True, fc="white" if p["op"] == "sub" else "#555555", ec="#1b5e20", lw=0.6))
    ax[1].set_xlim(124, 148)
    ax[1].set_ylim(8, 36)
    ax[1].set_aspect("equal")
    ax[1].grid(lw=0.3)
    ax[1].set_title("T3 pin gauge on the frame rail (all u-sections overlaid) -- side (y, z)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "png", "check_side.png"), dpi=110)
    plt.close(fig)


# ============================================================================ tools.md (Korean)
def write_md(tj, jd, dd, hd, gd, dummy, amp, M_d, W_d, m_print, prn, total_g, total_min, sweep, contact, tg, crown, bpk, com_park, z_over_cap):
    w, b = dummy["white"], dummy["black"]
    pf = PUNCH * K[0] / (sum(REST_Y) / 2 - K[0])
    L_ = []
    a = L_.append

    def dt(tools_):
        a("| 번호 | 공구 | 항목 | 값 | 단위 | 기준 | 비고 |")
        a("|---|---|---|---|---|---|---|")
        for d_ in DIMS:
            if d_["tool"] not in tools_:
                continue
            v = d_["value"]
            vs = fmt(v, 3 if abs(v - round(v, 2)) > 1e-9 else 2) if isinstance(v, float) else str(v)
            a("| %s | %s | %s | %s | %s | %s | %s |" % (d_["id"], d_["tool"], d_["item"], vs, d_["unit"], d_["basis"], d_["note"]))
        a("")
    a("# Toccata W1+ r4.4 — 출력 공구 3종 (벤치 지그 · 캡스턴 벤치 게이지 · 밸런스 핀 높이 게이지)")
    a("")
    a("`tools/make_tools.py`가 단일 모델(`%s/model_v4.py` + `geometry.json`)에서 만든다. 모든 치수는 `tools_geometry.json`의 `dims`(T01~T%02d)와 같다. 좌표: X = x − 그 건반의 밸런스 핀 x, y·z는 모델(z는 책상에서)."
      % (os.path.basename(MODEL_DIR.rstrip("/")) or MODEL_DIR, len(DIMS)))
    a("")
    a("## 먼저 알아둘 것 (중요한 순서)")
    a("")
    a("1. **벤치에서 건반 꼬리를 무엇이 누르느냐가 건반 높이를 바꾼다.** 건반은 앞이 무거워(무게중심 y%s, 봉 y%s) 지그에 올리면 꼬리가 뜬다. 쉼 펠트는 무른 접촉(모델 K 30 N/mm^1.5)이라 "
      "손가락으로 누르면 0.3 N에서 앞이 %s mm, 5 N에서 %s mm 달라진다(실제 쉼 반력 %s N 기준) — 펀칭 1장(%s mm)만큼 틀린다. 그래서 **캡스턴 게이지를 ‘가짜 레버’로 만들었다**: "
      "지그의 L 봉 토막에 걸려 실제 레버와 같은 모멘트(%s N·mm, 실제 %s)로 캡스턴을 누른다 → 쉼 펠트가 실제 하중을 받는다. 남는 차이는 앞 높이 %s / %s mm(백 / 흑)."
      % (fmt(SERVICE["white"]["key_com"][0], 1), fmt(K[0], 1), fmt(w["finger_03"], 2), fmt(w["finger_5"], 2), fmt(SERVICE["white"]["rest_R"], 2), fmt(pf, 2),
         fmt(M_d, 2), fmt(SERVICE["white"]["M"], 2), fmt(w["front_err"], 3), fmt(b["front_err"], 3)))
    a("2. **기준은 책상이 아니라 프레임 자리다.** 지그 밑면 = 프레임 밑면(z%s). 봉 토막 구멍 중심 = K(%s, %s)(프레임 봉 받침 바닥 z%s에 봉이 얹힌 자리), 쉼 선반 윗면 = z%s, 레버 봉 = L(%s, %s). "
      "지그를 프레임과 같은 층 높이로 뽑으면 선반·봉 높이가 프레임과 같은 층에서 반올림된다. 핀 게이지는 레일 윗면(z%s)과 레일 앞면(y%s)에 댄다."
      % (fmt(Z_DATUM, 1), fmt(K[0], 1), fmt(K[1], 1), fmt(K[1] - 2.0, 1), fmt(Z_SHELF, 3), fmt(L[0], 2), fmt(L[1], 1), fmt(Z_RAIL, 1), fmt(RAIL_Y0, 1)))
    a("3. **캡스턴은 확대해서 읽는다.** r4.3 글의 ‘빔 윗면 위 2.5 단’은 빔 윗면이 서포트 쪽(거친 면)이고 1/8회전(%s mm)을 FDM 계단으로 가를 수 없다. 가짜 레버의 바늘은 캡스턴보다 %s배(백) / %s배(흑) 움직여 "
      "1/8회전 = 바늘 %s / %s mm — 손톱으로 읽기 턱과 같은 높이인지 느낀다."
      % (fmt(TURN8, 4), fmt(amp["white"], 2), fmt(amp["black"], 2), fmt(w["per8"], 2), fmt(b["per8"], 2)))
    a("4. **출력물 4개, 추가 구매 없음.** 봉 토막 3개(%s · %s · 교정봉 %s, 건반 봉과 같은 4 m 봉에서 약 %s mm), 예비 밸런스 핀 1개(100개 묶음의 남는 것), 강철 블록 1개(설치 전 레버용 90개 중 하나를 빌림). "
      "합계 약 %s g · %s (부품표의 ‘출력 공구 15 g’을 바꿔야 함)." % (fmt(jd["stub_K"], 1), fmt(jd["stub_L"], 1), fmt(jd["cal"], 1), fmt(jd["stub_K"] + jd["stub_L"] + jd["cal"] + 6, 0),
                                                           fmt(total_g, 0), "%d시간 %d분" % (int(total_min // 60), int(total_min % 60))))
    a("")
    a("## 공구 한눈에")
    a("")
    a("| 공구 | 하는 일 | 기준 | 출력 방향 | 층 · 채움 | 질량 | 시간 | STL |")
    a("|---|---|---|---|---|---|---|---|")
    names = dict(bench_jig="T1 벤치 지그 (받침)", height_block="T1 높이 블록", capstan_gauge="T2 캡스턴 벤치 게이지 (가짜 레버)", pin_gauge="T3 밸런스 핀 높이 게이지")
    jobs = dict(bench_jig="건반 1개를 프레임과 같은 자리(K 봉·쉼 선반·L 봉)에 올림", height_block="건반 앞 높이 ±%s 확인 (백 %s / 흑 %s)" % (fmt(HB_WIN, 2), fmt(TOP_W, 1), fmt(TOP_B, 1)),
                capstan_gauge="실제 하중으로 꼬리를 누르고 캡스턴 꼭대기를 정착 쉼 높이 z%s로 확대해 읽음" % fmt(Z_C, 2), pin_gauge="핀을 꼭대기 z%s까지 눌러 넣고 GO/NO-GO로 확인" % fmt(PIN_TOP, 2))
    datum = dict(bench_jig="밑면 = 프레임 밑면 z%s" % fmt(Z_DATUM, 1), height_block="지그 받침판 윗면 z%s" % fmt(Z_PLATE, 1), capstan_gauge="L 봉 토막 + 영점 받침(교정)",
                 pin_gauge="레일 윗면 z%s + 앞면 y%s" % (fmt(Z_RAIL, 1), fmt(RAIL_Y0, 1)))
    for k_ in ("bench_jig", "height_block", "capstan_gauge", "pin_gauge"):
        v = prn[k_]
        a("| %s | %s | %s | %s | %s · 채움 %s %% · 벽 %d | %s g | 약 %s분 | `%s` |" % (names[k_], jobs[k_], datum[k_], v["orient"], v["layer"], fmt(100 * v["infill"], 0), v["walls"],
                                                                            fmt(v["mass_g"], 1), fmt(v["time_min"], 0), tj["tools"][k_]["stl"]))
    a("")
    a("공통: PETG, 0.4 노즐, 서포트 없음, 256 × 256 베드에 모두 들어감(가장 큰 지그 %s × %s). 시간은 P2S 기준 대략값." % (fmt(prn["bench_jig"]["bbox"][0], 0), fmt(prn["bench_jig"]["bbox"][1], 0)))
    a("")
    a("### FDM 보정 (±0.3을 어디에 넣었나)")
    a("")
    a("| 자리 | 설계 값 | 이유 |")
    a("|---|---|---|")
    a("| K·L 봉 토막 구멍, 가짜 레버 허브 | Ø3.9 출력 → Ø4.0 드릴 | 프레임 핀 보스·캐리어와 같은 방법: 드릴이 지름을 정하므로 FDM 오차가 남지 않음. 가로 구멍은 눈물방울 지붕 |")
    a("| 강철 주머니 | 9.4 × 19.4 × 40.4 (면마다 +0.2) + 스냅 립 0.4 | 출력 주머니는 0.1~0.3 작게 나옴; 립이 강철을 잡음 |")
    a("| 핀 게이지 누름 구멍 | Ø2.5 (핀 Ø2.0) | 작은 세로 구멍은 0.2~0.3 작게 나옴 → 실제 약 Ø2.2, 핀을 잡지 않음 |")
    a("| 핀 게이지 홈 폭 | 2.9 (핀 2.0) | −0.3이어도 2.6 |")
    a("| 지그 예비 핀 구멍 | Ø1.9 출력 (압입) | 프레임 핀 구멍 치수는 모델에 없음 — 프레임과 같은 방법으로 맞추고, 헐거우면 순간접착제 |")
    a("| 높이·땅·멈춤 면 (z) | 보정 없음 | 층 높이로 정해짐 — 모든 높이를 층 격자(0.1, 높이 블록 땅만 0.05)에 맞춤 |")
    a("| 바늘 끝 ↔ 읽기 턱 | X 틈 1.1 | 허브 축 놀음 ±0.5 + FDM에도 닿지 않음 |")
    a("")
    # ---------------- per tool
    a("## T1 벤치 지그 (받침 + 높이 블록)")
    a("")
    a("건반 한 개를 모듈 프레임과 같은 자리에 올린다: Ø4 봉 토막(K), 쉼 선반(z%s), 밸런스 핀(x 위치), 레버 봉 토막(L — 가짜 레버용), 영점 받침(교정), 읽기 턱 기둥, 주차 기둥. "
      "모든 건반(백 7 · 흑 5 · 끝 부속)이 같은 지그를 쓴다 — X 0에 그 건반의 밸런스 핀 홈이 온다." % fmt(Z_SHELF, 3))
    a("")
    dt(("벤치 지그", "높이 블록"))
    a("건반과의 틈 (모델 건반 12개의 쉼 자세 옆모습, X가 겹치는 것만; 설계 접촉 제외):")
    a("")
    a("| 지그·가짜 레버 부분 | 최소 틈 | 건반 | 건반 부분 |")
    a("|---|---|---|---|")
    for k, v in sorted(sweep.items(), key=lambda kv: kv[1][0])[:10]:
        a("| %s | %s | %s | %s |" % (" / ".join(k), fmt(v[0], 2), v[1], v[2]))
    a("")
    a("설계 접촉: 캡스턴 꼭대기 ↔ 가짜 레버 밑면 %s (닿음), 쉼 펠트 ↔ 선반 %s (펠트 눌림 몫), 노치 ↔ K 봉 토막, 핀 ↔ 핀 홈." %
      (fmt(crown, 2), fmt(min(min(d for d, _ in v) for k, v in contact.items() if k[0] == "rest felt"), 3) if any(k[0] == "rest felt" for k in contact) else "—"))
    a("")
    a("### 높이 블록")
    a("")
    a("받침판 윗면(z%s)에 세워 건반 옆면에 붙이는 계단 블록. 손톱을 건반 윗면에서 땅으로 밀어 본다:" % fmt(Z_PLATE, 1))
    a("")
    a("- **W+ / B+ (높은 땅)**: 손톱이 **걸려야** 한다(땅이 건반보다 높음). 손톱이 떨어지면 건반이 높다 → 펀칭 1장 더.")
    a("- **W− / B− (낮은 땅)**: 땅에서 건반으로 밀 때 손톱이 **걸려야** 한다(건반이 땅보다 높음). 안 걸리면 건반이 낮다 → 펀칭 1장 뺌.")
    a("- 창 = ±%s, 펀칭 1장 = 앞 %s mm이므로 늘 맞는 장수가 있다. 땅은 앞 y≈4 / 12(백), 앞 모서리 뒤 3~19(흑)에 대면 끝보다 0.93배 — 무시할 만함." % (fmt(HB_WIN, 2), fmt(pf, 2)))
    a("")
    a("## T2 캡스턴 벤치 게이지 (가짜 레버)")
    a("")
    a("실제 레버 모양 그대로(밑면 = 레버 펠트 면 z%s, 강철 9×19×40이 레버와 같은 자리 y%s~%s) 출력 캐리어에 강철 한 개를 끼운 것. 허브를 지그의 L 봉 토막에 끼운다. "
      "앞의 부리가 손잡이이고, 부리 끝의 바늘이 지그의 읽기 턱 기둥 옆에 온다." % (fmt(Z_C, 2), fmt(STEEL["y0"], 1), fmt(STEEL["y1"], 1)))
    a("")
    dt(("캡스턴 게이지",))
    a("- 하중: 출력 %s g(채움 100 %%) + 강철 %s g → L 모멘트 %s N·mm (실제 레버 %s: 무게 + 비틀림 스프링). 캡스턴 힘 백 %s N (실제 %s), 흑 %s N (실제 %s). 무게 %s N은 백·흑 모두 캡스턴 힘보다 작아(%s / %s N 위로) 허브가 늘 봉의 같은 쪽에 닿는다."
      % (fmt(m_print, 1), fmt(STEEL["m"], 1), fmt(M_d, 2), fmt(SERVICE["white"]["M"], 2), fmt(w["F_cap"], 2), fmt(w["F_service"], 2), fmt(b["F_cap"], 2), fmt(b["F_service"], 2),
         fmt(W_d, 2), fmt(w["net_up"], 2), fmt(b["net_up"], 2)))
    a("- 그 차이가 건반 앞 높이에 주는 영향: 백 %s, 흑 %s mm (모델의 쉼 펠트·노치 천 Hertz 법칙)." % (fmt(w["front_err"], 3), fmt(b["front_err"], 3)))
    a("- 읽기: 바늘 윗면(z%s at b = 0)과 읽기 턱 윗면이 손톱으로 같은 높이 = 캡스턴 꼭대기 z%s(정착 쉼). 확대비 백 %s · 흑 %s → 1/8회전 = 바늘 %s / %s mm."
      % (fmt(dd["z_led"], 1), fmt(Z_C, 2), fmt(amp["white"], 2), fmt(amp["black"], 2), fmt(w["per8"], 2), fmt(b["per8"], 2)))
    a("- 주차: 부리를 들어 뒤로 %s° 젖히면 주차 기둥에 기대 선다(무게중심이 L 뒤 %s mm). 이때 캡스턴 위(y%s~%s)에는 %s — 육각 렌치가 위에서 들어간다."
      % (fmt(math.degrees(bpk), 0), fmt(com_park[0] - L[0], 1), fmt(min(CAPS.values()) - 4.0, 0), fmt(max(CAPS.values()) + 4.0, 0),
         "가짜 레버가 전혀 없다" if z_over_cap is None else "가짜 레버의 가장 낮은 부분이 z" + fmt(z_over_cap, 1)))
    a("")
    a("## T3 밸런스 핀 높이 게이지")
    a("")
    a("레일 길이 방향(x) 막대 52 mm. 가운데 누름 구멍(멈춤 면 = 핀 꼭대기 z%s = 발 위 %s), 양 끝에 GO(천장 z%s) → NO-GO(천장 z%s) 구간. 발은 레일 윗면(z%s, 받침 능선 y%s 앞)에, 울타리는 레일 앞면(y%s)에 댄다. "
      "가운데 홈(폭 2.9, 천장 z%s)이 이미 눌린 이웃 핀(피치 ≥ 13.05) 위를 지나간다."
      % (fmt(PIN_TOP, 2), fmt(PIN_TOP - Z_RAIL, 2), fmt(gd["go"], 2), fmt(gd["nogo"], 2), fmt(Z_RAIL, 1), fmt(RIDGE_Y0, 2), fmt(RAIL_Y0, 1), fmt(gd["z_ch"], 1)))
    a("")
    dt(("핀 높이 게이지",))
    a("프레임(핀 D 자리)에 놓았을 때 이웃 부품과의 옆모습 거리. 설계 맞닿음(발 ↔ 레일 윗면 0, 대상 핀 ↔ 누름 구멍)은 뺐다. 울타리 ↔ 레일 앞면 0.3은 y 맞춤 틈이다. "
      "뒤 면 ↔ 봉 받침 능선(y%s, z%s까지)은 %s(울타리를 앞면에 대면 %s)." % (fmt(RIDGE_Y0, 2), fmt(RAIL_LIP, 1), fmt(gd["ridge_gap"], 2), fmt(gd["ridge_gap"] + 0.3, 2)))
    a("")
    a("| 프레임 부품 | 게이지 부분 | 거리 |")
    a("|---|---|---|")
    for k, v in sorted(tg.items(), key=lambda kv: kv[1])[:8]:
        a("| %s | %s | %s |" % (k[0], k[1], fmt(v, 2)))
    a("")
    # ---------------- procedures
    a("## 사용 순서")
    a("")
    a("### 0. 준비 (한 번)")
    a("")
    a("1. 네 개를 출력한다(위 표). 지그는 프레임과 같은 층 설정으로.")
    a("2. Ø4.0 드릴(악기당 공구)로 지그 K·L 기둥 구멍과 가짜 레버 허브를 뚫는다(프레임 핀 보스와 같은 방법).")
    a("3. 건반 봉과 같은 Ø4 봉에서 %s(K) · %s(L) · %s(교정봉)를 자르고 끝을 줄로 다듬는다." % (fmt(jd["stub_K"], 1), fmt(jd["stub_L"], 1), fmt(jd["cal"], 1)))
    a("4. K 봉 토막을 왼쪽 K 기둥으로 밀어 넣어 오른쪽 막힌 벽까지. 왼쪽 끝에 마스킹 테이프 한 바퀴(빠짐 방지).")
    a("5. 가짜 레버: 강철 블록 한 개를 +X 면에서 주머니에 눌러 끼운다(스냅 립). L 봉 토막을 왼쪽 L 기둥 → 허브 → 오른쪽 막힌 벽까지 민다. 가짜 레버가 제 무게로 자유롭게 도는지 본다.")
    a("6. 예비 밸런스 핀 1개를 지그 핀 구멍(X 0)에 T3으로 눌러 넣는다(아래 T3 순서). 이것이 T3의 첫 검증이다.")
    a("7. **교정**: 건반이 없는 지그의 백 영점 받침(CAL W, X ±%s~%s) 홈에 교정봉을 가로로 놓고 가짜 레버를 내려놓는다. 바늘 윗면이 읽기 턱과 손톱으로 같은 높이면 끝. "
      "다르면 높은 쪽(바늘 윗면 또는 턱 윗면)을 사포질해 맞춘다(한 번). 흑 영점 받침(CAL B)에서도 같은지 본다 — 차이가 흑 1/8회전(%s mm)보다 크면 가짜 레버 밑면을 평평하게 다듬는다."
      % (fmt(jd["pad_x"][0], 1), fmt(jd["pad_x"][1], 1), fmt(b["per8"], 2)))
    a("")
    a("### 1. 밸런스 핀 누르기 (T3, 프레임마다, 조립 1단계)")
    a("")
    a("1. 왼쪽 핀부터 차례로. 핀 한 개를 구멍에 손으로 세운다(이웃 오른쪽 핀은 아직 꽂지 않는다 — 서 있는 핀이 게이지 홈을 막음).")
    a("2. 게이지를 누름 구멍이 핀 위에 오게 얹고 울타리를 레일 앞면에 댄다.")
    a("3. 발이 레일 윗면에 닿을 때까지 엄지로, 빡빡하면 작은 바이스로 천천히 누른다(발이 닿으면 끝). **망치로 치지 않는다**: 압입 상한 80 N에서도 Ø2 핀 끝이 누름 구멍의 멈춤 면을 약 25~40 MPa로 누르고, 망치 충격은 PETG 항복을 넘어 멈춤 면이 파인다(그러면 핀이 모두 낮게 들어감).")
    a("4. **누른 핀은 바로, 오른쪽 이웃 핀을 꽂기 전에** GO/NO-GO로 본다(r4.4 고침 2): 게이지를 +X로 옮겨 방금 누른 핀이 왼쪽 끝 |<GO로 들어오게 레일을 따라 민다. **GO 구간은 핀 위로 지나가고 NO-GO 턱에서 멈춰야 합격**(꼭대기 z%s~%s). "
      "왼쪽의 이미 누른 핀들은 게이지 밖(피치 ≥ 13.05)이고 오른쪽 핀은 아직 없으므로 다른 핀에 걸리지 않는다. 모듈을 잇기 전, 프레임 한 장씩 한다."
      % (fmt(gd["nogo"], 2), fmt(gd["go"], 2)))
    a("   - 핀을 모두 누른 뒤에는 이 확인을 할 수 없다: 게이지 끝을 한 핀에 대면 두 칸 옆 핀이 가운데 누름 블록에, 또는 다른 핀이 반대쪽 NO-GO에 걸려, 낮은 핀도 ‘NO-GO에서 멈춤’으로 보인다.")
    a("   - GO에서 막힘 = 핀이 높다 → 누름 구멍으로 다시 누른다. NO-GO를 지나감 = 핀이 낮다 → 펜치로 조금 뽑아 다시 누른다.")
    a("   - 여러 핀이 연달아 낮으면 누름 구멍의 멈춤 면이 눌려 파인 것이다 → T3 다시 출력(약 %s분)." % fmt(prn["pin_gauge"]["time_min"], 0))
    a("")
    a("### 2. 건반마다 높이와 캡스턴 (T1 + T2, 조립 2단계)")
    a("")
    a("1. 가짜 레버를 주차 기둥에 젖혀 둔다. 건반 노치를 K 봉 토막에 스냅으로 끼우고 밸런스 핀 홈이 지그 핀에 오게 한다. 쉼 펠트(1.5T)와 펀칭 2장(설계 값)을 붙여 둔다.")
    a("2. 처음 한 번만: 캡스턴(M3×6 버튼헤드 + 너트 트랩)을 머리 밑이 빔에서 약 1.9 뜨게 돌려 둔다.")
    a("3. 가짜 레버를 내려 캡스턴에 얹는다 — 건반이 실제 쉼 하중으로 선반에 앉는다. 손으로 건반을 누르지 않는다.")
    a("4. **높이**: 높이 블록을 받침판에 세워 건반 머리 옆면(백 y≈0~16 / 흑 y≈58~74)에 붙이고 손톱으로 +/− 땅을 본다. 높으면 펀칭 1장 더, 낮으면 1장 뺀다(한 장 = 앞 %s). "
      "펀칭을 바꿀 때는 가짜 레버를 젖히고 건반을 뺀다." % fmt(pf, 2))
    a("5. **캡스턴**: 가짜 레버를 내린 채 바늘과 읽기 턱을 손톱으로 비교한다. 바늘이 낮으면 캡스턴을 1/8회전씩 풀고(올림), 높으면 조인다. 돌릴 때는 가짜 레버를 주차 기둥으로 젖히고 육각 렌치 2.0을 위에서 넣는다. "
      "1/8회전 = 바늘 %s(백) / %s(흑) mm." % (fmt(w["per8"], 2), fmt(b["per8"], 2)))
    a("6. 높이를 먼저, 캡스턴을 나중에 한다(펀칭은 건반 각도를 바꿔 캡스턴 높이도 바꾼다. 캡스턴은 쉼 하중을 바꾸지 않는다).")
    a("7. 가짜 레버를 젖히고 건반을 위로 당겨 뺀다(노치 스냅 1~2 N). 다음 건반.")
    a("")
    a("## 출력 검증 (검사 형상)")
    a("")
    a("| 공구 | 검사 | 합격 | 불합격이면 |")
    a("|---|---|---|---|")
    a("| 지그 | 캘리퍼: 밑면 → K 봉 토막 윗면 %s, 밑면 → 쉼 선반 윗면 %s, 밑면 → 영점 홈 바닥 %s, 밑면 → 읽기 턱 %s | 각 ±0.05 | 프레임도 같은 설정이면 같은 쪽으로 틀린다(건반끼리는 고름). 프레임과 다르게 뽑았다면 선반을 다시 출력 |"
      % (fmt(K[1] + 2.0 - Z_DATUM, 2), fmt(Z_SHELF - Z_DATUM, 2), fmt(jd["z_zero"] - Z_DATUM, 2), fmt(dd["z_led"] - Z_DATUM, 2)))
    a("| 지그 + 가짜 레버 | 교정봉을 영점 받침에(백·흑) → 바늘과 턱이 손톱으로 같은 높이 | 두 자리 모두 같은 높이 (차이 < 흑 1/8회전 %s) | 높은 쪽 사포질 (0단계 7) |" % fmt(b["per8"], 2))
    a("| 높이 블록 | 캘리퍼: 밑면 → 땅 W+ %s · W− %s · B+ %s · B− %s | 각 ±0.03 | 층 0.05 구간 설정 확인 후 다시 출력 |"
      % tuple(fmt(z - Z_PLATE, 2) for _, _, _, z in hd["lands"]))
    a("| 핀 게이지 | 캘리퍼 깊이 막대: 발 면 → 누름 구멍 바닥 %s, GO 천장 %s, NO-GO 천장 %s. 지그 핀을 누른 뒤 GO 통과·NO-GO 멈춤 | ±0.05, GO/NO-GO 합격 | 다시 출력 |"
      % (fmt(PIN_TOP - Z_RAIL, 2), fmt(gd["go"] - Z_RAIL, 2), fmt(gd["nogo"] - Z_RAIL, 2)))
    a("")
    a("## 주의")
    a("")
    a("- **F·F# 부분 착지**: 프레임에서는 USB 선반 홈 때문에 F·F# 쉼 펠트가 일부만 앉아 앞이 약 0.1 mm 높게 쉰다(DESIGN §1d, 이슈 2). 지그 선반은 온전하므로 이 차이는 창(±%s) 안에 남는다. "
      "이슈 2의 결과로 차이가 0.15를 넘으면 F·F#만 창의 낮은 쪽(− 땅 바로 위)으로 맞춘다." % fmt(HB_WIN, 2))
    a("- 지그는 프레임 한 대의 자리만 재현한다. 7개 모듈 프레임의 출력 차이(선반·받침 높이)는 지그가 없앨 수 없다 — 모든 프레임과 지그를 같은 프린터·같은 층 설정으로 뽑는다.")
    a("- 가짜 레버는 펠트가 없어 캡스턴에 단단히 닿는다. 기준 높이는 **정착 쉼** 꼭대기다: 지그 위 건반도 프레임과 같은 K 봉·쉼 선반·레버 모멘트에 얹혀 노치 천·쉼 펠트에 가라앉으므로, "
      "모델(4-DOF 쉼 상태)의 꼭대기 백 z%s · 흑 z%s(건반 좌표 z%s보다 %s / %s 낮음)의 가운데 z%s를 가짜 레버 밑면·영점 받침 면으로 썼다(백 %+.3f, 흑 %+.3f mm = 1/8회전의 %s / %s). "
      "r4.4 고침 2까지의 z%s 기준은 캡스턴을 백 %s · 흑 %s mm(1/8회전 %s / %s번) 높게 맞춰 업스톱 틈이 −0.40 → 약 −0.73(백)이 되었다(r4.4 검증)."
      % (fmt(SETTLE["white"]["crown"], 3), fmt(SETTLE["black"]["crown"], 3), fmt(Z_C_KEY, 1), fmt(Z_C_KEY - SETTLE["white"]["crown"], 3), fmt(Z_C_KEY - SETTLE["black"]["crown"], 3), fmt(Z_C, 2),
         Z_C - SETTLE["white"]["crown"], Z_C - SETTLE["black"]["crown"], fmt(abs(Z_C - SETTLE["white"]["crown"]) / TURN8, 2), fmt(abs(Z_C - SETTLE["black"]["crown"]) / TURN8, 2),
         fmt(Z_C_KEY, 1), fmt(Z_C_KEY - SETTLE["white"]["crown"], 3), fmt(Z_C_KEY - SETTLE["black"]["crown"], 3), fmt((Z_C_KEY - SETTLE["white"]["crown"]) / TURN8, 2), fmt((Z_C_KEY - SETTLE["black"]["crown"]) / TURN8, 2)))
    a("- 끝 부속 건반(A0·A#0·B0·C8)도 같은 지그를 쓴다: 지그의 틈 검사에 넣었고(K 기둥은 끝 부속까지 가장 넓은 꼬리 ±%s 밖), 캡스턴 y가 %s라 모듈 값(%s / %s)과 %s mm 안 — 영점 받침·확대비가 그대로다."
      % (fmt(ENV["at_rod"], 2), ", ".join("%s %s" % (k, fmt(v, 2)) for k, v in END_CAPS.items()), fmt(CAPS["white"], 2), fmt(CAPS["black"], 2),
         fmt(max(min(abs(v - CAPS["white"]), abs(v - CAPS["black"])) for v in END_CAPS.values()), 2)))
    a("- 모델이 바뀌면 `MODEL_DIR=<폴더> scratchpad/venv/bin/python tools/make_tools.py`로 다시 만든다(치수·STL·이 문서).")
    a("")
    a("## 파일")
    a("")
    a("- `make_tools.py` — 생성기 (모델: `%s`)" % MODEL_DIR)
    a("- `tools_geometry.json` — 치수(T01~T%02d), 공구별 옆모습(side, (y, z) + X 범위)·평면(plan, (X, y) + z 범위), 가짜 레버 주차 자세, 하중·확대비, 틈 검사" % len(DIMS))
    a("- `stl/tool_bench_jig.stl`, `stl/tool_height_block.stl`, `stl/tool_capstan_gauge.stl`, `stl/tool_pin_gauge.stl` — 베드 방향으로 놓인 출력 파일")
    a("- `scad/*.scad` — OpenSCAD 원본, `png/tool_*.png` — 출력 방향 렌더, `png/view_*.png` · `png/assembly_use.png` — 쓰는 자세, `png/check_side.png` — 지그 + 가짜 레버 + 건반 D·C# 옆모습 겹침, T3 + 프레임 레일")
    open(os.path.join(OUT, "tools.md"), "w").write("\n".join(L_) + "\n")


if __name__ == "__main__":
    main()
