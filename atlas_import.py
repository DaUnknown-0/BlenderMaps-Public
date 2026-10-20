# atlas_import.py <karte> - Atlas-Karten (eigene Karten aus Unknown's Atlas und optionalen Erweiterungen) in dasselbe
# Vorlagenformat wie die Vanilla-Karten bringen: atlasdata/<karte>/atlas.png (Kartenfoto, 52 px/m: Bodenkacheln +
# Requisiten-Sprites in Standlinien-Reihenfolge wie im Spiel), props0.png (alle Requisiten-Sprites auf einem Bogen) und
# world.json (Waende Ship, Hindernisse Ship, Glas ShortObjects, Raeume als Zonen, Spawn, Requisiten mit Rechteck).
#
# Quelle sind die erzeugten Kartendaten, die das Spiel selbst laedt: <Map>Data.cs (C#-Arrays) oder map.json
# (Atlas-Dateiformat, Zug). 1 m = 1 AU-Einheit. Sprite-Rechtecke zaehlen y wie Unity von unten. Weitere Karten melden
# Erweiterungen ueber bm_ext.py an (Eintrag wie unten in SOURCES).

import json
import math
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
MODS = ROOT.parent.parent
ATLAS = MODS / "UnknownsAtlas"

SOURCES = {
    "museum": {"cs": ATLAS / "src" / "AtlasMuseumData.cs", "layout": ATLAS / "src" / "AtlasMuseumLayout.cs",
               "assets": ATLAS / "assets", "prefix": "museum"},
    "park": {"cs": ATLAS / "src" / "AtlasParkData.cs", "layout": ATLAS / "src" / "AtlasParkLayout.cs",
             "assets": ATLAS / "assets", "prefix": "park"},
    "wald": {"cs": ATLAS / "src" / "AtlasWaldData.cs", "layout": ATLAS / "src" / "AtlasWaldLayout.cs",
             "assets": ATLAS / "assets", "prefix": "wald"},
    "train": {"json": ATLAS / "assets" / "train" / "map.json", "assets": ATLAS / "assets" / "train", "prefix": "train"},
}
import bm_ext                                                                       # noqa: E402
SOURCES.update(bm_ext.sources())                                                    # Karten optionaler Erweiterungen
PPU = 52.0

NUM = r"-?\d+(?:\.\d+)?"


def _vecs(s):
    return [(float(a), float(b)) for a, b in re.findall(rf"new\(\s*({NUM})f\s*,\s*({NUM})f\s*\)", s)]


def _block(src, name):
    """Text des Initialisierers 'name = { ... };' (Klammern gezaehlt)."""
    m = re.search(rf"\b{name}\s*=\s*(?:new[^{{]*)?\{{", src)
    if not m:
        return None
    i, depth = m.end(), 1
    while depth:
        c = src[i]
        depth += (c == "{") - (c == "}")
        i += 1
    return src[m.end():i - 1]


def _polys(src, name):
    b = _block(src, name)
    if b is None:
        return []
    return [_vecs(p) for p in re.findall(r"new Vector2\[\]\s*\{(.*?)\}", b, re.S)]


def _const(src, name):
    m = re.search(rf"\b{name}\s*=\s*({NUM})f", src)
    return float(m.group(1)) if m else None


