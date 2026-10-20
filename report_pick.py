# report_pick.py <reports-ordner> <karte> <aus.json> [nummern]: Inventar je Nightfall-Meldung - welche Modellteile
# (Objekt / Material) die Spielkamera sieht, mit Bildanteil und mittlerer Bildlage. Grundlage zum Zuordnen dessen,
# was auf einem Screenshot falsch aussieht. Raster 24 x 14 Strahlen (blender/bm_pick.py).
import collections
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BLENDER = r"C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe"
src, key, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
only = {int(n) for n in sys.argv[4].split(",")} if len(sys.argv) > 4 else None

reps = [(f, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(src.glob("*.json"))]
reps = [(i, f, d) for i, (f, d) in enumerate(reps) if d.get("map") == key and d.get("eyeZ") is not None]
if only:
    reps = [r for r in reps if r[0] in only]
views = [{"name": f"#{i}", "pos": [d["position"]["x"], d["position"]["y"], d["eyeZ"]], "yaw": d["headingDeg"],
          "pitch": d["pitchDeg"], "vfov": d["fovVerticalDeg"], "aspect": d["screen"]["aspect"], "grid": [24, 14]}
         for i, f, d in reps]
with tempfile.TemporaryDirectory() as td:
    pj = Path(td) / "picks.json"
    pj.write_text(json.dumps(views), encoding="utf-8")
    raw = Path(td) / "hits.json"
    subprocess.run([BLENDER, "-b", str(ROOT / "out" / key / f"{key}.blend"), "-P", str(ROOT / "blender" / "bm_pick.py"),
                    "--", str(pj), str(raw)], check=True, capture_output=True)
    res = json.loads(raw.read_text(encoding="utf-8"))
summary = []
for (i, f, d), r in zip(reps, res):
    c = collections.defaultdict(list)
    for h in r["hits"]:
        c[(h["obj"], h.get("mat"))].append(h)
    items = []
    for (ob, mat), hs in sorted(c.items(), key=lambda kv: -len(kv[1])):
        items.append({"obj": ob, "mat": mat, "share": round(len(hs) / len(r["hits"]), 3),
                      "u": round(sum(h["u"] for h in hs) / len(hs), 2), "v": round(sum(h["v"] for h in hs) / len(hs), 2),
                      "d": round(sum(h.get("d", 0) for h in hs) / len(hs), 2) if ob else None,
                      "at": hs[len(hs) // 2].get("at")})
    summary.append({"n": i, "file": f.name, "room": d["room"], "items": items, "hits": r["hits"]})
out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
for s in summary:
    print(f"#{s['n']} {s['room']}: " + "; ".join(f"{it['obj']}/{it['mat']} {it['share']:.0%} @({it['u']},{it['v']}) d{it['d']}"
                                               for it in s["items"][:8]))
