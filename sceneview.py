# sceneview.py <map> <out.jpg> [scale] [x0 y0 x1 y1]: Boden je Raum, Kappe und Kantenarten der Szene ueber dem Kartenfoto
import sys, random
from PIL import Image, ImageDraw
from bm_scene import Scene
key, out = sys.argv[1], sys.argv[2]
scale = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
sc = Scene(key); sc.build_plan(); r = sc.ref
im = r.image.copy().convert("RGBA"); ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
rnd = random.Random(5)
for n, g in sc.rooms.items():
    col = (rnd.randint(60, 255), rnd.randint(60, 255), rnd.randint(60, 255), 90)
    for pg in getattr(g, "geoms", [g]):
        d.polygon([r.w2p(*p) for p in pg.exterior.coords], fill=col)
        for h in pg.interiors:
            d.polygon([r.w2p(*p) for p in h.coords], fill=(0, 0, 0, 0), outline=(255, 0, 0, 255))
    c = g.representative_point(); d.text(r.w2p(c.x, c.y), n, fill=(255, 255, 255, 255))
for pg in getattr(sc.cap, "geoms", [sc.cap]):
    d.polygon([r.w2p(*p) for p in pg.exterior.coords], fill=(255, 255, 0, 110))
for hp in sc.props_fp:
    d.polygon([r.w2p(*p) for p in hp.exterior.coords], outline=(255, 140, 0, 255), width=4)
KC = {"north": (255, 60, 60, 255), "side": (60, 200, 255, 255), "open": (80, 255, 80, 255)}
for e in sc.wall_edges():
    d.line([r.w2p(*e["a"]), r.w2p(*e["b"])], fill=KC[e["kind"]], width=3)
im.alpha_composite(ov)
if len(sys.argv) > 7:
    x0, y0, x1, y1 = map(float, sys.argv[4:8])
    p0, p1 = r.w2p(x0, y1), r.w2p(x1, y0)
    im = im.crop((int(p0[0]), int(p0[1]), int(p1[0]), int(p1[1])))
im.convert("RGB").resize((int(im.width * scale), int(im.height * scale))).save(out, quality=88)
