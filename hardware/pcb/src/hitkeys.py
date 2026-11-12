"""Click targets of the board / wiring drawings BRD-01 ~ BRD-07 (the page's 'sheet hits').

A sheet function only says WHERE something is and WHICH thing it is: s.hits_keys = [{k, g, key, n, m, q, r} ...] in sheet mm.
The texts are not written here - hits.py takes them from the 3D model's info (model3d.py: bom.csv, cables.csv, harness.csv, the
pad <-> wire links), so a wire or a pad says the same thing on a drawing and in the 3D model.

  k 'p' pad (g = [x, y], r), 'w' wire (g = [[[x, y] ...] ...]), 'r' box (g = [x0, y0, x1, y1])
  key  info key of the 3D model ('U201.3', 'SBW-4', 'A501', 'W602c', 'PCB-SB' ...); or t / d given here for things only a drawing has
  n    net, m scope of the net ('EL', 'PED', 'CU' ...: the text of 'GND' differs per board), q one more line for this item only
  lo   1 = background (the printed parts around the circuit): picked only when nothing else is under the pointer
build.py copies the list into netlist/sheethits.json ('keys'); hits.key_items() resolves it.
"""
import re


def r2(v):
    return round(float(v), 2)


def real(net):
    """None for what is not a net: NC pins, unnamed single nets ('~...', 'N1'), 'do not connect'."""
    if not net or net == "NC" or net.startswith(("~", "연결 금지", "(이름 없음")) or re.fullmatch(r"N\d+", net):
        return None
    return net.split(" (")[0]


class Keys:
    """collects click targets of one drawing area; X, Y = that area's model -> sheet transform."""

    def __init__(self, s, X=None, Y=None, m=None):
        self.X, self.Y, self.m = X, Y, m
        if not hasattr(s, "hits_keys"):
            s.hits_keys = []
        self.out = s.hits_keys

    def _add(self, it, key, n, q, t, d, m=None):
        if key:
            it["key"] = key
        if t:
            it["t"] = t
        if d:
            it["d"] = list(d)
        if q:
            it["q"] = q
        n = real(n)
        if n:
            it["n"] = n
            if m or self.m:
                it["m"] = m or self.m
        self.out.append(it)
        return it

    # ---- model coordinates
    def pad(self, x, y, key, n=None, r=1.0, q=None, t=None, d=None):
        return self._add(dict(k="p", g=[r2(self.X(x)), r2(self.Y(y))], r=r), key, n, q, t, d)

    def wire(self, pts, key=None, n=None, q=None, t=None, d=None):
        return self._add(dict(k="w", g=[[[r2(self.X(x)), r2(self.Y(y))] for x, y in pts]]), key, n, q, t, d)

    def box(self, x0, y0, x1, y1, key=None, n=None, q=None, t=None, d=None, grow=0.0):
        xs, ys = sorted((self.X(x0), self.X(x1))), sorted((self.Y(y0), self.Y(y1)))
        return self._add(dict(k="r", g=[r2(xs[0] - grow), r2(ys[0] - grow), r2(xs[1] + grow), r2(ys[1] + grow)]), key, n, q, t, d)

    # ---- sheet coordinates
    def sbox(self, x0, y0, x1, y1, key=None, n=None, q=None, t=None, d=None, m=None):
        return self._add(dict(k="r", g=[r2(min(x0, x1)), r2(min(y0, y1)), r2(max(x0, x1)), r2(max(y0, y1))]), key, n, q, t, d, m)

    def swire(self, pts, key=None, n=None, q=None, t=None, d=None, m=None):
        return self._add(dict(k="w", g=[[[r2(x), r2(y)] for x, y in pts]]), key, n, q, t, d, m)


