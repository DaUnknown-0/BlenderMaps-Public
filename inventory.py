# inventory.py <karte> [--csv datei]: jedes gezeichnete Einzelobjekt der Karte und wie es im Modell steht.
#   Arten: modell (Drehkoerper/Rohr/Netz/mehrteilig), kasten+bild (Prisma mit Sprite als Front/Oberseite), tafel
#   (Alpha-Tafel/Scheibe), wand (Wandplatte), flach (Bodenflicken), fehlt (kein Teil ueber der Bildflaeche).
import json
import sys
from collections import Counter

from shapely.geometry import Polygon, Point, box as sbox, LineString
from shapely.ops import unary_union

import bm_base
from bm_ref import Ref, ROOT

key = sys.argv[1]
ref = Ref(key)
doc = json.loads((ROOT / "out" / key / "scene.json").read_text(encoding="utf-8"))
mats = doc["materials"]
log = {l[0]: l[2] for l in json.loads((ROOT / "out" / key / "objects_log.json").read_text(encoding="utf-8"))} \
    if (ROOT / "out" / key / "objects_log.json").exists() else {}
parts = []
for m in doc["meshes"]:
    if m.get("kind") != "parts":
        continue
    for q in m["parts"]:
        t = q.get("type")
        try:
            if t == "prism":
                g = Polygon(q["pts"]).buffer(0)
            elif t == "lathe":
                g = Point(q["c"]).buffer(max(p[0] for p in q["prof"]))
            elif t == "mesh":
                xs = [v[0] for v in q["verts"]]; ys = [v[1] for v in q["verts"]]
                g = sbox(min(xs), min(ys), max(xs), max(ys))
            elif t == "tube":
                g = unary_union([LineString([a[:2], b[:2]]).buffer(q.get("r", 0.05)) for a, b in zip(q["pts"], q["pts"][1:])])
            else:
                continue
        except Exception:
            continue
        if g.is_empty:
            continue
        tex = any(mats.get(q.get(k), {}).get("image") for k in ("top", "front", "mat"))
        alpha = any(mats.get(q.get(k), {}).get("alpha") for k in ("top", "front", "mat"))
        z1 = q.get("z1", 1.0) if t == "prism" else (max(p[1] for p in q["prof"]) if t == "lathe" else 1.0)
        z0 = q.get("z0", 0.0) if t == "prism" else 0.0
        parts.append((m["name"], t, g, tex, alpha, z0, z1, q))
rows = []
for i, p in enumerate(ref.world["props"]):
    if bm_base.classify(key, p["path"]) != "object":
        continue
    (x0, y0), (x1, y1) = p["min"], p["max"]
    w, h = x1 - x0, y1 - y0
    if w < 0.08 or h < 0.08 or w * h > 60:
        continue
    fp = sbox(x0, y0, x1, y1)
    hits = [pp for pp in parts if pp[2].intersects(fp) and pp[2].intersection(fp).area > 0.2 * min(pp[2].area, fp.area)]
    meshes = Counter(pp[0] for pp in hits)
    kinds = Counter(pp[1] for pp in hits)
    if not hits:
        art = "fehlt"
    else:
        modeled = kinds.get("lathe", 0) + kinds.get("tube", 0) + kinds.get("mesh", 0)
        thin = all((pp[6] - pp[5]) < 0.03 for pp in hits)
        flat_alpha = any(pp[4] for pp in hits)
        if modeled >= 1 or len(hits) >= 4:
            art = "modell"
        elif thin:
            art = "flach"
        elif flat_alpha:
            art = "tafel"
        elif any(pp[7].get("front") and (pp[6] - pp[5]) > 0.3 and pp[2].area < 0.08 for pp in hits):
            art = "wand"
        else:
            art = "kasten+bild" if any(pp[3] for pp in hits) else "kasten"
    rows.append((i, p["path"].split("(Clone)/")[-1], round(w, 2), round(h, 2), art, log.get(i, ""), len(hits),
                 ",".join(sorted(set(m.split("_", 1)[0] for m in meshes)))))
c = Counter(r[4] for r in rows)
print(key, len(rows), dict(c))
for r in rows:
    print(f"{r[0]:4d} {r[4]:12s} {r[5]:22s} {r[6]:2d} {r[2]:5.2f}x{r[3]:5.2f} {r[1]}")
