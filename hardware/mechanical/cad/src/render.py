"""PNG previews with OpenSCAD (import the assembly group STLs with their colours)."""
import json, os, subprocess, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))

def scad_for(groups, man):
    col = collections.OrderedDict()
    for p in man["parts"]:
        col.setdefault(p["group"], p["color"])
    lines = []
    for g in groups:
        f = os.path.join(OUT, "stl", "assembly", g.replace(" ", "_").replace("/", "·") + ".stl")
        if not os.path.exists(f):
            continue
        lines.append('color("%s") import("%s");' % (col.get(g, "#cccccc"), f))
    return "\n".join(lines)

def render(groups, png, camera, size=(1600, 900), extra="", view="axes"):
    """camera = 'eyex,eyey,eyez,cx,cy,cz' (world mm); view='axes' draws the axis cross, None/'' leaves it out."""
    man = json.load(open(os.path.join(OUT, "manifest.json")))
    if groups == "ALL":
        groups = list(collections.OrderedDict((p["group"], 1) for p in man["parts"]))
    src = scad_for(groups, man) + extra
    tmp = png + ".scad"
    open(tmp, "w").write(src)
    cmd = ["openscad", "--backend=manifold", "-o", png, "--imgsize=%d,%d" % size, "--camera=" + camera,
           "--colorscheme=Tomorrow"] + (["--view=" + view] if view else []) + ["--projection=p", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2000:])
    return png

if __name__ == "__main__":
    out = sys.argv[1]
    which = sys.argv[2]
    cam = sys.argv[3]
    groups = "ALL" if which == "ALL" else which.split(",")
    render(groups, out, cam)
