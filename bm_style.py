# bm_style.py - prozedurale Oberflaechen fuer die Vanilla-Karten (User 19.10.: "keine Ingame-Texturen mehr, alles selber
# machen, Spieltexturen nur noch als Referenz"). Boeden und Waende sind gezeichnete Kacheln (PIL) in Farben, die aus der
# Vorlage GEMESSEN werden (Median/Palette der Bodenflaeche bzw. des Wandbands); kein Pixel der Spielgrafik landet im
# Modell. Muster je Karte und Raum (FLOOR/WALL/ROOM), Bildschirminhalte als generische Anzeigen (ui_screen) in der
# Farbfamilie des jeweiligen Sprites.
#
# Kacheln: Boden 1 x 1 m (uv world), Wand H x H m (uv world, Kachel laengs der Wand, v = z/H).

import math
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw

PROCEDURAL = {"skeld", "mira", "polus", "airship", "fungle"}

# Standardmuster je Karte: (Boden, Wand)
MAP = {"skeld": ("plates", "panels"), "mira": ("tiles", "panels"), "polus": ("concrete", "plates"),
       "airship": ("planks", "wood"), "fungle": ("ground", "rock")}

# Raum-Ueberschreibungen (Teilstring des Raumnamens, Reihenfolge = Vorrang)
ROOM = {
    "skeld": [("Cafeteria", None, "panels"), ("Storage", "concrete", "plates"), ("Electrical", "metal", "plates"),
              ("Reactor", "metal", "plates"), ("Engine", "metal", "plates"), ("MedBay", "tiles", "panels"), ("Medical", "tiles", "panels"),
              ("Security", "plates", "panels"), ("Weapons", "plates", "panels"), ("Shields", "plates", "panels"),
              ("Hallway", "plates", "panels"), ("Admin", "carpet", "panels"), ("Comms", "plates", "panels")],
    "mira": [("Garden", "ground", "panels"), ("Greenhouse", "ground", "panels"), ("Reactor", "metal", "plates"),
             ("Launch", "plates", "plates"), ("Balcony", "plates", "plates"), ("Lab", "tiles", "panels"), ("Decon", "tiles", "panels"),
             ("Storage", "concrete", "plates"), ("Locker", "tiles", "panels"), ("Office", "carpet", "panels"), ("Admin", "carpet", "panels"),
             ("Cafe", "tiles", "panels"), ("Comms", "carpet", "panels"), ("MedBay", "tiles", "panels"), ("Hallway", "carpet", "panels")],
    "polus": [("Outside", "snow", "panels"), ("Balcony", "tiles", "panels"), ("ElecTube", "plates", "panels"), ("Dropship", "metal", "plates"), ("Office", "carpet", "panels"), ("Admin", "carpet", "panels"),
              ("Comms", "plates", "plates"), ("Weapons", "plates", "plates"), ("Science", "tiles", "panels"), ("Specimen", "tiles", "panels"),
              ("LifeSupp", "concrete", "plates"), ("Boiler", "grating", "plates"), ("Electrical", "metal", "plates"),
              ("Security", "plates", "panels"), ("Storage", "concrete", "plates"), ("Laboratory", "tiles", "panels"), ("Decon", "tiles", "plates")],
    "airship": [("Cockpit", "planks", "wood"), ("Kitchen", "tiles", "tile"), ("Showers", "tiles", "tile"), ("Medbay", "tiles", "panels"),
                ("Engine", "metal", "plates"), ("Electrical", "metal", "plates"), ("Gap", "metal", "plates"), ("Ventilation", "grating", "plates"),
                ("Vault", "carpet", "wood"), ("Lounge", "carpet", "wood"), ("Records", "planks", "wood"), ("Security", "planks", "wood"),
                ("Meeting", "carpet", "wood"), ("Armory", "planks", "wood"), ("Storage", "planks", "wood"), ("Cargo", "planks", "wood"),
                ("Hallway", "planks", "wood"), ("Comms", "planks", "wood"), ("Brig", "metal", "plates")],
    "fungle": [("Cafeteria", "planks", "wood"), ("Dorm", "planks", "wood"), ("Storage", "planks", "wood"), ("Kitchen", "tiles", "wood"),
               ("Lab", "tiles", "panels"), ("Reactor", "metal", "plates"), ("Comms", "planks", "wood"), ("Lookout", "planks", "wood"),
               ("Beach", "sand", "rock"), ("Jungle", "ground", "rock"), ("Greenhouse", "ground", "wood"), ("Outside", "ground", "rock"),
               ("Highland", "ground", "rock"), ("Plateau", "ground", "rock"), ("Mining", "ground", "rock"), ("Dropship", "metal", "plates"),
               ("Meeting", "planks", "wood"), ("Sleeping", "planks", "wood"), ("Rec", "sand", "wood"), ("Campfire", "sand", "rock")],
}


