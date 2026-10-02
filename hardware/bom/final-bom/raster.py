"""Rasterise each drawing used by the page: crop to the area around all its zone boxes (plus context),
render with resvg, save as WebP.  Writes raster/<name>.webp and raster/crops.json {file: [x, y, w, h, px_w, px_h]}.
Run with the venv python (resvg_py + PIL):  PY raster.py results.json"""
import json, os, re, sys, io
import resvg_py
from PIL import Image

F = os.path.dirname(os.path.abspath(__file__))
RES = json.load(open(sys.argv[1]))
OUT = os.path.join(F, "raster")
os.makedirs(OUT, exist_ok=True)
MAXW = 2200          # output pixel width cap
MAXPX = 9_000_000    # total pixel cap per image
crops = {}
for v in RES["views"]:
    f = v["file"].split("/")[-1]
    boxes = [z["box"] for z in v.get("zones", []) if z["box"][2] > 0 and z["box"][3] > 0]
    if not boxes:
        continue
    vx, vy, vw, vh = [float(x) for x in v["viewBox"]]
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
    # context margin: at least 12 % of the view, and keep the full width for narrow drawings
    mx = max(0.12 * vw, 0.25 * (x1 - x0)); my = max(0.12 * vw, 0.25 * (y1 - y0))
    cx = max(vx, x0 - mx); cy = max(vy, y0 - my)
    cx1 = min(vx + vw, x1 + mx); cy1 = min(vy + vh, y1 + my)
    if (cx1 - cx) > 0.7 * vw:
        cx, cx1 = vx, vx + vw
    if (cy1 - cy) > 0.8 * vh:
        cy, cy1 = vy, vy + vh
    cw, ch = cx1 - cx, cy1 - cy
    scale = min(MAXW / cw, (MAXPX / (cw * ch)) ** 0.5, 6.0)
    pw = int(round(cw * scale))
    s = open(os.path.join(F, "views", f), encoding="utf-8").read()
    root = re.search(r"<svg\b[^>]*>", s).group(0)
    root2 = re.sub(r'viewBox="[^"]+"', 'viewBox="%g %g %g %g"' % (cx, cy, cw, ch), root)
    root2 = re.sub(r'\swidth="[^"]+"', "", root2)
    root2 = re.sub(r'\sheight="[^"]+"', "", root2)
    s2 = s.replace(root, root2, 1)
    png = bytes(resvg_py.svg_to_bytes(svg_string=s2, width=pw, background="#ffffff"))
    im = Image.open(io.BytesIO(png)).convert("RGB")
    name = os.path.splitext(f)[0] + ".webp"
    im.save(os.path.join(OUT, name), "WEBP", quality=82, method=6)
    crops[f] = [round(cx, 2), round(cy, 2), round(cw, 2), round(ch, 2), im.width, im.height, name]
    print(f, "crop", [round(cx), round(cy), round(cw), round(ch)], "px", im.size, os.path.getsize(os.path.join(OUT, name)) // 1024, "KB")
json.dump(crops, open(os.path.join(OUT, "crops.json"), "w"), indent=1)
