# Blindvergleich: 20 Standpunkte (je Vanilla-Karte 4 Raeume), gleiche Lage fuer NightfallWeb (look.py) und Blender.
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shapely.geometry import Point, Polygon
from shapely.ops import polylabel, unary_union
from bm_scene import Scene

PICK = {"skeld": ["Cafeteria", "Medical", "Storage", "Weapons"],
        "mira": ["Cafe", "Laboratory", "Reactor", "Office"],
        "polus": ["Office", "Science", "LifeSupport", "Electrical"],
        "airship": ["Vault", "Kitchen", "Records", "Engine"],
        "fungle": ["Cafeteria", "Greenhouse", "Laboratory", "Kitchen"]}
OUT = Path(__file__).resolve().parent
views = []
for key, rooms in PICK.items():
    sc = Scene(key); sc.build_plan()
    doc = json.loads((OUT.parent / "out" / key / "scene.json").read_text(encoding="utf-8"))
    obst = []
    for m in doc["meshes"]:
        if m["kind"] == "parts":
            for q in m["parts"]:
                if "pts" in q and len(q["pts"]) >= 3 and q.get("z0", 0) < 1.0:
                    obst.append(Polygon(q["pts"]).buffer(0))
    obst = unary_union(obst) if obst else Polygon()
    for name in rooms:
        g = sc.rooms[name]
        big = max(getattr(g, "geoms", [g]), key=lambda q: q.area)
        free = big.buffer(-0.35).difference(obst.buffer(0.4)).buffer(0)
        x0, y0, x1, y1 = big.bounds
        cand = None
        for f in (0.15, 0.25, 0.35, 0.5):                         # moeglichst weit im Sueden, Blick nach Norden
            yy = y0 + f * (y1 - y0)
            line = free.intersection(Polygon([(x0, yy - 0.05), (x1, yy - 0.05), (x1, yy + 0.05), (x0, yy + 0.05)]))
            if not line.is_empty and line.area > 0.02:
                pc = max(getattr(line, "geoms", [line]), key=lambda q: q.area).centroid
                cand = (pc.x, pc.y)
                break
        if cand is None:
            p = polylabel(big, 0.05)
            cand = (p.x, p.y)
        z = getattr(sc, "auto_z", {}).get(name, 0.0)
        views.append({"key": key, "room": name, "x": round(cand[0], 2), "y": round(cand[1], 2), "z": z})
(OUT / "views.json").write_text(json.dumps(views, indent=1))
print(len(views))
for v in views: print(v)