def on(sc):
    return sc.key in PROCEDURAL or bool(sc.cfg.get("procedural"))


def _sh(rgb, f):
    return tuple(max(0, min(255, int(v * f))) for v in rgb)


def _mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _lum(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def patterns(key, room):
    fl, wa = MAP.get(key, ("plates", "panels"))
    for sub, f, w in ROOM.get(key, []):
        if sub.lower() in room.lower():
            return (f or fl), (w or wa)
    return fl, wa


# ------------------------------------------------------------------------------------------- Messung

def measure_floor(ref, poly):
    """Haeufigste Bodenfarbe und Zweitfarbe der sauberen Vorlage innerhalb des Raums (Referenz, keine Pixelnutzung)."""
    from bm_ref import palette
    x0, y0, x1, y1 = poly.bounds
    px0, py0 = ref.w2p(x0, y1)
    px1, py1 = ref.w2p(x1, y0)
    px0, py0, px1, py1 = int(max(0, px0)), int(max(0, py0)), int(min(ref.W, px1)), int(min(ref.H, py1))
    if px1 - px0 < 2 or py1 - py0 < 2:
        return (110, 116, 122), None
    img = ref.img_base[py0:py1, px0:px1]
    m = np.zeros(img.shape[:2], np.uint8)
    for g in getattr(poly, "geoms", [poly]):
        if g.is_empty:
            continue
        pts = np.array([[(x - x0) * ref.ppu, (y1 - y) * ref.ppu] for x, y in g.exterior.coords], np.int32)
        cv2.fillPoly(m, [pts], 1)
        for h in g.interiors:
            pts = np.array([[(x - x0) * ref.ppu, (y1 - y) * ref.ppu] for x, y in h.coords], np.int32)
            cv2.fillPoly(m, [pts], 0)
    m = cv2.erode(m, np.ones((5, 5), np.uint8))
    px = img[m > 0]
    if len(px) < 20:
        px = img.reshape(-1, 3)
    if len(px) > 20000:
        px = px[np.random.default_rng(1).choice(len(px), 20000, replace=False)]
    # sehr dunkle Konturpixel raus (Kontur der Zeichnung, nicht Bodenfarbe)
    bright = px[(px.astype(int).sum(1) > 60)]
    if len(bright) > 20:
        px = bright
    pal = palette(px, k=4)
    main = pal[0][0]
    accent = None
    for rgb, share in pal[1:]:
        if share > 0.08 and np.abs(np.array(rgb) - np.array(main)).sum() > 40:
            accent = rgb
            break
    return main, accent


def measure_walls(sc, north, B):
    """Wandfarben aus dem gezeichneten Nordband (Hauptfarbe, Abschluss oben, Sockel): Median je Zeilenbereich."""
    from bm_ref import palette
    strips = []
    for e in north:
        if e["len"] < 0.3:
            continue
        try:
            strips.append(sc.band_strip(e, B, sc.ref.ppu))
        except Exception:
            pass
    if not strips:
        return None
    arr = np.concatenate([s.reshape(-1, 3) for s in [st[int(st.shape[0] * 0.3):int(st.shape[0] * 0.82)] for st in strips]])
    arr = arr[arr.astype(int).sum(1) > 60]
    if len(arr) < 10:
        return None
    if len(arr) > 20000:
        arr = arr[np.random.default_rng(2).choice(len(arr), 20000, replace=False)]
    pal = palette(arr, k=4)
    main = pal[0][0]
    accent = None
    for rgb, share in pal[1:]:
        if share > 0.1 and np.abs(np.array(rgb) - np.array(main)).sum() > 50:
            accent = rgb
            break
    top = np.concatenate([st[int(st.shape[0] * 0.04):int(st.shape[0] * 0.16)].reshape(-1, 3) for st in strips])
    top = top[top.astype(int).sum(1) > 60]
    trim = tuple(int(v) for v in np.median(top, axis=0)) if len(top) else _sh(main, 0.8)
    return {"main": main, "accent": accent, "trim": trim}


# ------------------------------------------------------------------------------------------- Kacheln

def _noise(d, s, rgb, n, amp, seed, size=1):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.randrange(s), rnd.randrange(s)
        c = _sh(rgb, 1 + rnd.uniform(-amp, amp))
        if size == 1:
            d.point((x, y), fill=c)
        else:
            d.rectangle([x, y, x + size, y + size], fill=c)


def floor_image(pattern, main, accent=None, seed=0, s=256):
    im = Image.new("RGB", (s, s), main)
    d = ImageDraw.Draw(im)
    dark = _sh(main, 0.62)
    light = _sh(main, 1.14)
    acc = accent or _sh(main, 0.88)
    if pattern in ("plates", "metal"):
        if pattern == "metal":
            _noise(d, s, main, s * s // 6, 0.07, seed)
        else:
            _noise(d, s, main, s * s // 10, 0.05, seed)
        d.rectangle([0, 0, s - 1, s - 1], outline=dark, width=3)
        d.line([(s // 2, 0), (s // 2, s)], fill=_sh(main, 0.8), width=2)
        d.line([(0, s // 2), (s, s // 2)], fill=_sh(main, 0.8), width=2)
        for x, y in ((8, 8), (s - 9, 8), (8, s - 9), (s - 9, s - 9), (s // 2, 8), (8, s // 2), (s - 9, s // 2), (s // 2, s - 9)):
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=light, outline=dark)
        if accent:
            d.rectangle([s // 2 - 2, 0, s // 2 + 2, s], fill=acc)
    elif pattern == "tiles":
        n = 4
        t = s // n
        for i in range(n):
            for j in range(n):
                f = 1 + 0.05 * math.sin(i * 2.1 + j * 1.3 + seed)
                d.rectangle([i * t + 2, j * t + 2, (i + 1) * t - 2, (j + 1) * t - 2], fill=_sh(main, f))
        for i in range(n + 1):
            d.line([(i * t, 0), (i * t, s)], fill=dark, width=3)
            d.line([(0, i * t), (s, i * t)], fill=dark, width=3)
        if accent:
            d.rectangle([2 * t + 2, 2 * t + 2, 3 * t - 2, 3 * t - 2], fill=acc)
    elif pattern == "hex":
        r = s / 6
        for row in range(-1, 8):
            for col in range(-1, 8):
                cx = col * r * 1.5
                cy = row * r * math.sqrt(3) + (r * math.sqrt(3) / 2 if col % 2 else 0)
                pts = [(cx + r * 0.92 * math.cos(math.radians(60 * k)), cy + r * 0.92 * math.sin(math.radians(60 * k))) for k in range(6)]
                d.polygon(pts, fill=_sh(main, 1 + 0.05 * math.sin(row * 1.7 + col)), outline=dark)
    elif pattern == "grating":
        d.rectangle([0, 0, s, s], fill=_sh(main, 0.45))
        step = s // 8
        for i in range(0, s + 1, step):
            d.line([(i, 0), (i, s)], fill=light, width=5)
            d.line([(0, i), (s, i)], fill=light, width=5)
        d.rectangle([0, 0, s - 1, s - 1], outline=_sh(main, 1.25), width=6)
    elif pattern == "carpet":
        _noise(d, s, main, s * s // 3, 0.12, seed)
        g = acc
        for i in range(2):
            for j in range(2):
                cx, cy = int(s * (i + 0.5) / 2), int(s * (j + 0.5) / 2)
                r = s // 7
                d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], outline=g, width=2)
    elif pattern == "concrete":
        _noise(d, s, main, s * s // 3, 0.1, seed)
        rnd = random.Random(seed + 5)
        for _ in range(6):
            x, y = rnd.randrange(s), rnd.randrange(s)
            pts = [(x, y)]
            for k in range(5):
                pts.append((pts[-1][0] + rnd.randint(-20, 20), pts[-1][1] + rnd.randint(-20, 20)))
            d.line(pts, fill=dark, width=1)
        d.rectangle([0, 0, s - 1, s - 1], outline=_sh(main, 0.85), width=2)
    elif pattern == "planks":
        n = 6
        for i in range(n):
            f = 1 + 0.1 * math.sin(i * 2.3 + seed)
            d.rectangle([0, i * s / n, s, (i + 1) * s / n], fill=_sh(main, f))
            d.line([(0, i * s / n), (s, i * s / n)], fill=dark, width=3)
            off = int(s * ((i * 0.37 + seed * 0.1) % 1.0))
            d.line([(off, i * s / n), (off, (i + 1) * s / n)], fill=dark, width=3)
            rnd = random.Random(seed * 10 + i)
            for _ in range(5):
                y = rnd.uniform(i * s / n + 6, (i + 1) * s / n - 6)
                d.line([(0, y), (s, y + rnd.uniform(-4, 4))], fill=_sh(main, 0.9), width=1)
    elif pattern in ("ground", "sand", "grass", "snow"):
        _noise(d, s, main, s * s // 2, 0.14 if pattern != "snow" else 0.05, seed, size=2)
        rnd = random.Random(seed + 9)
        for _ in range(14):
            x, y = rnd.randrange(s), rnd.randrange(s)
            r = rnd.randint(6, 22)
            c = acc if accent else _sh(main, rnd.choice([0.85, 1.12]))
            d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=c)
        if pattern == "grass":
            for _ in range(80):
                x, y = rnd.randrange(s), rnd.randrange(s)
                d.line([(x, y), (x + rnd.randint(-3, 3), y - rnd.randint(4, 9))], fill=_sh(main, 1.25), width=1)
    else:
        _noise(d, s, main, s * s // 8, 0.06, seed)
    return im


def wall_image(pattern, main, trim=None, accent=None, H=1.39, seed=0, s=384, window=False):
    """Wandkachel H x H: Sockel unten, Feld, Abschluss oben, Muster je Art."""
    im = Image.new("RGB", (s, s), main)
    d = ImageDraw.Draw(im)
    px = s / H
    dark = _sh(main, 0.6)
    light = _sh(main, 1.15)
    trim = trim or _sh(main, 0.8)
    skirt = _sh(main, 0.55)
    if pattern == "panels":
        _noise(d, s, main, s * s // 12, 0.04, seed)
        # Paneelfugen: drei Felder je Kachel, eine waagerechte Fuge auf 55 %
        for i in range(1, 3):
            x = int(s * i / 3)
            d.line([(x, 0), (x, s)], fill=dark, width=3)
            d.line([(x + 3, 0), (x + 3, s)], fill=light, width=1)
        yh = int(s - 0.55 * H * px)
        d.line([(0, yh), (s, yh)], fill=dark, width=3)
        d.line([(0, yh + 3), (s, yh + 3)], fill=light, width=1)
        # Nieten an den Fugenkreuzungen
        for i in range(3):
            x = int(s * (i + 0.5) / 3)
            for y in (yh - 10, s - int(0.2 * px)):
                d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=light, outline=dark)
        d.rectangle([0, s - int(0.12 * px), s, s], fill=skirt)
        d.rectangle([0, s - int(0.12 * px) - 3, s, s - int(0.12 * px)], fill=_sh(main, 1.25))
        d.rectangle([0, 0, s, int(0.1 * px)], fill=trim)
        d.rectangle([0, int(0.1 * px), s, int(0.1 * px) + 3], fill=dark)
        if accent:
            d.rectangle([0, int(0.1 * px) + 6, s, int(0.1 * px) + 6 + int(0.05 * px)], fill=accent)
    elif pattern == "plates":
        _noise(d, s, main, s * s // 7, 0.07, seed)
        rows = 3
        for r in range(rows + 1):
            y = int(s * r / rows)
            d.line([(0, y), (s, y)], fill=dark, width=4)
            for j in range(6):
                x = int(s * (j + 0.5) / 6)
                yy = min(s - 6, y + 12)
                d.ellipse([x - 4, yy - 4, x + 4, yy + 4], fill=light, outline=dark)
        d.line([(s // 2, 0), (s // 2, s)], fill=dark, width=4)
        d.rectangle([0, s - int(0.08 * px), s, s], fill=skirt)
        d.rectangle([0, 0, s, int(0.06 * px)], fill=trim)
        if accent:
            d.rectangle([0, int(0.6 * s), s, int(0.6 * s) + 10], fill=accent)
    elif pattern == "concrete":
        _noise(d, s, main, s * s // 3, 0.1, seed)
        d.rectangle([0, s - int(0.1 * px), s, s], fill=skirt)
        d.rectangle([0, 0, s, int(0.05 * px)], fill=trim)
        d.line([(0, int(s * 0.5)), (s, int(s * 0.5))], fill=dark, width=2)
    elif pattern == "rock":
        _noise(d, s, main, s * s // 2, 0.16, seed, size=2)
        rnd = random.Random(seed + 3)
        for _ in range(26):
            x, y = rnd.randrange(s), rnd.randrange(s)
            r = rnd.randint(10, 40)
            c = _sh(main, rnd.choice([0.8, 0.9, 1.1, 1.2]))
            pts = [(x + r * rnd.uniform(0.6, 1.0) * math.cos(math.radians(a)), y + r * 0.7 * rnd.uniform(0.6, 1.0) * math.sin(math.radians(a))) for a in range(0, 360, 45)]
            d.polygon(pts, fill=c, outline=dark)
    elif pattern == "wood":
        n = 8
        for i in range(n):
            f = 1 + 0.08 * math.sin(i * 1.9 + seed)
            d.rectangle([i * s / n, 0, (i + 1) * s / n, s], fill=_sh(main, f))
            d.line([(i * s / n, 0), (i * s / n, s)], fill=dark, width=3)
        d.rectangle([0, s - int(0.12 * px), s, s], fill=skirt)
        d.rectangle([0, s - int(0.6 * px), s, s - int(0.6 * px) + int(0.03 * px)], fill=trim)
        d.rectangle([0, 0, s, int(0.08 * px)], fill=trim)
    elif pattern == "tile":
        n = 8
        t = s / n
        for i in range(n):
            for j in range(n):
                d.rectangle([i * t + 2, j * t + 2, (i + 1) * t - 2, (j + 1) * t - 2], fill=_sh(main, 1 + 0.04 * math.sin(i * 2 + j * 3 + seed)))
        for i in range(n + 1):
            d.line([(i * t, 0), (i * t, s)], fill=dark, width=2)
            d.line([(0, i * t), (s, i * t)], fill=dark, width=2)
        d.rectangle([0, s - int(0.1 * px), s, s], fill=skirt)
    else:
        _noise(d, s, main, s * s // 10, 0.05, seed)
        d.rectangle([0, s - int(0.1 * px), s, s], fill=skirt)
        d.rectangle([0, 0, s, int(0.06 * px)], fill=trim)
    return im


def ui_screen(colors, seed=0, w=160, h=100, kind=None):
    """Generische Geraeteanzeige: dunkler Grund, Balken/Kurve/Zeilen/Raster in der Farbfamilie (colors = [(rgb, anteil)])."""
    rnd = random.Random(seed)
    cols = [c for c, _ in colors if _lum(c) > 40] or [(120, 190, 200)]
    prim = max(cols, key=_lum) if len(cols) == 1 else cols[0]
    sec = cols[1] if len(cols) > 1 else _sh(prim, 0.7)
    bg = _sh(prim, 0.18)
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=_sh(prim, 0.5), width=2)
    kind = kind or rnd.choice(["bars", "graph", "text", "grid", "gauge"])
    if kind == "bars":
        n = rnd.randint(5, 9)
        for i in range(n):
            x0 = int(6 + (w - 12) * i / n)
            x1 = int(6 + (w - 12) * (i + 0.8) / n)
            hh = rnd.randint(int(h * 0.15), int(h * 0.8))
            d.rectangle([x0, h - 6 - hh, x1, h - 6], fill=prim if i % 3 else sec)
    elif kind == "graph":
        pts = [(6 + (w - 12) * i / 16, h * 0.5 + rnd.uniform(-h * 0.35, h * 0.35)) for i in range(17)]
        d.line(pts, fill=prim, width=2)
        for yy in range(10, h - 6, 14):
            d.line([(6, yy), (w - 6, yy)], fill=_sh(prim, 0.35), width=1)
    elif kind == "text":
        for i, yy in enumerate(range(8, h - 8, 9)):
            ln = rnd.randint(int(w * 0.3), int(w * 0.85))
            d.rectangle([8, yy, 8 + ln, yy + 4], fill=prim if i % 4 else sec)
    elif kind == "grid":
        for xx in range(8, w - 6, 16):
            d.line([(xx, 6), (xx, h - 6)], fill=_sh(prim, 0.5), width=1)
        for yy in range(8, h - 6, 16):
            d.line([(6, yy), (w - 6, yy)], fill=_sh(prim, 0.5), width=1)
        for _ in range(4):
            x, y = rnd.randrange(10, w - 10), rnd.randrange(10, h - 10)
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=sec)
    else:
        cx, cy, r = w // 2, int(h * 0.7), int(min(w, h) * 0.42)
        d.pieslice([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=_sh(prim, 0.4), outline=prim, width=2)
        a = math.radians(rnd.uniform(200, 340))
        d.line([(cx, cy), (cx + r * 0.9 * math.cos(a), cy + r * 0.9 * math.sin(a))], fill=sec, width=3)
    return im


def sprite_colors(img, k=3):
    """Farbfamilie eines Sprites (nur als Referenz: Palette der sichtbaren Pixel)."""
    from bm_ref import palette
    a = np.asarray(img.convert("RGBA"))
    px = a[..., :3][a[..., 3] > 100]
    if len(px) == 0:
        return [((120, 190, 200), 1.0)]
    if len(px) > 6000:
        px = px[np.random.default_rng(3).choice(len(px), 6000, replace=False)]
    return palette(px, k=k)


def median_rgb(img):
    a = np.asarray(img.convert("RGB")).reshape(-1, 3)
    return tuple(int(v) for v in np.median(a, axis=0))


# ------------------------------------------------------------------------------------------- Szene-Anbindung

class RoomStyle:
    """Materialien eines Raums (werden einmal je Raum erzeugt): floor, wall; Farben gemessen."""

    def __init__(self, sc, ctx, name, poly, north, B):
        self.key = sc.key
        self.name = name
        fl_pat, wa_pat = patterns(sc.key, name)
        ffix = getattr(getattr(sc, "mapmod", None), "FLOOR_STYLE", {}).get(name)
        main, accent = ffix if ffix else measure_floor(sc.ref, poly)
        self.floor_rgb, self.floor_accent = main, accent
        # Karten-Hook: feste Wandfarben fuer Raeume, deren Nordband nicht mehr die Wand zeigt (Polus Comms: Nordkante
        # liegt seit dem Einbau der Wandmoebel an der Wandkrone, darueber ist Gelaende -> lila Waende)
        fixed = getattr(getattr(sc, "mapmod", None), "WALL_STYLE", {}).get(name)
        wc = dict(fixed) if fixed else measure_walls(sc, north, B)
        if wc is None:
            base = sc.cfg.get("hull") or (90, 96, 100)
            wc = {"main": _sh(base, 1.1), "accent": None, "trim": _sh(base, 0.8)}
        self.wall_rgb = wc["main"]
        self.wall_trim = wc["trim"]
        self.wall_accent = wc["accent"]
        seed = sum(ord(c) for c in name)
        self.floor = ctx.tex(f"sf_{name}", floor_image(fl_pat, main, accent, seed=seed), uv="world", scale=[1.0, 1.0])
        self.wall = ctx.tex(f"sw_{name}", wall_image(wa_pat, wc["main"], wc["trim"], wc["accent"], H=sc.H, seed=seed), uv="world",
                            scale=[sc.H, sc.H])
        self.fl_pat, self.wa_pat = fl_pat, wa_pat


def room_style(sc, ctx, name, poly, north, B):
    cache = sc.__dict__.setdefault("_styles", {})
    if name not in cache:
        cache[name] = RoomStyle(sc, ctx, name, poly, north, B)
    return cache[name]


def style_for(ctx):
    """Stil des Raums der Ctx (Raumdateien rufen art_floor usw. mit ihrer Ctx auf)."""
    sc = ctx.scene
    cache = sc.__dict__.setdefault("_styles", {})
    name = ctx.room
    if name in cache:
        return cache[name]
    poly = sc.rooms.get(name) or ctx.poly
    north = [e for e in sc.wall_edges() if e["room"] == name and e["kind"] == "north"]
    return room_style(sc, ctx, name, poly, north, sc.cfg["k"] * sc.H)
