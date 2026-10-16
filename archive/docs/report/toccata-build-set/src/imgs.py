"""Normalise downloaded product photos: flatten on white, max 600 px, JPEG q80 -> report/img/<id>.jpg"""
import os, sys, json, glob
from PIL import Image
S = "/private/tmp/claude-501/-Users-kwg-Desktop-mydrive-project-Toccata/3546328f-6f85-459b-b398-b7404472305f/scratchpad"
SRC, DST = f"{S}/report/img_raw", f"{S}/report/img"
os.makedirs(SRC, exist_ok=True)
# move originals into img_raw once
for p in glob.glob(f"{DST}/*"):
    base = os.path.basename(p)
    if not os.path.exists(f"{SRC}/{base}"):
        os.replace(p, f"{SRC}/{base}")
    elif not base.endswith(".jpg") or os.path.getsize(p) > 150_000:
        os.remove(p)
done = {}
for p in sorted(glob.glob(f"{SRC}/*")):
    pid, ext = os.path.splitext(os.path.basename(p))
    try:
        im = Image.open(p)
        im.load()
    except Exception as e:
        print("BAD", p, e); continue
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((600, 600), Image.LANCZOS)
    out = f"{DST}/{pid}.jpg"
    im.save(out, "JPEG", quality=80, optimize=True, progressive=True)
    done[pid] = os.path.getsize(out)
print(len(done), "images,", sum(done.values()) // 1024, "KB")
