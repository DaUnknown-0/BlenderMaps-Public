# review.py <out.jpg> <karte:raum> ... : Original | Blender (Vergleichsrender) je Raum untereinander, Breite 900
import json
import sys
from PIL import Image, ImageDraw
from bm_ref import Ref

out = sys.argv[1]
rows = []
refs = {}
for spec in sys.argv[2:]:
    key, room = spec.split(":")
    r = refs.get(key) or refs.setdefault(key, Ref(key, full=True))
    bl = Image.open(f"out/{key}/cmp/{room}_bl.png").convert("RGB")
    bb = json.load(open(f"out/{key}/cmp/{room}_bl.json"))["bbox"]
    o = r.crop(*bb).resize(bl.size)
    s = 445 / bl.width
    W, H = 445, max(2, int(bl.height * s))
    if H > 330:
        s = 330 / bl.height
        W, H = int(bl.width * s), 330
    row = Image.new("RGB", (900, H + 16), (30, 30, 30))
    row.paste(o.resize((W, H)), (0, 16))
    row.paste(bl.resize((W, H)), (455, 16))
    ImageDraw.Draw(row).text((4, 2), spec, fill=(255, 255, 0))
    rows.append(row)
img = Image.new("RGB", (900, sum(r.height for r in rows)))
y = 0
for r in rows:
    img.paste(r, (0, y))
    y += r.height
img.save(out, quality=88)
