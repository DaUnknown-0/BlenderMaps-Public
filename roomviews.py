# roomviews.py <karte> <out.jpg> [eye]: je Raum eine Augenhoehen-Ansicht nach Norden (vom ruhigsten Bodenpunkt aus),
# als Kontaktbogen (4 Spalten, Raumname eingeblendet).
import json, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw
from shapely.ops import polylabel
from bm_ref import ROOT

key, out = sys.argv[1], sys.argv[2]
eye = float(sys.argv[3]) if len(sys.argv) > 3 else 0.62
doc = json.loads((ROOT / "out" / key / "scene.json").read_text(encoding="utf-8"))
from bm_scene import Scene
sc = Scene(key); sc.build_plan()
if sc.mapmod is not None and hasattr(sc.mapmod, "adjust"):
    pass
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
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
import math
import numpy as np
import shapely
walk = sc.floor.difference(obst.buffer(0.12)).buffer(0)
shapely.prepare(walk)


def fan(p, yaw):
    """mittlere freie Sichtweite (gedeckelt 9) in drei Strahlen um die Blickrichtung"""
    tot = 0.0
    for da in (-35, 0, 35):
        a = math.radians(yaw + da)
        t = np.arange(0.1, 9.0, 0.1)
        ok = shapely.contains_xy(walk, p[0] + np.cos(a) * t, p[1] + np.sin(a) * t)
        bad = np.nonzero(~ok)[0]
        tot += t[bad[0]] if len(bad) else 9.0
    return tot / 3


views = []
for name, g in sorted(sc.rooms.items()):
    big = max(getattr(g, "geoms", [g]), key=lambda q: q.area)
    if big.area < 0.5:
        continue
    free = big.difference(obst.buffer(0.3)).buffer(0)
    if free.is_empty or free.area < 0.2:
        free = big
    x0, y0, x1, y1 = free.bounds
    st = max(0.25, math.sqrt(free.area / 160))
    xs, ys = np.meshgrid(np.arange(x0 + st / 2, x1, st), np.arange(y0 + st / 2, y1, st))
    xs, ys = xs.ravel(), ys.ravel()
    inside = shapely.contains_xy(free, xs, ys)
    cands = list(zip(xs[inside], ys[inside])) or [(polylabel(big, tolerance=0.05).x, polylabel(big, tolerance=0.05).y)]
    scored = []
    for c in cands:
        if free.boundary.distance(Point(c)) < 0.25 and len(cands) > 6:
            continue
        for yaw in (90, 0, 180, 270):
            scored.append((fan(c, yaw) + (0.6 if yaw == 90 else 0.0), c, yaw))
    scored.sort(key=lambda t: -t[0])
    picks = scored[:1]
    if big.area > 8 and scored:
        alt = [t for t in scored if abs(((t[2] - picks[0][2]) + 180) % 360 - 180) >= 90
               and math.dist(t[1], picks[0][1]) > 0.8]
        if alt:
            picks.append(alt[0])
    z = getattr(sc, "auto_z", {}).get(name, 0.0)
    for m in doc["meshes"]:
        if m.get("coll") == name and m.get("zlift"):
            z = m["zlift"]
            break
    for j, (_, c, yaw) in enumerate(picks):
        views.append({"name": name + ("" if j == 0 else f"_{j}"), "pos": [c[0], c[1], z + eye], "yaw": yaw, "pitch": -6,
                      "fov": 90})
tmp = Path(tempfile.mkdtemp())
(tmp / "v.json").write_text(json.dumps(views))
Path(out).with_suffix(".json").write_text(json.dumps(views, indent=0))   # Standpunkte zum Nachrendern
B = r"C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe"
import os
EE = bool(os.environ.get("BM_EE"))                                  # BM_EE=1: mit Licht (EEVEE) statt Workbench
TW, TH = (480, 300) if EE else (320, 180)
if EE:
    for v in views:
        v["res"] = [TW * 2, TH * 2]
    (tmp / "v.json").write_text(json.dumps(views))
subprocess.run([B, "-b", str(ROOT / "out" / key / f"{key}.blend"), "-P",
                str(ROOT / "blender" / ("bm_eevee.py" if EE else "bm_views.py")), "--",
                str(tmp / "v.json"), str(tmp)] + (["16"] if EE else []), capture_output=True)
ims = []
for v in views:
    f = tmp / f"{v['name']}.png"
    if f.exists():
        im = Image.open(f).convert("RGB").resize((TW, TH))
        ImageDraw.Draw(im).text((4, 4), v["name"], fill=(255, 255, 0))
        ims.append(im)
cols = 4
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * TW, rows * TH))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * TW, (i // cols) * TH))
sheet.save(out, quality=85)
print(len(ims), "Ansichten")
