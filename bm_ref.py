# BlenderMaps - Nachbau aller Among-Us-Karten in Blender als Grundlage fuer Nightfall.
#
# bm_ref.py: Zugriff auf die Originalvorlage einer Karte. Quelle sind die Daten, die der Nightfall-Survey im
# laufenden Spiel geschrieben hat (Assets/NightfallWeb/data/<karte>/): atlas.png ist das Foto der ganzen Karte
# (Zeile 0 = Nordrand), world.json die Spielgeometrie (Raeume, Collider, Tueren, Vents, Konsolen, Sprites).
#
# Koordinaten: AU-Welt (x nach Osten, y nach Norden). In Blender gilt dasselbe, z ist die Hoehe.

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
NFW = ROOT.parent / "NightfallWeb" / "data"
MAPS = {"skeld": "skeldship", "mira": "miraship", "polus": "polusship", "airship": "airship", "fungle": "fungleship"}

# Spawn ausserhalb der Karte (Airship: Spawn-Auswahl): Startpunkt fuer den Grundriss im Hauptflur
SPAWN_FIX = {"airship": (10.0, 0.0), "fungle": (-3.0, 2.0)}   # Fungle: Spawn liegt im Lagerfeuer-Collider
# Karten, deren Aufnahme zu grob ist: aus den Sprites neu zusammensetzen (Ausschnitt x0, y0, x1, y1)
COMPOSITE = {"fungle": (-30.0, -25.0, 32.0, 25.0)}

# Eigene Karten aus Unknown's Atlas und optionalen Erweiterungen (bm_ext.py), Vorlage aus atlas_import.py
import bm_ext                                                                       # noqa: E402
ATLAS_MAPS = ("museum", "park", "wald", "train") + bm_ext.maps()

H_WALL = 1.39          # Raumhoehe wie in Nightfall (2,1 * 0,66); Augenhoehe 0,62
EYE = 0.62


