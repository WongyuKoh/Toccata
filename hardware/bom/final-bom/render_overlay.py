"""Render an SVG drawing with highlight boxes on top, to check zone boxes by eye.

Usage:
  PY render_overlay.py <view.svg> <boxes.json | '-' for none> <out.png> [--width 1400] [--crop x,y,w,h]

boxes.json: [{"zone": "mod.steel", "box": [x, y, w, h]}, ...]  -- x,y,w,h in the SVG's ROOT user
coordinates (the viewBox system of the outer <svg>), exactly what the page will use.
Each box is drawn as a translucent red rectangle with its zone id written above it.
--crop renders only that viewBox region (zoom in on a detail).
"""
import sys, json, re, html
import resvg_py

args = sys.argv[1:]
svg_path, boxes_arg, out = args[0], args[1], args[2]
width = 1400
crop = None
if "--width" in args:
    width = int(args[args.index("--width") + 1])
if "--crop" in args:
    crop = [float(v) for v in args[args.index("--crop") + 1].split(",")]
s = open(svg_path, encoding="utf-8").read()
boxes = [] if boxes_arg == "-" else json.load(open(boxes_arg)) if not boxes_arg.startswith("[") else json.loads(boxes_arg)
m = re.search(r"<svg\b[^>]*>", s)
root = m.group(0)
vb = re.search(r'viewBox="([^"]+)"', root)
vbv = [float(v) for v in re.split(r"[ ,]+", vb.group(1).strip())]
stroke = max(vbv[2], vbv[3]) / 700.0
fs = max(vbv[2], vbv[3]) / 90.0
ov = []
for b in boxes:
    x, y, w, h = b["box"]
    ov.append('<rect x="%g" y="%g" width="%g" height="%g" fill="#ff2d2d" fill-opacity="0.22" stroke="#ff0000" stroke-width="%g"/>' % (x, y, w, h, stroke))
    ov.append('<text x="%g" y="%g" font-size="%g" fill="#d00000" font-family="sans-serif" font-weight="bold">%s</text>' % (x, y - stroke * 1.5, fs, html.escape(b.get("zone", ""))))
s2 = s[: s.rindex("</svg>")] + "\n".join(ov) + "</svg>"
if crop:
    root2 = re.sub(r'viewBox="[^"]+"', 'viewBox="%g %g %g %g"' % tuple(crop), root)
    root2 = re.sub(r'\swidth="[^"]+"', "", root2)
    root2 = re.sub(r'\sheight="[^"]+"', "", root2)
    s2 = s2.replace(root, root2, 1)
png = resvg_py.svg_to_bytes(svg_string=s2, width=width, background="#ffffff")
open(out, "wb").write(bytes(png))
print("wrote", out, "viewBox", vbv)
