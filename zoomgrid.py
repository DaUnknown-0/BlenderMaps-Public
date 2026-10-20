# zoomgrid.py <map> x0 y0 x1 y1 <out> [scale] [step]: Ausschnitt mit feinem Weltraster (Beschriftung je Linie)
import sys
import numpy as np
from PIL import Image, ImageDraw
from bm_ref import Ref
key, x0, y0, x1, y1, out = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6]
sc = float(sys.argv[7]) if len(sys.argv) > 7 else 8
st = float(sys.argv[8]) if len(sys.argv) > 8 else 0.1
r = Ref(key)
im = r.crop_full(x0, y0, x1, y1) if len(sys.argv) > 9 and sys.argv[9] == "full" else r.crop(x0, y0, x1, y1)
im = im.resize((int(im.width * sc), int(im.height * sc)), Image.NEAREST)
d = ImageDraw.Draw(im)
for gx in np.arange(np.ceil(x0 / st) * st, x1, st):
    X = (gx - x0) * r.ppu * sc
    d.line([(X, 0), (X, im.height)], fill=(255, 0, 0) if abs(gx * 2 - round(gx * 2)) < 1e-6 else (255, 150, 150), width=1)
    d.text((X + 2, 2), f"{gx:.2f}", fill=(255, 255, 0))
for gy in np.arange(np.ceil(y0 / st) * st, y1, st):
    Y = (y1 - gy) * r.ppu * sc
    d.line([(0, Y), (im.width, Y)], fill=(0, 80, 255) if abs(gy * 2 - round(gy * 2)) < 1e-6 else (150, 170, 255), width=1)
    d.text((2, Y + 2), f"{gy:.2f}", fill=(255, 255, 0))
im.save(out)
print(im.size)