def _tuples(src, name):
    b = _block(src, name)
    return [] if b is None else re.findall(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", b)


def read_cs(cfg):
    src = cfg["cs"].read_text(encoding="utf-8")
    d = {"minX": _const(src, "MinX"), "minY": _const(src, "MinY"), "maxX": _const(src, "MaxX"), "maxY": _const(src, "MaxY"),
         "walls": _polys(src, "Walls"), "opaque": _polys(src, "Opaque"), "glass": _polys(src, "Glass")}
    rooms = []
    b = _block(src, "Rooms")
    for m in re.finditer(r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*SystemTypes\.(\w+)\s*,\s*new Vector2\[\]\s*\{(.*?)\}\s*\)', b, re.S):
        rooms.append({"key": m.group(1), "name": m.group(2), "room": m.group(3), "area": _vecs(m.group(4))})
    d["rooms"] = rooms
    d["floorPixelsPerMeter"] = _const(src, "FloorPixelsPerMeter")
    d["floorTiles"] = []
    for t in _tuples(src, "FloorTiles"):
        v = [x.strip().rstrip("f") for x in t.split(",")]
        d["floorTiles"].append({"index": int(v[0]), "x": float(v[1]), "y": float(v[2]), "w": int(v[3]), "h": int(v[4])})
    d["propPixelsPerMeter"] = _const(src, "PropPixelsPerMeter")
    d["props"] = []
    for t in _tuples(src, "Props"):
        v = [x.strip() for x in t.split(",")]
        if len(v) < 11:
            continue
        f = [x.rstrip("f") for x in v]
        d["props"].append({"kind": v[0].strip('"'), "atlas": int(f[1]), "x": int(f[2]), "y": int(f[3]), "w": int(f[4]),
                           "h": int(f[5]), "worldX": float(f[6]), "worldY": float(f[7]), "baseY": float(f[8]),
                           "footX0": float(f[9]), "footX1": float(f[10])})
    sp = re.search(rf"\bSpawn\s*=\s*new\(\s*({NUM})f\s*,\s*({NUM})f", src)
    if not sp and cfg.get("layout"):
        sp = re.search(rf"\bSpawn\s*=\s*new\(\s*({NUM})f\s*,\s*({NUM})f", cfg["layout"].read_text(encoding="utf-8"))
    d["spawn"] = [float(sp.group(1)), float(sp.group(2))] if sp else None
    return d


def read_json(cfg):
    d = json.loads(cfg["json"].read_text(encoding="utf-8"))
    return d


def compose(d, cfg):
    x0, y0, x1, y1 = d["minX"], d["minY"], d["maxX"], d["maxY"]
    W, H = int(round((x1 - x0) * PPU)), int(round((y1 - y0) * PPU))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    fppm = d["floorPixelsPerMeter"]
    pre = cfg["prefix"]
    for t in d["floorTiles"]:
        f = cfg["assets"] / f"{pre}_floor_{t['index']}.jpg"
        if not f.exists():
            continue
        tile = Image.open(f).convert("RGBA")
        sw, sh = t["w"] / fppm, t["h"] / fppm
        tile = tile.resize((max(1, int(round(sw * PPU))), max(1, int(round(sh * PPU)))), Image.LANCZOS)
        img.alpha_composite(tile, (int(round((t["x"] - x0) * PPU)), int(round((y1 - (t["y"] + sh)) * PPU))))
    floor_only = img.convert("RGB").copy()
    pppm = d["propPixelsPerMeter"]
    atl = {}
    sprites = []
    for i, p in enumerate(d["props"]):
        k = p["atlas"]
        if k not in atl:
            f = cfg["assets"] / f"{pre}_props_{k}.png"
            atl[k] = Image.open(f).convert("RGBA") if f.exists() else None
        A = atl[k]
        if A is None:
            continue
        top = A.height - p["y"] - p["h"]                        # Unity-Rechteck: y von unten
        spr = A.crop((p["x"], top, p["x"] + p["w"], top + p["h"]))
        sprites.append((p, spr, i))
    for p, spr, i in sorted(sprites, key=lambda t: -t[0]["baseY"]):
        sw, sh = p["w"] / pppm, p["h"] / pppm
        s2 = spr.resize((max(1, int(round(sw * PPU))), max(1, int(round(sh * PPU)))), Image.LANCZOS)
        img.alpha_composite(s2, (int(round((p["worldX"] - x0) * PPU)), int(round((y1 - (p["worldY"] + sh)) * PPU))))
    return img.convert("RGB"), sprites, floor_only


def pack(sprites):
    """Alle Sprites zeilenweise auf einen Bogen (props0.png); Rueckgabe Bogen und Rechtecke (x, y oben, w, h)."""
    Wmax = 4096
    x = y = rowh = 0
    rects = []
    for p, spr, i in sprites:
        w, h = spr.size
        if x + w > Wmax:
            x, y, rowh = 0, y + rowh + 2, 0
        rects.append((x, y, w, h))
        x += w + 2
        rowh = max(rowh, h)
    sheet = Image.new("RGBA", (Wmax, y + rowh + 2), (0, 0, 0, 0))
    for (p, spr, i), (rx, ry, w, h) in zip(sprites, rects):
        sheet.paste(spr, (rx, ry))
    return sheet, rects


def main(key):
    if key not in SOURCES:
        bm_ext.unknown(key, SOURCES)
    cfg = SOURCES[key]
    d = read_json(cfg) if "json" in cfg else read_cs(cfg)
    out = ROOT / "atlasdata" / key
    out.mkdir(parents=True, exist_ok=True)
    img, sprites, floor_only = compose(d, cfg)
    img.save(out / "atlas.png")
    floor_only.save(out / "floor.png")                                   # nur Boden + Waende (Texturquelle)
    sheet, rects = pack(sprites)
    sheet.save(out / "props0.png")
    walls = [{"path": f"{key}/Walls", "layer": "Ship", "kind": "wall", "closed": True, "paths": [list(map(list, r)) for r in d["walls"]]}]
    walls += [{"path": f"{key}/Opaque{i}", "layer": "Ship", "kind": "wall", "closed": True, "paths": [list(map(list, r))]}
              for i, r in enumerate(d["opaque"])]
    walls += [{"path": f"{key}/Glass{i}", "layer": "ShortObjects", "kind": "wall", "closed": True, "paths": [list(map(list, r))]}
              for i, r in enumerate(d["glass"])]
    zones = []
    for r in d["rooms"]:
        xs = [p[0] for p in r["area"]]
        ys = [p[1] for p in r["area"]]
        zones.append({"kind": "room", "path": f"{key}/{r['key']}", "name": r["name"], "system": r["room"],
                      "min": [min(xs), min(ys)], "max": [max(xs), max(ys)], "paths": [list(map(list, r["area"]))]})
    pppm = d["propPixelsPerMeter"]
    props = []
    for (p, spr, i), (rx, ry, w, h) in zip(sprites, rects):
        props.append({"path": f"{key}/{p['kind']}#{i}", "name": p["kind"], "layer": 12, "collider": False,
                      "sortOrder": 0, "z": 0, "min": [p["worldX"], p["worldY"]],
                      "max": [p["worldX"] + p["w"] / pppm, p["worldY"] + p["h"] / pppm], "rect": [rx, ry, w, h],
                      "baseY": p["baseY"], "foot": [p["footX0"], p["footX1"]]})
    spawn = d.get("spawn") or [sum(p[0] for p in d["rooms"][0]["area"]) / len(d["rooms"][0]["area"]),
                               sum(p[1] for p in d["rooms"][0]["area"]) / len(d["rooms"][0]["area"])]
    world = {"map": key, "atlas": {"file": "atlas.png", "w": img.width, "h": img.height, "min": [d["minX"], d["minY"]],
                                   "max": [d["maxX"], d["maxY"]], "pixelsPerUnit": PPU},
             "sheets": [{"file": "props0.png", "w": sheet.width, "h": sheet.height}], "spawn": list(spawn),
             "rooms": [], "zones": zones, "walls": walls, "props": props, "vents": [], "doors": [], "consoles": []}
    (out / "world.json").write_text(json.dumps(world), encoding="utf-8")
    print(key, img.size, "Waende", len(d["walls"]), "Hindernisse", len(d["opaque"]), "Glas", len(d["glass"]),
          "Raeume", len(zones), "Requisiten", len(props), "Spawn", spawn)


if __name__ == "__main__":
    for k in (sys.argv[1:] or list(SOURCES)):
        main(k)
