# zoomcol.py <map> x0 y0 x1 y1 <out.png> [scale]: Ausschnitt des Kartenfotos mit Collidern und Gitter (Weltkoordinaten)
import sys
from PIL import Image, ImageDraw
from bm_ref import Ref
key, x0, y0, x1, y1, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
sc = float(sys.argv[7]) if len(sys.argv) > 7 else 3
r = Ref(key)
im = r.crop(x0, y0, x1, y1)
im = im.resize((int(im.width * sc), int(im.height * sc)), Image.NEAREST).convert("RGB")
d = ImageDraw.Draw(im)
P = lambda p: ((p[0] - x0) * r.ppu * sc, (y1 - p[1]) * r.ppu * sc)
col = {"Ship": (255, 0, 0), "Shadow": (0, 170, 255), "ShortObjects": (0, 255, 0), "Objects": (255, 0, 255)}
for w, pts in r.colliders(("Ship", "Shadow", "ShortObjects", "Objects")):
    d.line([P(p) for p in pts], fill=col[w["layer"]], width=2)
import math
for gx in range(math.ceil(x0), math.floor(x1) + 1):
    d.line([P((gx, y0)), P((gx, y1))], fill=(255, 255, 255), width=1)
    d.text((P((gx, y1))[0] + 2, 2), str(gx), fill=(255, 255, 0))
for gy in range(math.ceil(y0), math.floor(y1) + 1):
    d.line([P((x0, gy)), P((x1, gy))], fill=(255, 255, 255), width=1)
    d.text((2, P((x0, gy))[1] + 2), str(gy), fill=(255, 255, 0))
im.save(out)
print(im.size)