def clip_line(pts, box):
    """the pieces of a polyline inside box = (x0, x1, y0, y1) (Liang-Barsky per segment)."""
    x0, x1, y0, y1 = box
    out, cur = [], []
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t0, t1, ok = 0.0, 1.0, True
        for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if abs(p) < 1e-12:
                if q < 0:
                    ok = False
                    break
            else:
                t = q / p
                if p < 0:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
        if not ok or t0 > t1:
            if len(cur) > 1:
                out.append(cur)
            cur = []
            continue
        p0, p1 = (a[0] + dx * t0, a[1] + dy * t0), (a[0] + dx * t1, a[1] + dy * t1)
        if not cur or abs(cur[-1][0] - p0[0]) > 1e-6 or abs(cur[-1][1] - p0[1]) > 1e-6:
            if len(cur) > 1:
                out.append(cur)
            cur = [p0]
        cur.append(p1)
        if t1 < 1.0:
            if len(cur) > 1:
                out.append(cur)
            cur = []
    if len(cur) > 1:
        out.append(cur)
    return out


# ---------------------------------------------------------------------- CAD part id -> the thing's key in the circuit
# circuit parts drawn from the CAD (centre unit): what they are comes from bom.csv / netlist.csv under their refdes
CAD_REF = {"BAT-LFP": "BT601", "C-XT60": "X605", "CU-E-FUSE": "F601", "CU-E-SWITCH": "SW601", "CU-E-BUCK": "A602", "CU-E-PI5": "A603",
           "PB-E-HUB": "A604", "CU-E-AMP": "A702", "CU-E-DONGLE": "A701", "CU-E-GENDER": "X701", "C-XT60F-L": "X704", "C-XT60M-L": "X703",
           "C-XT60F-R": "X706", "C-XT60M-R": "X705"}
# cables drawn from the CAD -> their W number (cables.csv / harness.csv)
WID_OF = {"C-BAT-LEAD": "BAT-LEAD", "C-BAT-DC": "BAT-DC", "C-PWR-IN": "W601", "C-PWR-FUSE": "W602a", "C-PWR-5V": "W603", "C-SPK-L": "W703",
          "C-SPK-R": "W705", "C-SPKPIG-L": "W704", "C-SPKPIG-R": "W706", "C-USB-PED": "W208", "C-USB-UPSTREAM": "W209",
          "TS-C-DSI": "W605", "TS-C-PWR-RED": "W608", "TS-C-PWR-BLK": "W608"}
# the small boards and what sits on them (drawn in detail elsewhere)
CAD_BOARD = {"CU-E-PEDBOARD": "PCB-PB", "CU-E-PEDZERO": "A501", "CU-E-J702BOARD": "PCB-J702", "CU-E-J702": "J702",
             "CU-E-J501BOARD": "PCB-J501", "CU-E-J501": "J501"}


def cad_key(pid, kind=None):
    """info key of a CAD part of the centre unit (BRD-04)."""
    if kind in ("print", "plywood"):
        return "CTX-" + pid
    m = re.fullmatch(r"O(\d)-C-USB", pid)
    if m:
        return "W20" + m.group(1)
    return CAD_REF.get(pid) or WID_OF.get(pid) or CAD_BOARD.get(pid) or pid


def cad_is_cable(pid):
    return pid.startswith(("C-", "TS-C")) and pid not in CAD_REF and pid != "C-DC" or pid.endswith("-C-USB")


def end_key(ref):
    """the part at one end of a harness lead ('O1 J302', 'SW601-1 · 2', 'A602 OUT+ · OUT−', 'J702 기판', 'PS') -> info key."""
    if ref.strip() == "PS":
        return "PCB-PS"
    m = re.search(r"[A-Z]{1,3}\d{3}", ref)
    return m.group(0) if m else None


def lead_scope(h):
    """scope of the nets of a harness lead (which board's 'GND' text applies)."""
    if h["id"] in ("W401",):
        return "EL"
    if h["id"] in ("W411",):
        return "ER"
    if h["id"] in ("W501", "W502"):
        return "PED"
    if h.get("part") in ("pwr", "aud", "ts"):
        return "CU"
    return None
