# wallcheck.py <karte> <out.jpg> [pro Raum]: Augenhoehen-Rundblicke (4 Richtungen) von mehreren begehbaren Punkten je
# Raum; zaehlt je Bild Himmel-/Hintergrundpixel (Loecher in Waenden/Boeden/Decken) und fast schwarze Flaechen
# (Konturhuellen von innen, texturlose Teile). Kontaktbogen der schlimmsten Ansichten, Liste auf der Konsole und als
# <out>.json (Standpunkte zum Nachrendern mit shots.py).
import json, math, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import shapely
from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon
from shapely.ops import polylabel, unary_union
from bm_ref import ROOT
from bm_scene import Scene

key, out = sys.argv[1], sys.argv[2]
per_room = int(sys.argv[3]) if len(sys.argv) > 3 else 3
doc = json.loads((ROOT / "out" / key / "scene.json").read_text(encoding="utf-8"))
sc = Scene(key); sc.build_plan()
obst = []
for m in doc["meshes"]:
    if m["kind"] != "parts":
        continue
    for q in m["parts"]:
        if "pts" in q and len(q["pts"]) >= 3 and q.get("z0", 0) < 1.0:
            obst.append(Polygon(q["pts"]).buffer(0))
        elif q.get("type") in ("lathe", "cyl") and "c" in q:
            r_ = max(pt[0] for pt in q["prof"]) if "prof" in q else q.get("r", 0.3)
            obst.append(Point(q["c"]).buffer(r_))
obst = unary_union(obst) if obst else Polygon()
walk = sc.walk_real().difference(obst.buffer(0.15)).buffer(0)
shapely.prepare(walk)
rng = np.random.default_rng(7)
views = []
sky_rooms = set()
for name, g in sorted(sc.rooms.items()):
    big = max(getattr(g, "geoms", [g]), key=lambda q: q.area)
    if big.area < 0.5:
        continue
    free = big.intersection(walk).buffer(0)
    if free.is_empty or free.area < 0.1:
        continue
    pts = []
    fb = max(getattr(free, "geoms", [free]), key=lambda q: q.area)
    pl = polylabel(fb, tolerance=0.05)
    pts.append((pl.x, pl.y))
    x0, y0, x1, y1 = free.bounds
    tries = 0
    while len(pts) < per_room and tries < 400:
        tries += 1
        p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if shapely.contains_xy(free, p[0], p[1]) and all(math.dist(p, q) > 1.0 for q in pts):
            pts.append(p)
    z = getattr(sc, "auto_z", {}).get(name, 0.0)
    for m in doc["meshes"]:
        if m.get("coll") == name and m.get("zlift"):
            z = m["zlift"]
            break
    for j, c in enumerate(pts):
        for yaw in (90, 0, 180, 270):
            views.append({"name": f"{name}_{j}_{yaw}", "room": name, "pos": [round(c[0], 2), round(c[1], 2), round(z + 0.62, 2)],
                          "yaw": yaw, "pitch": -4, "fov": 90, "res": [320, 180]})
views.append({"name": "_sky", "room": "", "pos": [0, 0, 300], "yaw": 90, "pitch": 60, "fov": 60, "res": [64, 36]})
tmp = Path(tempfile.mkdtemp())
(tmp / "v.json").write_text(json.dumps(views))
B = r"C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe"
subprocess.run([B, "-b", str(ROOT / "out" / key / f"{key}.blend"), "-P", str(ROOT / "blender" / "bm_views.py"), "--",
                str(tmp / "v.json"), str(tmp)], capture_output=True)
sky = np.asarray(Image.open(tmp / "_sky.png").convert("RGB")).reshape(-1, 3)
skycol = np.median(sky, axis=0)
res = []
for v in views[:-1]:
    f = tmp / f"{v['name']}.png"
    if not f.exists():
        continue
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
    issky = np.abs(a - skycol).sum(-1) <= 8
    isblack = a.max(-1) < 22
    # Himmel oben im Bild ist bei offenen Raeumen normal: nur Himmel in der unteren Bildhaelfte zaehlt voll
    h = a.shape[0]
    low = issky[h // 2:].mean()
    v["sky"] = round(float(issky.mean()), 3)
    v["sky_low"] = round(float(low), 3)
    v["black"] = round(float(isblack.mean()), 3)
    v["score"] = round(float(low * 2 + issky.mean() * 0.3 + isblack.mean()), 3)
    res.append(v)
res.sort(key=lambda v: -v["score"])
Path(out).with_suffix(".json").write_text(json.dumps(res, indent=0))
worst = [v for v in res if v["score"] > 0.08][:24]
TW, TH = 320, 180
cols = 4
rows = max(1, (len(worst) + cols - 1) // cols)
sheet = Image.new("RGB", (cols * TW, rows * TH))
for i, v in enumerate(worst):
    im = Image.open(tmp / f"{v['name']}.png").convert("RGB")
    ImageDraw.Draw(im).text((4, 4), f"{v['name']} sky{v['sky']:.2f} low{v['sky_low']:.2f} bl{v['black']:.2f}", fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * TW, (i // cols) * TH))
sheet.save(out, quality=85)
by_room = {}
for v in res:
    by_room.setdefault(v["room"], []).append(v)
print(f"{len(res)} Ansichten, Himmel {skycol.astype(int).tolist()}")
for r, vs in sorted(by_room.items(), key=lambda kv: -max(v["score"] for v in kv[1])):
    w = max(vs, key=lambda v: v["score"])
    if w["score"] > 0.05:
        print(f"{r:18s} max {w['score']:.2f} ({w['name']} pos {w['pos']}) himmel unten {w['sky_low']:.2f} schwarz {w['black']:.2f}")
