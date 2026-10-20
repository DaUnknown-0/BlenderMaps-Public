# planview.py <map> <out.jpg> [hull r,g,b]: Grundriss (begehbar, je Raum eingefaerbt) ueber dem Kartenfoto
import sys, random
from PIL import Image, ImageDraw
from bm_ref import Ref
from bm_plan import Plan
key, out = sys.argv[1], sys.argv[2]
hull = tuple(int(v) for v in sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else None
r = Ref(key); pl = Plan(r, hull_color=hull)
print("geschlossen:", pl.closed)
rooms = pl.rooms()
im = r.image.copy().convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
rnd = random.Random(3)
for n, g in rooms.items():
    col = (rnd.randint(60, 255), rnd.randint(60, 255), rnd.randint(60, 255), 120)
    for pg in getattr(g, "geoms", [g]):
        d.polygon([r.w2p(*p) for p in pg.exterior.coords], fill=col, outline=(255, 255, 255, 255))
        for h in pg.interiors:
            d.polygon([r.w2p(*p) for p in h.coords], fill=(0, 0, 0, 0), outline=(255, 0, 0, 255))
    c = g.representative_point(); d.text(r.w2p(c.x, c.y), n, fill=(255, 255, 255, 255))
for x, y, c in pl.closed:
    px, py = r.w2p(x, y); d.ellipse([px - 6, py - 6, px + 6, py + 6], outline=(255, 0, 0, 255), width=3)
im.alpha_composite(ov)
scale = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
im.convert("RGB").resize((int(im.width * scale), int(im.height * scale))).save(out, quality=88)
