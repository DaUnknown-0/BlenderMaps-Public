# colmap.py <karte> <aus.png> [aus.json]: Collider-Karte zum Abgleich Modell <-> Spiel.
#   Draufsicht: Boden (grau), Ship-Collider (rot), geschlossene Objekt-Collider (orange), Konsolen/Tasks (gruen mit Namen),
#   Vents (cyan), Grundflaechen aller gebauten Teile (blau, dunkler = hoeher).
#   Bericht (JSON + Konsole): Konsolen ohne Modellteil in der Naehe (fehlende Task-Objekte), Objekt-Collider ohne Teil
#   darauf (fehlende Moebel), Teile im Laufbereich ueber 0,35 (Spieler liefe hindurch).
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union

from bm_ref import ROOT

key, out = sys.argv[1], sys.argv[2]
rep = sys.argv[3] if len(sys.argv) > 3 else None
from bm_scene import Scene                                                          # noqa: E402
import bm_objects                                                                    # noqa: E402

sc = Scene(key)
sc.build_plan()
doc = json.loads((ROOT / "out" / key / "scene.json").read_text(encoding="utf-8"))
ref = sc.ref
walk = sc.walk_real()
PPU = 40
x0, y0 = ref.mn
x1, y1 = ref.mx
W, Hh = int((x1 - x0) * PPU), int((y1 - y0) * PPU)
im = Image.new("RGB", (W, Hh), (24, 24, 28))
d = ImageDraw.Draw(im)


def P(x, y):
    return ((x - x0) * PPU, (y1 - y) * PPU)


def poly(g, fill=None, outline=None, width=1):
    for q in getattr(g, "geoms", [g]):
        if q.is_empty or q.geom_type != "Polygon":
            continue
        pts = [P(x, y) for x, y in q.exterior.coords]
        if fill:
            d.polygon(pts, fill=fill)
        if outline:
            d.line(pts, fill=outline, width=width)
        for h in q.interiors:
            hp = [P(x, y) for x, y in h.coords]
            if fill:
                d.polygon(hp, fill=(24, 24, 28))
            if outline:
                d.line(hp, fill=outline, width=width)


poly(sc.floor, fill=(70, 72, 78))
poly(walk, fill=(96, 100, 108))
# Teile: Grundflaechen je Teil (bm_objects._parts_footprint liefert die Vereinigung; hier je Teil mit Hoehe)
parts = [(m["name"], q) for m in doc["meshes"] if m.get("kind") == "parts" for q in m["parts"]]


def fp_of(q):
    t = q.get("type")
    try:
        if t == "prism":
            return Polygon(q["pts"]).buffer(0), q["z0"], q["z1"]
        if t == "mesh":
            vs = q["verts"]
            zs = [v[2] for v in vs]
            from shapely.geometry import MultiPoint
            return MultiPoint([(v[0], v[1]) for v in vs]).convex_hull, min(zs), max(zs)
        if t == "lathe":
            r = max(p[0] for p in q["prof"])
            zs = [p[1] for p in q["prof"]]
            return Point(q["c"]).buffer(r), min(zs), max(zs)
        if t == "tube":
            pts = q["pts"]
            from shapely.geometry import LineString
            return LineString([(p[0], p[1]) for p in pts]).buffer(q["r"]) if len(pts) > 1 else Point(pts[0][0], pts[0][1]).buffer(q["r"]), min(p[2] for p in pts), max(p[2] for p in pts)
    except Exception:
        return None
    return None


fps = []
for name, q in parts:
    r = fp_of(q)
    if r is None or r[0].is_empty:
        continue
    g, z0, z1 = r
    fps.append((name, g, z0, z1))
    sh = int(min(1.0, max(0.0, z1 / 2.0)) * 120)
    poly(g, fill=(60, 90 + sh // 2, 200 - sh))
# Collider
cols_ship, cols_obj = [], []
for w in ref.world["walls"]:
    for path in w["paths"]:
        if len(path) < 2:
            continue
        pts = [P(x, y) for x, y in path]
        if w["layer"] == "Ship":
            d.line(pts + ([pts[0]] if w.get("closed") else []), fill=(230, 60, 60), width=2)
            if w.get("closed") and len(path) >= 3:
                cols_ship.append((w["path"], Polygon(path).buffer(0)))
        else:
            d.line(pts + ([pts[0]] if w.get("closed") else []), fill=(240, 160, 50), width=2)
            if w.get("closed") and len(path) >= 3:
                cols_obj.append((w["path"], Polygon(path).buffer(0)))
try:
    font = ImageFont.truetype("arial.ttf", 11)
except Exception:
    font = ImageFont.load_default()
allfp = unary_union([g for _, g, _, _ in fps]) if fps else Polygon()
report = {"missing_console": [], "missing_object": [], "intrusion": []}
for c in ref.world.get("consoles", []):
    x, y = c["pos"]
    near = allfp.distance(Point(x, y))
    ok = near < 0.7                                                       # Wandkonsolen: Collider-Mitte liegt vor der Wand
    d.ellipse([P(x - 0.12, y + 0.12), P(x + 0.12, y - 0.12)], outline=(80, 240, 120) if ok else (255, 80, 220), width=2)
    d.text(P(x + 0.15, y + 0.05), c["name"], fill=(200, 255, 200) if ok else (255, 160, 240), font=font)
    if not ok:
        report["missing_console"].append({"name": c["name"], "room": c.get("room"), "pos": [x, y], "dist": round(near, 2)})
for v in ref.world.get("vents", []):
    x, y = v.get("pos", v.get("min", [0, 0]))
    d.rectangle([P(x - 0.15, y + 0.15), P(x + 0.15, y - 0.15)], outline=(80, 220, 240), width=2)
for pth, g in cols_obj:
    if g.area < 0.03:
        continue
    cov = allfp.intersection(g).area / g.area
    if cov < 0.25:
        report["missing_object"].append({"path": pth, "bounds": [round(v, 2) for v in g.bounds], "covered": round(cov, 2)})
        poly(g, outline=(255, 90, 90), width=3)
for name, g, z0, z1 in fps:
    if z1 <= 0.35:
        continue
    inter = walk.intersection(g)
    if inter.area > 0.02:
        report["intrusion"].append({"part": name, "area": round(inter.area, 3), "z": [round(z0, 2), round(z1, 2)],
                                    "at": [round(inter.centroid.x, 2), round(inter.centroid.y, 2)]})
        poly(inter, outline=(255, 255, 0), width=2)
report["intrusion"].sort(key=lambda e: -e["area"])
im.save(out)
print(f"{key}: Konsolen ohne Teil {len(report['missing_console'])}, Objekt-Collider ohne Teil {len(report['missing_object'])}, "
      f"Teile im Laufbereich {len(report['intrusion'])}")
for e in report["missing_console"]:
    print("  Konsole fehlt:", e)
for e in report["missing_object"][:40]:
    print("  Objekt fehlt:", e)
for e in report["intrusion"][:25]:
    print("  Laufweg:", e)
if rep:
    Path(rep).write_text(json.dumps(report, indent=1), encoding="utf-8")