class Ref:
    def __init__(self, key, full=False):
        self.key = key
        if key not in ATLAS_MAPS and key not in MAPS:
            bm_ext.unknown(key, ATLAS_MAPS + tuple(MAPS))
        d = (ROOT / "atlasdata" / key) if key in ATLAS_MAPS else NFW / MAPS[key]
        self.world = json.loads((d / "world.json").read_text(encoding="utf-8"))
        if key in SPAWN_FIX:
            self.world["spawn"] = list(SPAWN_FIX[key])
        a = self.world["atlas"]
        self.ppu = a["pixelsPerUnit"]
        self.mn, self.mx = a["min"], a["max"]
        # Zwei Bilder: full_image = Foto der Karte mit allen Objekten (Vergleich, Oberflaechen der Moebel), image =
        # SAUBERE Vorlage fuer Boden und Waende (eigene Karten: floor.png; Vanilla: Grundbilder ohne Einzelobjekte,
        # bm_base). full=True macht beide zum Foto (Vergleichsrender).
        self._full_wanted = full
        fo = d / "floor.png"
        self.image = Image.open(fo if (fo.exists() and not full) else d / a["file"]).convert("RGB")
        self._full_path = d / a["file"]
        # Die Aufnahme ist auf 4096 Pixel Breite gedeckelt und wurde dabei nur waagerecht gestaucht (Polus 37,2 statt
        # 52 px/Einheit, Airship 51,1): auf den senkrechten Massstab zurueckstrecken, damit ein Pixel quadratisch ist.
        ppx = self.image.width / (self.mx[0] - self.mn[0])
        ppy = self.image.height / (self.mx[1] - self.mn[1])
        if abs(ppx - ppy) / ppy > 0.002:
            import cv2
            w = int(round((self.mx[0] - self.mn[0]) * ppy))
            self.image = Image.fromarray(cv2.resize(np.asarray(self.image), (w, self.image.height),
                                                    interpolation=cv2.INTER_LINEAR))
            self.ppu = ppy
        sh = self.world["sheets"][0]
        self.sheet = Image.open(d / sh["file"]).convert("RGBA")
        if key in COMPOSITE:
            self._composite(d, COMPOSITE[key])
        self.full_image = self.image
        if fo.exists() and not full:                                  # eigene Karte: Foto separat laden
            fi = Image.open(self._full_path).convert("RGB")
            self.full_image = fi if fi.size == self.image.size else fi.resize(self.image.size)
        elif not full:
            self._clean_base()
        # img = Foto (Grundriss-, Kontur-, Huellenerkennung wie bisher), img_base = saubere Vorlage (Wandtexturen)
        self.img = np.asarray(self.full_image)
        self.img_full = self.img
        self.img_base = np.asarray(self.image)
        self.W, self.H = self.image.size

    def _clean_base(self):
        """Vanilla: Grundbilder der Raeume ohne Einzelobjekte (bm_base), gecacht in out/<karte>/base.png."""
        import bm_base
        if self.key not in bm_base.BASE:
            return
        cache = ROOT / "out" / self.key / "base.png"
        src = [Path(bm_base.__file__), self._full_path]
        if cache.exists() and all(cache.stat().st_mtime >= p.stat().st_mtime for p in src):
            img = Image.open(cache).convert("RGB")
        else:
            img, _ = bm_base.compose(self, ("base", "wall"), background=self.full_image)
            cache.parent.mkdir(parents=True, exist_ok=True)
            img.save(cache)
        if img.size == self.full_image.size:
            self.image = img

    def crop_full(self, x0, y0, x1, y1, ppu=None):
        """Wie crop, aber aus dem Foto mit allen Objekten (Oberflaechen gebauter Moebel)."""
        keep = self.image
        self.image = self.full_image
        try:
            return self.crop(x0, y0, x1, y1, ppu)
        finally:
            self.image = keep

    def _composite(self, d, box_):
        """Grobe Aufnahme (Fungle 19,3 px/E) durch die Sprites in Bogenaufloesung ersetzen: Foto hochskalieren,
        alle Sprites ausser Hintergrund/Ueberlagerung in Sortierfolge darueber, dann die grobe Helligkeit (Schatten,
        Toenung) des Fotos wieder aufpraegen. Ergebnis 52 px/E, zwischengespeichert in out/<karte>/atlas52.png."""
        import cv2
        x0, y0, x1, y1 = box_
        P = 52.0
        cache = ROOT / "out" / self.key / "atlas52.png"
        if cache.exists():
            self.image = Image.open(cache).convert("RGB")
        else:
            src = self.image
            a = src.crop((int((x0 - self.mn[0]) * self.ppu), int((self.mx[1] - y1) * self.ppu),
                          int((x1 - self.mn[0]) * self.ppu), int((self.mx[1] - y0) * self.ppu)))
            W, H = int(round((x1 - x0) * P)), int(round((y1 - y0) * P))
            lo = np.asarray(a.resize((W, H), Image.BILINEAR)).astype(np.float32)
            base = Image.fromarray(lo.astype(np.uint8)).convert("RGBA")
            sheet = self.sheet
            for p in sorted(self.world["props"], key=lambda p: (p.get("sortOrder", 0), -p.get("z", 0))):
                if p["path"].startswith("Backgrounds") or "Overlay" in p["path"] or "Parallax" in p["path"]:
                    continue
                (a0, b0), (a1, b1) = p["min"], p["max"]
                if a1 < x0 or a0 > x1 or b1 < y0 or b0 > y1:
                    continue
                ra, rb, rw, rh = p["rect"]
                spr = sheet.crop((ra, rb, ra + rw, rb + rh))
                sx, sy = (a1 - a0) / rw, (b1 - b0) / rh
                cx0, cy0, cx1, cy1 = max(a0, x0), max(b0, y0), min(a1, x1), min(b1, y1)
                sub = spr.crop((int((cx0 - a0) / sx), int((b1 - cy1) / sy), int(math.ceil((cx1 - a0) / sx)),
                                int(math.ceil((b1 - cy0) / sy))))
                w_, h_ = max(1, int(round((cx1 - cx0) * P))), max(1, int(round((cy1 - cy0) * P)))
                base.alpha_composite(sub.resize((w_, h_), Image.BILINEAR), (int(round((cx0 - x0) * P)), int(round((y1 - cy1) * P))))
            comp = np.asarray(base.convert("RGB")).astype(np.float32)
            f = P / self.ppu
            small = cv2.resize(comp, (int(comp.shape[1] / f), int(comp.shape[0] / f)), interpolation=cv2.INTER_AREA)
            lowc = cv2.resize(small, (comp.shape[1], comp.shape[0]), interpolation=cv2.INTER_LINEAR)
            corr = np.clip(comp + cv2.GaussianBlur(lo - lowc, (0, 0), 6.0), 0, 255).astype(np.uint8)
            self.image = Image.fromarray(corr)
            cache.parent.mkdir(parents=True, exist_ok=True)
            self.image.save(cache)
        self.mn, self.mx, self.ppu = [x0, y0], [x1, y1], P

    # Welt <-> Atlaspixel (Pixelmitte)
    def w2p(self, x, y):
        return (x - self.mn[0]) * self.ppu, (self.mx[1] - y) * self.ppu

    def p2w(self, px, py):
        return self.mn[0] + px / self.ppu, self.mx[1] - py / self.ppu

    def crop(self, x0, y0, x1, y1, ppu=None):
        """Ausschnitt der Welt [x0,x1] x [y0,y1] als Bild, optional auf andere Aufloesung umgerechnet."""
        p0 = self.w2p(x0, y1)
        p1 = self.w2p(x1, y0)
        im = self.image.crop((round(p0[0]), round(p0[1]), round(p1[0]), round(p1[1])))
        if ppu and abs(ppu - self.ppu) > 1e-6:
            im = im.resize((max(1, round((x1 - x0) * ppu)), max(1, round((y1 - y0) * ppu))), Image.LANCZOS)
        return im

    def colliders(self, layers=("Ship",)):
        out = []
        for w in self.world["walls"]:
            if w["layer"] in layers:
                for p in w["paths"]:
                    out.append((w, [tuple(q) for q in p] + ([tuple(p[0])] if w.get("closed") else [])))
        return out

    def zones(self):
        zs = [z for z in self.world["zones"] if z["kind"] == "room"]
        if not zs and self.world.get("rooms"):                       # Fungle: nur Raumrechtecke
            for r in self.world["rooms"]:
                (x0, y0), (x1, y1) = r["min"], r["max"]
                zs.append({"kind": "room", "path": f"{self.key}/{r['name']}", "min": r["min"], "max": r["max"],
                           "paths": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]]})
        return zs


def zone_name(z):
    parts = z["path"].split("/")
    return parts[1] if len(parts) > 1 else z["path"]


def hexcol(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c[:3])


def palette(pixels, k=6, iters=20, seed=0):
    """Haeufigste Farben einer Pixelmenge (k-means in RGB), sortiert nach Anteil: [(rgb, anteil), ...]."""
    px = np.asarray(pixels, dtype=np.float32).reshape(-1, 3)
    if len(px) == 0:
        return []
    rng = np.random.default_rng(seed)
    cent = px[rng.choice(len(px), size=min(k, len(px)), replace=False)]
    for _ in range(iters):
        d = ((px[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(len(cent)):
            m = px[lab == j]
            if len(m):
                cent[j] = np.median(m, axis=0)
    d = ((px[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
    lab = d.argmin(1)
    res = [(tuple(int(round(v)) for v in cent[j]), float((lab == j).mean())) for j in range(len(cent))]
    return sorted(res, key=lambda r: -r[1])
