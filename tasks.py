# tasks.py <karte> <aus_prefix>: je Konsole (Task) eine Nahaufnahme aus Spielersicht (Workbench): Kamera auf dem
# naechsten begehbaren Punkt 1,3 m vor der Konsole, Blick auf die Konsole. Kontaktboegen zu je 24 Bildern.
import json
import math
import os
import subprocess
import sys

from shapely.geometry import Point

from bm_ref import ROOT
from bm_scene import Scene

key, out = sys.argv[1], sys.argv[2]
sc = Scene(key)
sc.build_plan()
walk = sc.walk_real()
doc = json.loads((ROOT / "out" / key / "scene.json").read_text(encoding="utf-8"))
rz = {n: 0.0 for n in doc["rooms"]}
args = []
cams = []
for c in sc.ref.world.get("consoles", []):
    x, y = c["pos"]
    best = None
    # Standpunkt: Richtung mit dem meisten freien Raum hinter dem Spieler (Blick von der Raumseite auf die Konsole)
    for ang in range(0, 360, 15):
        free = 0.0
        for dist in (0.9, 1.2, 1.6, 2.0, 2.5, 3.0):
            px, py = x + dist * math.cos(math.radians(ang)), y + dist * math.sin(math.radians(ang))
            if walk.contains(Point(px, py)):
                free = dist
            else:
                break
        if free >= 0.9 and (best is None or free > best[0]):
            dist = min(1.5, free)
            best = (free, x + dist * math.cos(math.radians(ang)), y + dist * math.sin(math.radians(ang)), (ang + 180) % 360)
    if not best:
        continue
    _, px, py, yaw = best
    z = 0.0
    args.append(f"{c['name']}:{px:.2f},{py:.2f},{0.62 + z:.2f},{yaw},-6,70")
    cams.append({"name": c["name"], "room": c.get("room"), "pos": [x, y], "cam": [round(px, 2), round(py, 2), 0.62 + z, yaw, -6]})
per = 12
for s in range(0, len(args), per):
    env = dict(os.environ, BM_WB="1")
    subprocess.run([sys.executable, str(ROOT / "shots.py"), key, f"{out}_{s // per}.jpg"] + args[s:s + per], env=env)
(ROOT / "out" / key / "task_cams.json").write_text(json.dumps(cams, indent=0), encoding="utf-8")
print(len(args), "Konsolen")
