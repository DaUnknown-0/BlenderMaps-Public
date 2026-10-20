# Echte 3D-Koerper fuer die Requisiten der eigenen Karten (Unknown's Atlas, optionale Erweiterungen), 19.10.: statt Prisma mit aufgeklebtem
# Sprite baut jede Art (museum_art-Kind) einen parametrischen Koerper aus Kaesten, Drehkoerpern, Rohren und Netzen auf
# dem Grundriss, den _atlas_props aus dem Collider bzw. der Standlinie bestimmt. Sprite-Pixel kommen nur als Bild-
# inhalt vor (Gemaelde, Karten, Pinnwand, Schilder), nie als Ersatz fuer Geometrie.
#
# Aufruf: build(P) bzw. MODELS[kind](P) -> Teileliste; P (Prop) traegt Grundriss (x0..x1, y0..y1), Hoehe h, Sprite, Standlinie und
# Materialhelfer. Front = Sueden (-y) wie im Spiel. z0 = 0 (alle Atlas-Karten sind einstoeckig).

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box as sbox
from shapely import affinity

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bm_spec import box, cyl, lathe, tube, obox, prism, mesh, tooth, blob, boulder, sprite_outline                # noqa: E402
import bm_models as M                                                                                              # noqa: E402

K = 0.55
OL = (18, 20, 24)
WOOD = (150, 105, 62)
WOOD_D = (95, 62, 36)
WALNUT = (110, 72, 46)
STEEL = (188, 194, 202)
STEEL_D = (92, 98, 106)
BRASS = (201, 162, 76)
GLASS_RGB = (176, 208, 232)


def _sh(rgb, f):
    return tuple(max(0, min(255, int(v * f))) for v in rgb)


class Prop:
    def __init__(self, ctx, sc, i, p, fp, h, spr, pad, base):
        self.ctx, self.sc, self.p, self.i = ctx, sc, p, i
        self.kind = p["name"]
        self.nm = f"am_{sc.key}_{i}"
        self.fp = fp
        self.x0, self.y0, self.x1, self.y1 = fp.bounds
        self.cx, self.cy = (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2
        self.w, self.d = self.x1 - self.x0, self.y1 - self.y0
        self.h = h
        self.spr = spr
        (sx0, sy0), (sx1, sy1) = p["min"], p["max"]
        self.sx0, self.sy0, self.sx1, self.sy1 = sx0, sy0, sx1, sy1
        self.ppm = spr.width / max(1e-6, sx1 - sx0)
        self.base, self.pad = base, pad
        a = np.asarray(spr)[..., 3] > 100
        ys, xs = np.where(a)
        if len(xs):
            self.vx0, self.vx1 = sx0 + xs.min() / self.ppm, sx0 + (xs.max() + 1) / self.ppm
            self.vytop, self.vybot = sy1 - ys.min() / self.ppm, sy1 - (ys.max() + 1) / self.ppm
        else:
            self.vx0, self.vx1, self.vytop, self.vybot = sx0, sx1, sy1, sy0
        self.seed = i
        self.rnd = random.Random(i * 31 + 7)

    # Materialien
    def m(self, suf, rgb):
        return self.ctx.color(f"{self.nm}_{suf}", tuple(int(v) for v in rgb))

    def g(self, suf, rgb, s=1.6):
        return self.ctx.glow(f"{self.nm}_{suf}", tuple(int(v) for v in rgb), s)

    def glass(self, suf="glass", rgb=GLASS_RGB, a=88):
        im = Image.new("RGBA", (8, 8), tuple(rgb) + (a,))
        t = self.ctx.tex(f"{self.nm}_{suf}", im, uv="part")
        self.ctx.scene.mats[t]["alpha"] = True
        return t

    def img(self, wx0, wy0, wx1, wy1, bg=None, up=2):
        """Sprite-Ausschnitt in Welt-Bildkoordinaten (y nach oben) als RGB (Durchsicht auf bg bzw. Mittelfarbe)."""
        c0 = int(round((wx0 - self.sx0) * self.ppm)); c1 = int(round((wx1 - self.sx0) * self.ppm))
        r0 = int(round((self.sy1 - wy1) * self.ppm)); r1 = int(round((self.sy1 - wy0) * self.ppm))
        c0, c1 = max(0, min(c0, self.spr.width - 1)), max(1, min(c1, self.spr.width))
        r0, r1 = max(0, min(r0, self.spr.height - 1)), max(1, min(r1, self.spr.height))
        if c1 <= c0 + 1 or r1 <= r0 + 1:
            return None
        sub = self.spr.crop((c0, r0, c1, r1))
        arr = np.asarray(sub)
        if bg is None:
            vis = arr[..., :3][arr[..., 3] > 100]
            bg = tuple(int(v) for v in vis.mean(0)) if len(vis) else (90, 90, 90)
        out = Image.new("RGBA", sub.size, tuple(bg) + (255,))
        out.alpha_composite(sub)
        out = out.convert("RGB")
        if up > 1:
            out = out.resize((out.width * up, out.height * up), Image.LANCZOS)
        return out

    def tex(self, suf, im):
        return self.ctx.tex(f"{self.nm}_{suf}", im, uv="part")

    def zvis(self):
        """Sichtbarer Bildbereich als Hoehe ueber der Standlinie (Wandbilder, Lampen)."""
        return max(0.0, (self.vybot - self.base) / K), max(0.3, (self.vytop - self.base) / K)


# ------------------------------------------------------------------------------------------------ Hilfen

def legs4(P, x0, y0, x1, y1, z0, z1, mat, s=0.05, inset=0.06, round_=False):
    out = []
    for fx in (x0 + inset, x1 - inset):
        for fy in (y0 + inset, y1 - inset):
            out.append(cyl(fx, fy, s / 2, z0, z1, mat, seg=8) if round_ else box(fx, fy, s, s, z0, z1, mat))
    return out


def candle(P, x, y, z, h=0.14, r=0.018, lit=True, wax=(236, 228, 200)):
    out = [cyl(x, y, r, z, z + h, P.m("wax", wax), seg=8)]
    if lit:
        out.append(lathe(x, y, [(0.0, z + h), (r * 0.7, z + h + 0.02), (r * 0.4, z + h + 0.06), (0.0, z + h + 0.09)],
                         P.g("flame", (255, 214, 120), 2.6), seg=8))
    return out


def drawers(P, x0, x1, yf, z0, z1, n, mat, knob, rows=1, dy=-1):
    """Schubladenfronten an der Suedseite (yf = Vorderkante): n Spalten, rows Reihen, Fuge + Knauf."""
    out = []
    w = (x1 - x0) / n
    hh = (z1 - z0) / rows
    for r in range(rows):
        for i in range(n):
            cx = x0 + w * (i + 0.5)
            zc = z0 + hh * (r + 0.5)
            out.append(box(cx, yf + dy * 0.012, w - 0.03, 0.024, zc - hh / 2 + 0.015, zc + hh / 2 - 0.015, mat, bevel=0.004, outline=OL))
            out.append(box(cx, yf + dy * 0.03, 0.06, 0.02, zc - 0.012, zc + 0.012, knob))
    return out


def doors(P, x0, x1, yf, z0, z1, n, mat, knob, dy=-1):
    out = []
    w = (x1 - x0) / n
    for i in range(n):
        cx = x0 + w * (i + 0.5)
        out.append(box(cx, yf + dy * 0.012, w - 0.025, 0.024, z0 + 0.015, z1 - 0.015, mat, bevel=0.004, outline=OL))
        kx = cx + (w / 2 - 0.06) * (1 if i % 2 == 0 else -1)
        out.append(cyl(kx, yf + dy * 0.03, 0.014, (z0 + z1) / 2 - 0.014, (z0 + z1) / 2 + 0.014, knob, seg=8))
    return out


def books(P, x0, x1, y, z, depth, hmax, seed=0, n=None, tilt=True):
    rnd = random.Random(seed)
    out = []
    x = x0 + 0.02
    pal = [(170, 60, 60), (60, 90, 150), (80, 130, 90), (200, 170, 80), (120, 80, 120), (220, 220, 210), (90, 60, 40)]
    j = 0
    while x < x1 - 0.04 and (n is None or j < n):
        bw = rnd.uniform(0.025, 0.05)
        bh = hmax * rnd.uniform(0.6, 1.0)
        out.append(box(x + bw / 2, y, bw, depth, z, z + bh, P.m(f"book{j % 7}", pal[j % 7]), outline=OL))
        x += bw + 0.004
        j += 1
    return out


def cabinet(P, x0, y0, x1, y1, z0, z1, rgb, dark=None, top=True, plinth=0.06):
    """Korpus: Seiten, Rueckwand, Boden, Deckel, Sockel."""
    dark = dark or _sh(rgb, 0.72)
    body, dk = P.m("body", rgb), P.m("dark", dark)
    t = 0.025
    out = [box(x0 + t / 2, (y0 + y1) / 2, t, y1 - y0, z0, z1, body, outline=OL),
           box(x1 - t / 2, (y0 + y1) / 2, t, y1 - y0, z0, z1, body, outline=OL),
           box((x0 + x1) / 2, y1 - t / 2, x1 - x0, t, z0, z1, body),
           box((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, z0, z0 + plinth, dk)]
    if top:
        out.append(box((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 + 0.02, y1 - y0 + 0.02, z1 - 0.03, z1, body, bevel=0.006, outline=OL))
    return out


def shelves(P, x0, y0, x1, y1, z0, z1, n, mat, items=True, seed=0, depth_items=None):
    out = []
    for k in range(n):
        z = z0 + (z1 - z0) * (k + 0.2) / n
        out.append(box((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, z - 0.02, z, mat))
        if items:
            out += books(P, x0 + 0.03, x1 - 0.03, (y0 + y1) / 2, z, (y1 - y0) * 0.7, (z1 - z0) / n * 0.65, seed=seed * 10 + k)
    return out


def pic(P, frame_rgb=(120, 80, 40), depth=0.04, border=0.05, y=None, img=True, z=None, x=None, bg=None, gold=False):
    """Bild an der Wand (Suedseite zeigt das Sprite): Rahmen + Leinwand."""
    z0, z1 = z or P.zvis()
    x0, x1 = x or (P.vx0, P.vx1)
    y = P.base + 0.02 if y is None else y
    fr = P.m("frame", frame_rgb if not gold else BRASS)
    out = [box((x0 + x1) / 2, y + depth / 2, x1 - x0, depth, z0, z1, fr, bevel=0.01, outline=OL)]
    if img:
        im = P.img(x0 + border, P.base + (z0 + border / K * 0.55) * K, x1 - border, P.base + (z1 - border) * K, bg=bg)
        if im is not None:
            c = box((x0 + x1) / 2, y - 0.004, x1 - x0 - 2 * border, 0.012, z0 + border, z1 - border, fr)
            c["front"] = P.tex("pic", im)
            out.append(c)
    return out


def panel_south(P, x0, x1, y, z0, z1, wx0, wy0, wx1, wy1, suf="face", depth=0.03, mat=None, bg=None):
    """Senkrechte Platte mit Sprite-Ausschnitt (Welt-Bildkoordinaten) auf der Suedseite."""
    im = P.img(wx0, wy0, wx1, wy1, bg=bg)
    b = box((x0 + x1) / 2, y + depth / 2, x1 - x0, depth, z0, z1, mat or P.m(suf + "_side", (60, 60, 64)))
    if im is not None:
        b["front"] = P.tex(suf, im)
    return b


def ring_posts(P, cx, cy, rx, ry, n, z0, z1, r, mat, a0=0.0):
    out = []
    for i in range(n):
        a = a0 + 2 * math.pi * i / n
        out.append(cyl(cx + rx * math.cos(a), cy + ry * math.sin(a), r, z0, z1, mat, seg=8))
    return out


def roof_hip(P, x0, y0, x1, y1, z0, z1, mat, over=0.15):
    """Walmdach als Netz: Traufe (x0..x1, y0..y1) auf z0, First auf z1."""
    x0, y0, x1, y1 = x0 - over, y0 - over, x1 + over, y1 + over
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rl = (x1 - x0) * 0.25
    verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (cx - rl, cy, z1), (cx + rl, cy, z1)]
    faces = [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4), (3, 2, 1, 0)]
    return mesh(verts, faces, mat, outline=OL)


def roof_gable(P, x0, y0, x1, y1, z0, z1, mat, over=0.12, along="x"):
    x0, y0, x1, y1 = x0 - over, y0 - over, x1 + over, y1 + over
    if along == "x":
        cy = (y0 + y1) / 2
        verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, cy, z1), (x1, cy, z1)]
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (3, 2, 1, 0)]
    else:
        cx = (x0 + x1) / 2
        verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (cx, y0, z1), (cx, y1, z1)]
        faces = [(1, 2, 5, 4), (3, 0, 4, 5), (0, 1, 4), (2, 3, 5), (3, 2, 1, 0)]
    return mesh(verts, faces, mat, outline=OL)


def tripod(P, cx, cy, z1, spread=0.3, r=0.012, mat=None, z0=0.0):
    mat = mat or P.m("tripod", (70, 60, 50))
    out = []
    for i in range(3):
        a = math.radians(90 + 120 * i)
        out.append(tube([(cx + spread * math.cos(a), cy + spread * math.sin(a), z0), (cx, cy, z1)], r, mat, seg=6))
    return out


def ladder(P, x, y0, y1, z0, z1, mat, w=0.5, along="z", lean=0.0):
    """Leiter senkrecht in der Ebene y0 (Holme bei x +- w/2), Sprossen alle 0,3; lean = Fusspunkt nach Sueden."""
    out = []
    n = max(2, int((z1 - z0) / 0.3))
    for sx in (-1, 1):
        out.append(tube([(x + sx * w / 2, y0 - lean, z0), (x + sx * w / 2, y0, z1)], 0.022, mat, seg=6))
    for k in range(1, n):
        t = k / n
        yy = y0 - lean * (1 - t)
        out.append(tube([(x - w / 2, yy, z0 + (z1 - z0) * t), (x + w / 2, yy, z0 + (z1 - z0) * t)], 0.015, mat, seg=6))
    return out


def chair(P, cx, cy, yaw=0.0, rgb=(110, 72, 46), seat_z=0.45, w=0.42, back_h=0.5, arms=False, cushion=None):
    """Stuhl mit Lehne auf der +y-Seite (yaw 0 = Lehne im Norden)."""
    f = M._fx(yaw)
    mat = P.m("chair", rgb)
    out = [obox((cx, cy, seat_z - 0.02), (w, w, 0.04), mat, yaw=yaw, outline=OL)]
    if cushion:
        out.append(obox((cx, cy, seat_z + 0.015), (w - 0.04, w - 0.04, 0.03), P.m("cush", cushion), yaw=yaw))
    o = f(0, w * 0.45, 0)
    out.append(obox((cx + o[0], cy + o[1], seat_z + back_h / 2), (w, 0.035, back_h), mat, yaw=yaw, outline=OL))
    for sx in (-1, 1):
        for sy in (-1, 1):
            o = f(sx * w * 0.42, sy * w * 0.42, 0)
            out.append(cyl(cx + o[0], cy + o[1], 0.018, 0.0, seat_z - 0.02, mat, seg=6))
    if arms:
        for sx in (-1, 1):
            o = f(sx * (w / 2 - 0.02), 0, 0)
            out.append(obox((cx + o[0], cy + o[1], seat_z + 0.2), (0.04, w * 0.9, 0.04), mat, yaw=yaw))
            o2 = f(sx * (w / 2 - 0.02), -w * 0.4, 0)
            out.append(cyl(cx + o2[0], cy + o2[1], 0.015, seat_z, seat_z + 0.2, mat, seg=6))
    return out


def armchair(P, x0, y0, x1, y1, rgb, dark=None, h_seat=0.42, h_back=0.95, arm_h=0.62):
    dark = dark or _sh(rgb, 0.7)
    body, dk = P.m("uph", rgb), P.m("uph_d", dark)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, d = x1 - x0, y1 - y0
    aw = min(0.16, w * 0.2)
    out = [box(cx, cy, w, d, 0.06, h_seat, body, bevel=0.02, outline=OL),
           box(cx, y1 - 0.12, w, 0.24, h_seat, h_back, dk, bevel=0.025, outline=OL),
           box(x0 + aw / 2, cy - 0.05, aw, d - 0.1, h_seat, arm_h, dk, bevel=0.02, outline=OL),
           box(x1 - aw / 2, cy - 0.05, aw, d - 0.1, h_seat, arm_h, dk, bevel=0.02, outline=OL),
           box(cx, cy - 0.1, w - 2 * aw - 0.02, d - 0.35, h_seat, h_seat + 0.07, body, bevel=0.02, outline=OL)]
    out += legs4(P, x0, y0, x1, y1, 0.0, 0.06, P.m("foot", (60, 40, 30)), s=0.05, inset=0.05)
    return out


def counter(P, x0, y0, x1, y1, h, rgb, top_rgb=None, skirt=None, facing="S"):
    top_rgb = top_rgb or _sh(rgb, 1.15)
    body, top = P.m("body", rgb), P.m("top", top_rgb)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    out = [box(cx, cy, x1 - x0, y1 - y0, 0.0, h - 0.04, body, outline=OL),
           box(cx, cy, x1 - x0 + 0.06, y1 - y0 + 0.06, h - 0.04, h, top, bevel=0.01, outline=OL)]
    if skirt:
        out.append(box(cx, y0 - 0.004, x1 - x0, 0.008, 0.0, h * 0.4, P.m("skirt", skirt)))
    return out


def lamp_glow(P, x, y, z, r=0.09, rgb=(255, 230, 160), s=3.0):
    return lathe(x, y, [(0.0, z - r), (r * 0.85, z - r * 0.5), (r, z), (r * 0.85, z + r * 0.5), (0.0, z + r)], P.g("lamp", rgb, s), seg=12)


def disc_s(P, x, y, z, r, t, mat, seg=20, outline=None):
    """Scheibe in der x-z-Ebene (Zifferblatt, Luefter an der Suedseite), Dicke t nach Sueden."""
    return lathe(x, y, [(0.0, z - t), (r, z - t), (r, z), (0.0, z)], mat, seg=seg, outline=outline, tilt=(90.0, 90.0, z))


def wheel(P, cx, cy, z, r, w, mat, axis="x"):
    """Rad/Scheibe mit Achse entlang x oder y (Drehkoerper gekippt)."""
    prof = [(0.0, z - w / 2), (r, z - w / 2), (r, z + w / 2), (0.0, z + w / 2)]
    tilt = (90.0, 90.0, z) if axis == "y" else (90.0, 0.0, z)
    return lathe(cx, cy, prof, mat, seg=24, outline=OL, tilt=tilt)


def sarcophagus_poly(cx, cy, L, w, yaw=0.0):
    """Sechseck eines Sarkophags (Laengsachse y bei yaw 0, Kopf = +y)."""
    pts = [(-w * 0.32, -L / 2), (w * 0.32, -L / 2), (w / 2, L * 0.18), (w * 0.4, L / 2), (-w * 0.4, L / 2), (-w / 2, L * 0.18)]
    pg = Polygon([(cx + x, cy + y) for x, y in pts])
    return affinity.rotate(pg, yaw, origin=(cx, cy))


# ------------------------------------------------------------------------------------------------ Familien

def kind_shelf(P, rgb=WOOD, dark=None, n=None, items=True, facing="S"):
    n = n or max(2, min(6, int(P.h / 0.4)))
    depth = min(P.d, 0.45)
    y1 = P.y0 + depth
    out = cabinet(P, P.x0, P.y0, P.x1, y1, 0.0, P.h, rgb, dark)
    out += shelves(P, P.x0 + 0.03, P.y0 + 0.03, P.x1 - 0.03, y1 - 0.03, 0.08, P.h - 0.05, n, P.m("board", _sh(rgb, 0.9)), items, P.seed)
    return out


def kind_cabinet_doors(P, rgb=WOOD, nd=2, glass=False, drawers_n=0):
    depth = min(P.d, 0.5)
    y1 = P.y0 + depth
    out = cabinet(P, P.x0, P.y0, P.x1, y1, 0.0, P.h, rgb)
    zsplit = 0.0
    if drawers_n:
        zsplit = P.h * 0.35
        out += drawers(P, P.x0 + 0.03, P.x1 - 0.03, P.y0, 0.06, zsplit, drawers_n, P.m("drawer", _sh(rgb, 1.08)), P.m("knob", BRASS))
    if glass:
        gm = P.glass()
        w = (P.x1 - P.x0 - 0.06) / nd
        for i in range(nd):
            cx = P.x0 + 0.03 + w * (i + 0.5)
            out.append(box(cx, P.y0 + 0.012, w - 0.02, 0.012, zsplit + 0.05, P.h - 0.05, gm))
            out.append(box(cx, P.y0 + 0.006, w - 0.01, 0.012, zsplit + 0.03, zsplit + 0.06, P.m("mull", _sh(rgb, 0.8))))
            out.append(box(cx, P.y0 + 0.006, w - 0.01, 0.012, P.h - 0.07, P.h - 0.04, P.m("mull", _sh(rgb, 0.8))))
            out.append(box(cx - w / 2 + 0.012, P.y0 + 0.006, 0.024, 0.012, zsplit + 0.03, P.h - 0.04, P.m("mull", _sh(rgb, 0.8))))
    else:
        out += doors(P, P.x0 + 0.03, P.x1 - 0.03, P.y0, zsplit + 0.02, P.h - 0.04, nd, P.m("door", _sh(rgb, 1.06)), P.m("knob", BRASS))
    return out


def kind_desk(P, top_rgb=WOOD, leg_rgb=None, h=None, drawers_side=True, items=()):
    h = h or min(P.h, 0.78)
    leg_rgb = leg_rgb or _sh(top_rgb, 0.75)
    out = M.table(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, h=h, top_rgb=top_rgb, leg_rgb=leg_rgb, thick=0.05)
    if drawers_side and P.w > 1.2:
        bw = min(0.5, P.w * 0.3)
        out.append(box(P.x1 - bw / 2 - 0.04, P.cy, bw, P.d - 0.1, 0.0, h - 0.05, P.m("ped", _sh(top_rgb, 0.85)), outline=OL))
        out += drawers(P, P.x1 - bw - 0.04, P.x1 - 0.04, P.y0 + 0.05, 0.06, h - 0.08, 1, P.m("drawer", _sh(top_rgb, 0.95)), P.m("knob", BRASS), rows=3)
    for it in items:
        out += it(P, h)
    return out


def it_lamp(P, h, dx=0.3, dy=0.05, rgb=(60, 120, 70)):
    x, y = P.x1 - dx, P.cy + dy
    return [cyl(x, y, 0.06, h, h + 0.015, P.m("lampbase", BRASS), seg=12),
            cyl(x, y, 0.012, h, h + 0.32, P.m("lampbase", BRASS), seg=8),
            lathe(x, y, [(0.0, h + 0.28), (0.07, h + 0.28), (0.13, h + 0.34), (0.0, h + 0.36)], P.g("shade", rgb, 1.8), seg=14, outline=OL)]


def it_book(P, h, dx=-0.1, dy=0.0, open_=True, rgb=(238, 232, 214)):
    x, y = P.cx + dx, P.cy + dy
    if open_:
        return [obox((x - 0.11, y, h + 0.012), (0.2, 0.26, 0.02), P.m("page", rgb), roll=0.0, pitch=4.0),
                obox((x + 0.11, y, h + 0.012), (0.2, 0.26, 0.02), P.m("page", rgb), pitch=-4.0)]
    return [box(x, y, 0.2, 0.28, h, h + 0.04, P.m("bookc", (120, 40, 40)), outline=OL)]


def it_paper(P, h, dx=0.0, dy=0.0, rot=8.0):
    return [box(P.cx + dx, P.cy + dy, 0.21, 0.29, h, h + 0.004, P.m("paper", (236, 236, 230)), rot=rot)]


def it_typewriter(P, h, dx=0.0, dy=0.05):
    x, y = P.cx + dx, P.cy + dy
    out = [box(x, y, 0.36, 0.3, h, h + 0.12, P.m("tw", (50, 52, 58)), bevel=0.01, outline=OL),
           box(x, y + 0.1, 0.4, 0.03, h + 0.12, h + 0.2, P.m("tw", (50, 52, 58))),
           box(x, y + 0.11, 0.24, 0.006, h + 0.2, h + 0.42, P.m("paper", (236, 236, 230)))]
    for r in range(3):
        for c in range(8):
            out.append(cyl(x - 0.14 + c * 0.04, y - 0.1 + r * 0.06, 0.012, h + 0.12, h + 0.135, P.m("key", (200, 200, 196)), seg=6))
    return out


def it_candle(P, h, dx=-0.3, dy=0.0):
    return candle(P, P.cx + dx, P.cy + dy, h, 0.12)


# ------------------------------------------------------------------------------------------------ Modelle

MODELS = {}
VARIANTS = []     # fn(P, kind) -> Teileliste oder None: ersetzt eine Art fuer bestimmte Karten (Erweiterungen, bm_ext.py)


def model(*names):
    def deco(fn):
        for n in names:
            MODELS[n] = fn
        return fn
    return deco


def variant(fn):
    VARIANTS.append(fn)
    return fn


def build(P):
    for v in VARIANTS:
        r = v(P, P.kind)
        if r is not None:
            return r
    return MODELS[P.kind](P)


# ---- Regale, Schraenke

@model("regal", "regal_shop", "regal_werk", "funkregal")
def m_regal(P):
    pal = {"regal_shop": (170, 120, 78), "regal_werk": (200, 204, 208), "funkregal": (128, 92, 60)}
    rgb = pal.get(P.kind, (150, 105, 62))
    return kind_shelf(P, rgb)


@model("hochregal")
def m_hochregal(P):
    steel = P.m("rack", (80, 110, 160))
    out = []
    depth = min(P.d, 1.2)
    n = max(2, int(P.w / 1.2))
    for i in range(n + 1):
        x = P.x0 + P.w * i / n
        for y in (P.y0 + 0.05, P.y0 + depth - 0.05):
            out.append(box(x, y, 0.07, 0.07, 0.0, P.h, steel, outline=OL))
    levels = max(2, int(P.h / 0.9))
    for k in range(levels):
        z = 0.1 + (P.h - 0.2) * k / levels
        out.append(box(P.cx, P.y0 + depth / 2, P.w, depth, z, z + 0.05, steel, outline=OL))
        for i in range(n):
            bx = P.x0 + P.w * (i + 0.5) / n
            out += M.crate_stack(P.ctx, f"{P.nm}_c{k}{i}", bx, P.y0 + depth / 2, min(0.9, P.w / n - 0.15), 0.42, n=1, seed=k * 7 + i)
            out[-3:] = M.lift(out[-3:], z + 0.05)
    return out


@model("schrank")
def m_schrank(P):
    out = cabinet(P, P.x0, P.y0, P.x1, P.y0 + min(P.d, 0.45), 0.0, P.h, (236, 236, 232), (170, 170, 166))
    out += doors(P, P.x0 + 0.03, P.x1 - 0.03, P.y0, 0.06, P.h - 0.05, 1, P.m("door", (244, 244, 240)), P.m("knob", (120, 120, 120)))
    cr = P.m("cross", (210, 40, 40))
    out.append(box(P.cx, P.y0 - 0.03, 0.06, 0.01, 0.14, 0.4, cr))
    out.append(box(P.cx, P.y0 - 0.03, 0.26, 0.01, 0.24, 0.3, cr))
    return out


@model("schaltschrank")
def m_cabinets(P):
    k = P.kind
    if k == "schaltschrank":
        out = cabinet(P, P.x0, P.y0, P.x1, P.y0 + min(P.d, 0.5), 0.0, P.h, (182, 188, 196), (96, 102, 110))
        out += doors(P, P.x0 + 0.03, P.x1 - 0.03, P.y0, 0.06, P.h * 0.55, 1, P.m("door", (190, 196, 204)), P.m("knob", (60, 60, 64)))
        for r in range(3):
            z = P.h * 0.6 + (P.h * 0.38) * r / 3
            out.append(box(P.cx, P.y0 - 0.006, P.w - 0.1, 0.012, z + 0.02, z + P.h * 0.11, P.m("panel", (70, 74, 82)), outline=OL))
            for c in range(3):
                out.append(cyl(P.x0 + 0.15 + c * 0.14, P.y0 - 0.015, 0.014, z + 0.05, z + 0.08, P.g(f"led{c}", [(230, 70, 60), (80, 220, 90), (240, 200, 70)][c], 2.0), seg=6))
        out.append(box(P.cx, P.y0 - 0.006, 0.18, 0.012, P.h * 0.4, P.h * 0.5, P.g("warn", (240, 200, 60), 1.3)))
        return out
    return None


@model("garderobe")
def m_garderobe(P):
    steel = P.m("rail", (120, 122, 128))
    out = []
    if P.kind == "garderobe" and P.w < 1.5:
        # Wandgarderobe: Leiste mit Haken, drei Maentel
        z = min(P.h, 1.6)
        out.append(box(P.cx, P.base + 0.06, P.w, 0.03, z - 0.04, z, P.m("leiste", (110, 72, 46)), outline=OL))
        cols = [(60, 70, 140), (160, 60, 60), (200, 120, 60), (70, 90, 70)]
        for j in range(3):
            x = P.x0 + P.w * (j + 0.5) / 3
            out.append(cyl(x, P.base + 0.03, 0.01, z - 0.02, z, steel, seg=6))
            out.append(blob(x, P.base + 0.15, z - 0.45, 0.13, 0.1, 0.45, (P.m(f"coat{j}", cols[j]), P.m(f"coat{j}_d", _sh(cols[j], 0.75))), seed=j, seg=10, rings=6))
        return out
    # Kleiderstange auf Rollen
    z = min(P.h, 1.7)
    y = P.y0 + min(P.d, 0.5) / 2
    for x in (P.x0 + 0.05, P.x1 - 0.05):
        out.append(cyl(x, y, 0.016, 0.03, z, steel, seg=8))
        out.append(tube([(x, y - 0.22, 0.03), (x, y + 0.22, 0.03)], 0.014, steel, seg=6))
    out.append(tube([(P.x0 + 0.05, y, z), (P.x1 - 0.05, y, z)], 0.014, steel, seg=8))
    cols = [(50, 50, 56), (230, 226, 210), (236, 234, 222), (210, 170, 60), (120, 40, 60)]
    n = max(3, min(6, int(P.w / 0.45)))
    for j in range(n):
        x = P.x0 + 0.2 + (P.w - 0.4) * (j + 0.5) / n
        out.append(blob(x, y, z - 0.5, 0.16, 0.08, 0.5, (P.m(f"cl{j}", cols[j % 5]), P.m(f"cl{j}_d", _sh(cols[j % 5], 0.75))), seed=j, seg=10, rings=6))
        out.append(tube([(x, y, z - 0.02), (x, y, z - 0.09)], 0.006, steel, seg=6))
    return out


# ---- Tische, Pulte

@model("tisch_lang", "vermittlungstisch", "kartentisch", "werktisch", "laborbank", "saegetisch", "admintisch")
def m_tables(P):
    k = P.kind
    if k == "tisch_lang":
        h = min(P.h, 0.78)
        out = M.table(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, h=h, top_rgb=(172, 120, 72), leg_rgb=(110, 72, 46))
        for j in range(5):
            x = P.x0 + 0.3 + (P.w - 0.6) * j / 4
            out.append(cyl(x, P.cy, 0.07, h, h + 0.008, P.m("plate", (230, 228, 220)), seg=14))
        out.append(lamp_glow(P, P.cx, P.cy, h + 0.12, r=0.05, s=2.2))
        return out
    if k == "vermittlungstisch":
        h = min(P.h, 0.78)
        out = M.table(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, h=h, top_rgb=(172, 120, 72), leg_rgb=(110, 72, 46))
        for j in range(3):
            x = P.x0 + P.w * (j + 0.5) / 3
            out.append(box(x, P.cy, 0.18, 0.14, h, h + 0.08, P.m("phone", (40, 40, 44)), bevel=0.01, outline=OL))
            out.append(cyl(x, P.cy, 0.05, h + 0.08, h + 0.09, P.m("dial", (226, 226, 220)), seg=12))
        return out
    if k == "kartentisch":
        h = min(P.h, 0.9)
        out = M.table(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, h=h - 0.1, top_rgb=WOOD, leg_rgb=WOOD_D)
        im = P.img(P.vx0 + 0.1, P.base + 0.25, P.vx1 - 0.1, P.vytop - 0.15)
        t = obox((P.cx, P.cy, h - 0.03), (P.w - 0.05, P.d - 0.05, 0.04), P.m("mapboard", (226, 218, 190)), roll=-18.0, outline=OL)
        out.append(t)
        if im is not None:
            # Karte als duennes Prisma darueber (nur Prismen tragen Bilder): flach auf der Platte, leicht hoeher
            m = box(P.cx, P.cy, P.w - 0.15, P.d - 0.25, h + 0.005, h + 0.012, P.m("mapside", (226, 218, 190)))
            m["top"] = P.tex("map", im)
            out.append(m)
        return out
    if k == "werktisch":
        h = min(P.h, 0.9)
        out = counter(P, P.x0, P.y0, P.x1, P.y1, h, (208, 214, 220), (232, 236, 240))
        out += drawers(P, P.x0 + 0.05, P.x1 - 0.05, P.y0, 0.1, h - 0.1, max(3, int(P.w / 0.9)), P.m("drawer", (216, 220, 226)), P.m("knob", (80, 80, 86)))
        for j, c in enumerate(((200, 170, 60), (200, 170, 60), (230, 230, 230), (200, 170, 60))):
            out.append(box(P.x0 + 0.3 + j * 0.3, P.cy, 0.14, 0.1, h, h + 0.04, P.m(f"part{j}", c), outline=OL))
        return out
    if k == "laborbank":
        return M.lab_bench(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, h=min(P.h, 0.9), seed=P.seed)
    if k == "saegetisch":
        h = min(P.h, 0.85)
        out = M.table(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, h=h, top_rgb=(172, 120, 72), leg_rgb=(110, 72, 46), thick=0.08)
        out.append(wheel(P, P.cx, P.cy, h + 0.05, 0.16, 0.01, P.m("blade", (190, 194, 200)), axis="x"))
        out.append(box(P.cx, P.cy, 0.35, 0.3, h + 0.2, h + 0.35, P.m("hood", (190, 60, 50)), bevel=0.02, outline=OL))
        out.append(box(P.cx - P.w * 0.2, P.cy - 0.1, P.w * 0.55, 0.12, h, h + 0.05, P.m("plank", (200, 160, 100)), outline=OL))
        return out
    if k == "admintisch":
        h = min(P.h, 0.9)
        out = legs4(P, P.x0, P.y0, P.x1, P.y1, 0.0, h - 0.1, P.m("leg", (176, 182, 190)), s=0.06, inset=0.08)
        out.append(box(P.cx, P.cy, P.w, P.d, h - 0.1, h - 0.02, P.m("frame", (196, 202, 210)), bevel=0.01, outline=OL))
        out.append(box(P.cx, P.cy, P.w - 0.1, P.d - 0.1, h - 0.02, h, P.g("holo", (140, 200, 240), 1.8)))
        return out
    return None


# ---- Sitzmoebel

@model("bank", "liege")
def m_benches(P):
    k = P.kind
    if k == "liege":
        h = min(P.h, 0.5)
        out = [box(P.cx, P.cy, P.w, P.d, h - 0.08, h, P.m("liege", (236, 238, 240)), bevel=0.015, outline=OL),
               box(P.cx + P.w * 0.15, P.cy, P.w * 0.6, P.d - 0.06, h, h + 0.03, P.m("pad", (120, 170, 190)), bevel=0.01),
               cyl(P.x0 + 0.3, P.cy, 0.14, h, h + 0.04, P.m("pillow", (236, 238, 240)), ry=0.1, seg=16)]
        out += legs4(P, P.x0, P.y0, P.x1, P.y1, 0.0, h - 0.08, P.m("leg", (120, 124, 130)), s=0.04)
        return out
    out = M.bench(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, h=0.44, rgb=(150, 105, 62), leg_rgb=(110, 72, 46), slats=0)
    if P.sc.key == "wald":
        out.append(box(P.cx, P.y1 - 0.04, P.w, 0.05, 0.6, 0.9, P.m("back", (150, 105, 62)), bevel=0.01, outline=OL))
        out.append(box(P.cx, P.y1 - 0.04, P.w, 0.05, 0.44, 0.55, P.m("back", (150, 105, 62)), bevel=0.01, outline=OL))
        for x in (P.x0 + 0.06, P.x1 - 0.06):
            out.append(box(x, P.y1 - 0.04, 0.04, 0.05, 0.44, 0.9, P.m("leg2", (90, 94, 100))))
    return out


# ---- Theken, Buden, Kassen

@model("tresen_kasse", "infotheke", "theke", "kasse", "kassenhaeuschen", "bude", "kuehltruhe")
def m_counters(P):
    k = P.kind
    if k == "tresen_kasse":
        h = min(P.h, 1.0)
        out = counter(P, P.x0, P.y0, P.x1, P.y1, h, (150, 105, 62), (232, 196, 140))
        out += doors(P, P.x0 + 0.05, P.x1 - 0.05, P.y0, 0.08, h - 0.08, 3, P.m("door", (158, 110, 66)), P.m("knob", BRASS))
        out.append(box(P.x1 - 0.4, P.cy, 0.34, 0.3, h, h + 0.22, P.m("reg", (50, 52, 58)), bevel=0.01, outline=OL))
        out.append(box(P.x1 - 0.4, P.cy - 0.16, 0.28, 0.01, h + 0.06, h + 0.18, P.g("regscr", (120, 200, 180), 1.5)))
        for j, c in enumerate(((190, 120, 70), (70, 120, 190), (90, 160, 90), (200, 180, 90), (150, 80, 160))):
            out.append(box(P.x0 + 0.25 + j * 0.16, P.cy, 0.1, 0.14, h, h + 0.14, P.m(f"book{j}", c), outline=OL))
        return out
    if k == "infotheke":
        h = min(P.h, 1.0)
        ell = affinity.scale(sbox(P.x0, P.y0, P.x1, P.y1).centroid.buffer(1.0, 48), P.w / 2, P.d / 2)
        out = [prism(ell, 0.0, h - 0.05, P.m("body", (150, 105, 62)), outline=OL),
               prism(affinity.scale(ell, 1.03, 1.03), h - 0.05, h, P.m("top", (214, 160, 96)), bevel=0.01, outline=OL),
               prism(affinity.scale(ell, 0.68, 0.68), h - 0.06, h + 0.02, P.m("inner", (140, 96, 58)), outline=OL)]
        out += M.monitor(P.ctx, P.nm + "_mon", P.cx, P.cy + P.d * 0.2, h + 0.02, 0.32, 0.22, yaw=0.0)
        im = Image.new("RGB", (64, 64), (40, 90, 200))
        from PIL import ImageDraw, ImageFont
        try:
            f = ImageFont.truetype("arialbd.ttf", 48)
        except Exception:
            f = ImageFont.load_default()
        ImageDraw.Draw(im).text((32, 32), "i", fill=(255, 255, 255), font=f, anchor="mm")
        s = box(P.cx, P.y0 - 0.005, 0.26, 0.012, h * 0.45, h * 0.45 + 0.26, P.m("sign", (40, 90, 200)))
        s["front"] = P.tex("info", im)
        out.append(s)
        return out
    if k == "theke":
        h = min(P.h, 1.0)
        out = counter(P, P.x0, P.y0, P.x1, P.y1, h, (190, 60, 70), (176, 120, 72), skirt=(236, 236, 230))
        for j in range(int(P.w / 0.4)):
            x = P.x0 + 0.2 + j * 0.4
            out.append(box(x, P.y0 - 0.002, 0.2, 0.004, 0.0, h * 0.4, P.m("stripe", (200, 60, 70))))
        return out
    if k in ("kasse", "kassenhaeuschen", "bude"):
        museum = P.sc.key == "museum"
        hw = P.h
        red, cream = (190, 60, 70), (236, 230, 214)
        out = []
        d = P.d
        if museum:
            # Ticket-Haeuschen Museum: Theke mit Holzsockel, Fenster, gestreifte Markise
            hc = min(0.95, hw * 0.3)
            out += counter(P, P.x0, P.y0, P.x1, P.y1, hc, (118, 80, 50), (150, 105, 62))
            out.append(box(P.cx, P.cy, P.w - 0.1, d - 0.1, hc, hw * 0.78, P.m("hut", cream), outline=OL))
            out.append(box(P.cx, P.y0 + 0.04, P.w - 0.3, 0.01, hc + 0.1, hw * 0.78 - 0.1, P.g("window", (190, 215, 235), 0.9)))
            out.append(box(P.cx, P.y0 - 0.02, P.w - 0.3, 0.02, hc, hc + 0.04, P.m("sill", (236, 236, 236))))
            z0, z1 = hw * 0.78, hw
            out.append(box(P.cx, P.cy - 0.08, P.w + 0.2, d + 0.16, z0, z1 - 0.1, P.m("awn", red), bevel=0.03, outline=OL))
            for j in range(int((P.w + 0.2) / 0.3)):
                if j % 2 == 0:
                    out.append(box(P.x0 - 0.1 + 0.15 + j * 0.3, P.y0 - 0.17, 0.3, 0.01, z0, z1 - 0.1, P.m("awn_w", cream)))
            im = Image.new("RGB", (256, 72), (120, 40, 50))
            from PIL import ImageDraw, ImageFont
            try:
                f = ImageFont.truetype("arialbd.ttf", 44)
            except Exception:
                f = ImageFont.load_default()
            ImageDraw.Draw(im).text((128, 36), "TICKETS", fill=(236, 230, 214), font=f, anchor="mm")
            s = box(P.cx, P.y0 - 0.03, P.w * 0.6, 0.03, hw * 0.78 - 0.32, hw * 0.78 - 0.1, P.m("sign", (120, 40, 50)), outline=OL)
            s["front"] = P.tex("tickets", im)
            out.append(s)
            return out
        # Park: Haeuschen mit Satteldach bzw. Bude mit Markise
        hc = min(0.95, hw * 0.28)
        if k == "bude":
            out += counter(P, P.x0, P.y0, P.x1, P.y1, hc, (190, 60, 70), (160, 112, 66), skirt=cream)
            for j in range(int(P.w / 0.3)):
                if j % 2 == 0:
                    out.append(box(P.x0 + 0.15 + j * 0.3, P.y0 - 0.004, 0.3, 0.004, 0.0, hc - 0.05, P.m("stripe_w", cream)))
            for x in (P.x0 + 0.06, P.x1 - 0.06):
                out.append(cyl(x, P.cy, 0.03, hc, hw - 0.3, P.m("post", (150, 105, 62)), seg=8))
            out.append(box(P.cx, P.cy - 0.1, P.w + 0.2, d + 0.3, hw - 0.5, hw - 0.3, P.m("awn", red), bevel=0.03, outline=OL))
            for j in range(int((P.w + 0.2) / 0.3)):
                if j % 2 == 0:
                    out.append(box(P.x0 - 0.1 + 0.15 + j * 0.3, P.y0 - 0.26, 0.3, 0.01, hw - 0.5, hw - 0.3, P.m("awn_w", cream)))
            for j in range(int((P.w + 0.2) / 0.22)):
                out.append(lamp_glow(P, P.x0 - 0.1 + 0.11 + j * 0.22, P.y0 - 0.26, hw - 0.52, r=0.03, s=2.6))
            im = Image.new("RGB", (256, 72), (40, 36, 40))
            from PIL import ImageDraw, ImageFont
            try:
                f = ImageFont.truetype("arialbd.ttf", 44)
            except Exception:
                f = ImageFont.load_default()
            ImageDraw.Draw(im).text((128, 36), "CANDY", fill=(240, 200, 70), font=f, anchor="mm")
            s = box(P.cx, P.y0 - 0.2, P.w * 0.6, 0.03, hw - 0.28, hw, P.m("sign", (40, 36, 40)), outline=OL)
            s["front"] = P.tex("candy", im)
            out.append(s)
            return out
        out.append(box(P.cx, P.cy, P.w, d, 0.0, hc, P.m("base", red), outline=OL))
        out.append(box(P.cx, P.cy, P.w - 0.04, d - 0.04, hc, hw * 0.62, P.m("hut", cream), outline=OL))
        out.append(box(P.cx, P.y0 - 0.005, P.w * 0.45, 0.01, hc + 0.1, hw * 0.62 - 0.15, P.g("window", (240, 210, 130), 1.3)))
        out.append(box(P.cx, P.y0 - 0.02, P.w * 0.5, 0.03, hc + 0.06, hc + 0.1, P.m("sill", (120, 80, 50))))
        out.append(box(P.cx, P.cy, P.w + 0.1, d + 0.1, hw * 0.62, hw * 0.75, P.m("fascia", red), outline=OL))
        out.append(roof_gable(P, P.x0, P.y0, P.x1, P.y1, hw * 0.75, hw, P.m("roof", (170, 50, 60)), over=0.15, along="y"))
        im = Image.new("RGB", (256, 72), (20, 24, 34))
        from PIL import ImageDraw, ImageFont
        try:
            f = ImageFont.truetype("arialbd.ttf", 44)
        except Exception:
            f = ImageFont.load_default()
        ImageDraw.Draw(im).text((128, 36), "TICKETS", fill=(120, 230, 240), font=f, anchor="mm")
        s = box(P.cx, P.y0 - 0.18, P.w * 0.45, 0.03, hw * 0.78, hw * 0.9, P.g("sign", (20, 24, 34), 1.4), outline=OL)
        s["front"] = P.tex("tickets", im)
        out.append(s)
        return out
    if k == "kuehltruhe":
        h = min(P.h, 1.0)
        out = [box(P.cx, P.cy, P.w, P.d, 0.0, h - 0.12, P.m("body", (236, 238, 240)), bevel=0.01, outline=OL),
               box(P.cx, P.cy, P.w - 0.06, P.d - 0.06, h - 0.12, h, P.glass("lid", a=100)),
               box(P.cx, P.cy, P.w, 0.04, h - 0.12, h, P.m("rim", (190, 196, 204)))]
        for j, c in enumerate(((230, 150, 190), (240, 230, 170), (170, 220, 160), (180, 120, 80))):
            out.append(box(P.x0 + 0.2 + j * (P.w - 0.4) / 3, P.cy, 0.22, 0.3, h - 0.3, h - 0.14, P.m(f"ice{j}", c), outline=OL))
        im = Image.new("RGB", (256, 64), (236, 238, 240))
        from PIL import ImageDraw, ImageFont
        try:
            f = ImageFont.truetype("arialbd.ttf", 40)
        except Exception:
            f = ImageFont.load_default()
        ImageDraw.Draw(im).text((128, 32), "ICE CREAM", fill=(80, 150, 200), font=f, anchor="mm")
        s = box(P.cx, P.y0 - 0.005, P.w - 0.2, 0.012, h * 0.3, h * 0.5, P.m("sign", (236, 238, 240)))
        s["front"] = P.tex("ice", im)
        out.append(s)
        return out
    return None


# ---- Vitrinen, Glas, Stellwaende

@model("vitrine", "tischvitrine", "tresorvitrine", "glaswand", "stellwand")
def m_vitrines(P):
    k = P.kind
    gm = P.glass()
    if k == "glaswand":
        z1 = min(P.h, 2.4)
        fr = P.m("frame", (196, 202, 210))
        out = [box(P.cx, P.cy, P.w, 0.06, 0.0, 0.06, fr), box(P.cx, P.cy, P.w, 0.06, z1 - 0.05, z1, fr),
               box(P.cx, P.cy, P.w, 0.015, 0.06, z1 - 0.05, gm)]
        for x in (P.x0 + 0.03, P.x1 - 0.03):
            out.append(box(x, P.cy, 0.05, 0.06, 0.0, z1, fr, outline=OL))
        return out
    if k == "stellwand":
        z1 = min(P.h, 2.2)
        out = [box(P.cx, P.cy, P.w, 0.08, 0.0, z1, P.m("wall", (150, 40, 60)), bevel=0.01, outline=OL),
               box(P.cx, P.cy, P.w + 0.2, 0.3, 0.0, 0.05, P.m("foot", (60, 60, 66)))]
        for sy, suf in ((-1, "front"), (1, "face_n")):
            for j in range(3):
                z = 0.5 + j * 0.55
                b = box(P.cx, P.cy + sy * 0.045, P.w * 0.6, 0.01, z, z + 0.4, P.m("pic_fr", BRASS), outline=OL)
                out.append(b)
                out.append(box(P.cx, P.cy + sy * 0.052, P.w * 0.6 - 0.08, 0.008, z + 0.04, z + 0.36, P.m(f"pic{j}", [(80, 120, 160), (170, 150, 90), (90, 140, 100)][j])))
        return out
    wood = (118, 78, 48)
    if k == "tresorvitrine":
        fr = P.m("frame", (60, 66, 76))
        out = [box(P.cx, P.cy, P.w, P.d, 0.0, 0.3, fr, outline=OL),
               box(P.cx, P.cy, P.w - 0.06, P.d - 0.06, 0.3, P.h - 0.08, P.g("inner", (150, 50, 60), 0.6)),
               box(P.cx, P.cy, P.w, P.d, P.h - 0.08, P.h, fr, bevel=0.01, outline=OL)]
        for x in (P.x0 + 0.03, P.x1 - 0.03):
            for y in (P.y0 + 0.03, P.y1 - 0.03):
                out.append(box(x, y, 0.06, 0.06, 0.3, P.h, fr))
        out.append(box(P.cx, P.y0 + 0.012, P.w - 0.12, 0.012, 0.33, P.h - 0.1, gm))
        for s_, x in ((-1, P.x0 + 0.012), (1, P.x1 - 0.012)):
            out.append(box(x, P.cy, 0.012, P.d - 0.12, 0.33, P.h - 0.1, gm))
        for j in range(2):
            z = 0.35 + j * (P.h - 0.5) / 2
            out.append(box(P.cx, P.cy, P.w - 0.14, P.d - 0.14, z, z + 0.02, gm))
            out.append(lathe(P.cx - 0.3, P.cy, [(0.0, z + 0.02), (0.05, z + 0.02), (0.03, z + 0.2), (0.0, z + 0.24)], P.g(f"gem{j}", (90, 200, 160), 1.8), seg=8))
            out.append(cyl(P.cx + 0.3, P.cy, 0.09, z + 0.02, z + 0.04, P.m("plate", (190, 160, 100)), seg=14))
        return out
    hb = 0.45 if k == "vitrine" else min(0.75, P.h * 0.55)
    out = cabinet(P, P.x0, P.y0, P.x1, P.y1, 0.0, hb, wood)
    out += drawers(P, P.x0 + 0.04, P.x1 - 0.04, P.y0, 0.07, hb - 0.06, 1 if P.w < 1.4 else 2, P.m("drawer", (128, 86, 54)), P.m("knob", BRASS))
    fr = P.m("gframe", (196, 202, 210))
    z1 = P.h
    for x in (P.x0 + 0.015, P.x1 - 0.015):
        for y in (P.y0 + 0.015, P.y1 - 0.015):
            out.append(box(x, y, 0.03, 0.03, hb, z1, fr))
    out.append(box(P.cx, P.cy, P.w, P.d, z1 - 0.03, z1, fr, outline=OL))
    out.append(box(P.cx, P.y0 + 0.012, P.w - 0.04, 0.012, hb, z1 - 0.03, gm))
    out.append(box(P.cx, P.y1 - 0.012, P.w - 0.04, 0.012, hb, z1 - 0.03, gm))
    out.append(box(P.x0 + 0.012, P.cy, 0.012, P.d - 0.04, hb, z1 - 0.03, gm))
    out.append(box(P.x1 - 0.012, P.cy, 0.012, P.d - 0.04, hb, z1 - 0.03, gm))
    out.append(box(P.cx, P.cy, P.w - 0.06, P.d - 0.06, z1 - 0.045, z1 - 0.03, gm))
    out.append(box(P.cx, P.cy, P.w - 0.04, P.d - 0.04, hb, hb + 0.02, P.m("felt", (226, 220, 200))))
    if k == "vitrine":
        out.append(tooth((P.cx, P.cy, hb + 0.03), 0.22, 0.26, P.m("pyr", (200, 196, 190))))
        out.append(box(P.cx, P.cy, 0.3, 0.06, hb + 0.02, hb + 0.04, P.m("pyrbase", (90, 90, 96))))
    else:
        for j in range(4):
            out.append(lathe(P.x0 + 0.3 + (P.w - 0.6) * j / 3, P.cy, [(0.0, hb + 0.02), (0.03, hb + 0.02), (0.035, hb + 0.08), (0.0, hb + 0.12)], P.m(f"item{j}", [(200, 170, 80), (120, 160, 190), (190, 120, 90), (160, 200, 160)][j]), seg=8))
    return out


# ---- Maschinen und Geraete

@model("dampfmaschine", "turbine", "schwungrad", "kessel", "aggregat", "pumpenhaus", "projektor", "vermittlung", "monitorwand",
       "monitore", "klima", "mischpult", "lautsprecher", "herd", "spieluhr", "nachtlicht", "lampe", "stuetze", "stele", "mast",
       "tank", "lieferwagen", "boot", "arena", "tunnelwand")
def m_machines(P):
    k = P.kind
    cx, cy, w, d, h = P.cx, P.cy, P.w, P.d, P.h
    if k == "dampfmaschine":
        green, dark, steel = (72, 128, 100), (36, 60, 50), (170, 176, 184)
        out = [box(cx, cy, w, d, 0.0, 0.3, P.m("base", (90, 96, 104)), outline=OL),
               box(P.x0 + w * 0.33, cy, w * 0.6, d * 0.8, 0.3, h * 0.72, P.m("body", green), bevel=0.02, outline=OL),
               box(P.x0 + w * 0.33, P.y0 + 0.1, w * 0.6, 0.04, 0.5, h * 0.7, P.m("rib", dark)),
               cyl(P.x0 + 0.5, cy, 0.14, h * 0.72, h, P.m("chimney", (60, 64, 70)), seg=16, outline=OL),
               lathe(P.x1 - w * 0.22, cy, [(0.0, 0.55 + d * 0.3 - w * 0.2), (d * 0.3, 0.55 + d * 0.3 - w * 0.2), (d * 0.3, 0.55 + d * 0.3 + w * 0.2), (0.0, 0.55 + d * 0.3 + w * 0.2)], P.m("cyl", steel), seg=20, outline=OL, tilt=(90.0, 0.0, 0.55 + d * 0.3)),
               tube([(P.x1 - w * 0.05, cy, 0.55 + d * 0.3), (P.x1 + 0.4, cy, 0.55 + d * 0.3)], 0.03, P.m("rod", steel), seg=8)]
        im = Image.new("RGB", (160, 48), green)
        from PIL import ImageDraw, ImageFont
        try:
            f = ImageFont.truetype("arialbd.ttf", 30)
        except Exception:
            f = ImageFont.load_default()
        ImageDraw.Draw(im).text((80, 24), "1887", fill=BRASS, font=f, anchor="mm")
        s = box(P.x0 + w * 0.33, P.y0 + 0.09, 0.5, 0.012, 0.4, 0.55, P.m("plate", green))
        s["front"] = P.tex("1887", im)
        out.append(s)
        out.append(box(P.x0 + w * 0.33, P.y0 + 0.08, 0.04, 0.02, 0.3, h * 0.7, P.m("band", BRASS)))
        return out
    if k == "turbine":
        steel = P.m("drum", (176, 182, 190))
        out = [box(cx, cy, w, d, 0.0, 0.25, P.m("base", (96, 102, 110)), outline=OL)]
        L = w * 0.68
        r = min(d * 0.42, h * 0.38)
        zc = 0.25 + r
        out.append(lathe(P.x0 + L / 2 + 0.05, cy, [(0.0, zc - L / 2), (r, zc - L / 2), (r, zc + L / 2), (0.0, zc + L / 2)], steel, seg=28, outline=OL, tilt=(90.0, 0.0, zc)))
        for j in range(6):
            x = P.x0 + 0.1 + L * (j + 0.5) / 6
            out.append(lathe(x, cy, [(r * 0.98, zc - 0.03), (r * 1.04, zc - 0.03), (r * 1.04, zc + 0.03), (r * 0.98, zc + 0.03)], P.m("band", (120, 126, 134)), seg=28, tilt=(90.0, 0.0, zc)))
        out.append(lathe(P.x0 + 0.08, cy, [(0.0, zc - 0.03), (r * 1.1, zc - 0.03), (r * 1.1, zc + 0.03), (0.0, zc + 0.03)], P.m("endcap", (150, 156, 164)), seg=28, outline=OL, tilt=(90.0, 0.0, zc)))
        for j in range(8):
            a = math.radians(j * 45)
            out.append(tube([(P.x0 + 0.06, cy, zc), (P.x0 + 0.06, cy + r * math.cos(a), zc + r * math.sin(a))], 0.02, P.m("spoke", (90, 94, 100)), seg=6))
        out.append(box(P.x1 - w * 0.14, cy, w * 0.24, d * 0.6, 0.25, h, P.m("cab", (72, 128, 100)), bevel=0.02, outline=OL))
        out.append(box(P.x1 - w * 0.14, P.y0 + d * 0.19, 0.2, 0.012, h * 0.35, h * 0.5, P.g("btn", (240, 200, 60), 1.4)))
        return out
    if k == "schwungrad":
        r = min(w, h) * 0.45
        steel = P.m("ped", (120, 126, 134))
        out = [box(cx, cy, 0.5, 0.5, 0.0, 0.08, steel, outline=OL), box(cx, cy, 0.36, 0.3, 0.08, h * 0.45, steel, outline=OL)]
        zc = h * 0.45 + r * 0.9
        green = P.m("wheel", (70, 160, 120))
        out.append(lathe(cx, cy, [(r * 0.9, zc - 0.04), (r, zc - 0.04), (r, zc + 0.04), (r * 0.9, zc + 0.04)], green, seg=32, outline=OL, tilt=(90.0, 90.0, zc)))
        for j in range(6):
            a = math.radians(j * 60)
            out.append(tube([(cx, cy, zc), (cx + r * 0.92 * math.cos(a), cy, zc + r * 0.92 * math.sin(a))], 0.022, green, seg=6))
        out.append(lathe(cx, cy, [(0.0, zc - 0.06), (0.1, zc - 0.06), (0.1, zc + 0.06), (0.0, zc + 0.06)], P.m("hub", BRASS), seg=16, tilt=(90.0, 90.0, zc)))
        out.append(tube([(cx - 0.05, cy, zc), (cx - 0.05 - r * 1.3, cy, zc - r * 0.4)], 0.025, steel, seg=8))
        return out
    if k == "kessel":
        r = min(w, d) * 0.46
        out = [box(cx, cy, w, d, 0.0, 0.15, P.m("base", (96, 102, 110)), outline=OL),
               lathe(cx, cy, [(0.0, 0.15), (r * 0.7, 0.15), (r, 0.5), (r, h - r), (r * 0.7, h - 0.1), (0.0, h)], P.m("tank", (176, 182, 190)), seg=28, outline=OL),
               lathe(cx, cy, [(r * 0.98, h * 0.5), (r * 1.05, h * 0.5), (r * 1.05, h * 0.55), (r * 0.98, h * 0.55)], P.m("band", BRASS), seg=28),
               disc_s(P, cx, cy - r - 0.015, h * 0.58, 0.08, 0.02, P.m("gauge", (236, 236, 230)), seg=14, outline=OL),
               tube([(P.x1 - 0.1, cy, h * 0.45), (P.x1 + 0.2, cy, h * 0.45), (P.x1 + 0.2, cy, 0.1)], 0.04, P.m("pipe", (120, 126, 134)), seg=8),
               lathe(cx, cy, [(0.0, h), (0.06, h), (0.06, h + 0.1), (0.0, h + 0.1)], P.m("valve", (200, 60, 60)), seg=10)]
        return out
    if k == "aggregat":
        y_, dk = (214, 170, 40), (60, 60, 64)
        out = [box(cx, cy, w, d, 0.0, 0.12, P.m("frame", dk), outline=OL),
               box(cx, cy, w, d, 0.12, h, P.m("body", y_), bevel=0.02, outline=OL),
               box(cx, P.y0 - 0.01, w - 0.2, 0.02, 0.2, h * 0.4, P.m("grille", (40, 40, 44)), outline=OL),
               cyl(P.x0 + 0.3, cy, 0.05, h, h + 0.35, P.m("exh", (60, 60, 64)), seg=10),
               disc_s(P, cx + 0.2, P.y0 - 0.002, h * 0.56, 0.04, 0.015, P.m("btn", (200, 50, 50)), seg=10)]
        for j, c in enumerate(((80, 230, 90), (240, 200, 70), (230, 70, 60))):
            out.append(disc_s(P, P.x1 - 0.3 + j * 0.08, P.y0 - 0.002, h * 0.31, 0.012, 0.008, P.g(f"led{j}", c, 2.0), seg=6))
        out.append(box(cx, P.y0 - 0.004, w - 0.2, 0.008, 0.13, 0.17, P.m("stripe", (40, 40, 44))))
        for j in range(2):
            out.append(blob(P.x0 + 0.3 + j * 0.1, cy, h + 0.45 + j * 0.2, 0.08, 0.08, 0.1, (P.m("smoke", (200, 200, 210)), P.m("smoke", (200, 200, 210))), seed=j, seg=8, rings=4))
        return out
    if k == "pumpenhaus":
        green = (72, 128, 100)
        out = [box(cx, cy, w, d, 0.0, h * 0.4, P.m("base", _sh(green, 0.8)), outline=OL),
               box(cx, cy, w, d, h * 0.4, h, P.m("body", green), outline=OL),
               box(cx + w * 0.2, P.y0 - 0.012, 0.5, 0.024, 0.1, h * 0.35, P.m("door", (60, 64, 70)), outline=OL),
               disc_s(P, P.x0 + 0.5, P.y0 - 0.002, h * 0.6, 0.12, 0.02, P.m("gauge", (236, 236, 230)), seg=16, outline=OL),
               box(P.x1 - 0.3, P.y0 - 0.008, 0.2, 0.012, h * 0.25, h * 0.37, P.g("warn", (240, 200, 60), 1.3)),
               tube([(P.x1 - 0.05, cy, h * 0.5), (P.x1 + 0.3, cy, h * 0.5), (P.x1 + 0.3, cy, 0.0)], 0.06, P.m("pipe", (120, 126, 134)), seg=10),
               cyl(P.x1 - 0.3, P.y1 - 0.3, 0.1, h, h + 0.2, P.m("vent", (60, 64, 70)), seg=12)]
        return out
    if k == "projektor":
        steel = P.m("steel", (120, 126, 134))
        out = [cyl(cx, cy, w * 0.4, 0.0, 0.1, P.m("base", (60, 64, 72)), seg=24, outline=OL),
               cyl(cx, cy, w * 0.3, 0.1, 0.3, steel, seg=24, outline=OL),
               cyl(cx, cy, 0.1, 0.3, h * 0.55, steel, seg=16),
               cyl(cx, cy, w * 0.2, h * 0.5, h * 0.6, P.g("ring", (120, 200, 240), 1.6), seg=24)]
        for sx in (-1, 1):
            out.append(tube([(cx, cy, h * 0.55), (cx + sx * w * 0.32, cy, h * 0.85)], 0.035, steel, seg=8))
            out.append(lathe(cx + sx * w * 0.32, cy, [(0.0, h * 0.85 - 0.22), (0.18, h * 0.85 - 0.12), (0.22, h * 0.85), (0.18, h * 0.85 + 0.12), (0.0, h * 0.85 + 0.22)], P.m("ball", (190, 196, 204)), seg=16, outline=OL))
        out.append(lathe(cx, cy, [(0.0, h * 0.55), (0.12, h * 0.6), (0.14, h * 0.7), (0.0, h * 0.75)], P.m("ball", (190, 196, 204)), seg=14))
        return out
    if k == "vermittlung":
        hc = min(h * 0.4, 1.0)
        out = counter(P, P.x0, P.y0, P.x1, P.y1, hc, (118, 80, 50), (150, 105, 62))
        out.append(box(cx, P.y1 - 0.06, w, 0.1, hc, h, P.m("board", (60, 44, 34)), outline=OL))
        for r in range(3):
            for c in range(int(w / 0.12)):
                out.append(cyl(P.x0 + 0.1 + c * 0.12, P.y1 - 0.115, 0.014, hc + 0.15 + r * 0.2, hc + 0.17 + r * 0.2, P.m("jack", (200, 196, 180)), seg=6))
        for j in range(6):
            x = P.x0 + 0.3 + (w - 0.6) * j / 5
            out.append(tube([(x, P.y0 + 0.2, hc + 0.02), (x + 0.1, P.y1 - 0.12, hc + 0.3 + (j % 3) * 0.2)], 0.008, P.m(f"cord{j % 2}", [(200, 60, 60), (60, 60, 200)][j % 2]), seg=5))
        return out
    if k == "monitorwand":
        # Museum: schmale Saeule mit Bildschirmen uebereinander an der Wand
        n = max(3, int(h / 0.45))
        out = [box(cx, P.base + 0.13, w, 0.2, 0.0, h, P.m("tower", (50, 54, 62)), bevel=0.01, outline=OL)]
        for j in range(n):
            z = 0.1 + (h - 0.2) * j / n
            out.append(M.screen_panel(P.ctx, f"{P.nm}_s{j}", cx, P.base + 0.02, z + 0.03, z + (h - 0.2) / n - 0.05, w - 0.15, "S", None, (110, 180, 220), glow=1.3))
        return out
    if k == "monitore":
        n = max(3, int(h / 0.5))
        out = [box(cx, P.base + 0.15, w, 0.24, 0.0, h, P.m("tower", (50, 54, 62)), bevel=0.01, outline=OL)]
        for j in range(n):
            z = 0.25 + (h - 0.4) * j / n
            out.append(M.screen_panel(P.ctx, f"{P.nm}_s{j}", cx, P.base + 0.02, z, z + (h - 0.4) / n - 0.08, w - 0.2, "S", None, (90, 170, 110), glow=1.3))
        return out
    if k == "klima":
        out = [box(cx, cy, w, min(d, 0.6), 0.0, h * 0.45, P.m("grille", (190, 196, 204)), outline=OL),
               box(cx, cy, w, min(d, 0.6), h * 0.45, h, P.m("body", (226, 230, 234)), bevel=0.01, outline=OL),
               disc_s(P, cx, P.y0 + 0.012, h * 0.7, w * 0.3, 0.02, P.m("fan", (90, 94, 100)), seg=24, outline=OL)]
        for j in range(5):
            out.append(box(cx, P.y0 + 0.005, w - 0.1, 0.01, h * 0.05 + j * h * 0.08, h * 0.05 + j * h * 0.08 + 0.02, P.m("slat", (150, 156, 164))))
        return out
    if k == "mischpult":
        if P.w > 2.0:
            hc = min(h * 0.45, 0.95)
            out = counter(P, P.x0, P.y0, P.x1, P.y1, hc, (70, 40, 90), (40, 40, 48))
            out.append(obox((cx, cy, hc + 0.1), (w - 0.1, d - 0.1, 0.1), P.m("deck", (36, 36, 44)), roll=-12.0, outline=OL))
            for j in range(16):
                c = [(80, 220, 240), (240, 90, 200), (240, 200, 70)][j % 3]
                out.append(cyl(P.x0 + 0.15 + (w - 0.3) * j / 15, cy + P.rnd.uniform(-0.3, 0.3), 0.015, hc + 0.16, hc + 0.19, P.g(f"led{j % 3}", c, 2.2), seg=6))
            return out
        out = [box(cx, cy, w, min(d, 0.5), 0.0, h * 0.5, P.m("stand", (50, 52, 58)), outline=OL),
               obox((cx, cy, h * 0.5 + 0.06), (w, min(d, 0.5), 0.12), P.m("deck", (70, 74, 82)), roll=-20.0, outline=OL)]
        for j in range(6):
            out.append(obox((cx, cy - 0.15 + j * 0.06, h * 0.5 + 0.13 + j * 0.02), (w - 0.1, 0.006, 0.01), P.m("slot", (30, 30, 34)), roll=-20.0))
            out.append(obox((cx + P.rnd.uniform(-0.1, 0.1), cy - 0.15 + j * 0.06, h * 0.5 + 0.15 + j * 0.02), (0.03, 0.02, 0.02), P.m("fader", (220, 220, 224))))
        return out
    if k == "lautsprecher":
        yf = cy - min(d, 0.7) / 2
        out = [box(cx, cy, w, min(d, 0.7), 0.0, h, P.m("box", (46, 42, 58)), bevel=0.015, outline=OL)]
        for z, r in ((h * 0.28, w * 0.3), (h * 0.65, w * 0.18)):
            out.append(disc_s(P, cx, yf - 0.002, z, r * 1.05, 0.03, P.m("rim", (90, 94, 110)), seg=20, outline=OL))
            out.append(disc_s(P, cx, yf - 0.03, z, r * 0.9, 0.01, P.m("cone", (30, 30, 36)), seg=20))
            out.append(disc_s(P, cx, yf - 0.035, z, r * 0.3, 0.02, P.m("dome", (60, 60, 70)), seg=12))
        out.append(disc_s(P, cx, yf - 0.002, h * 0.85, 0.03, 0.01, P.g("led", (120, 220, 240), 2.0), seg=8))
        return out
    if k == "herd":
        out = [box(cx, cy, w, d, 0.0, 0.2, P.m("legs", (50, 52, 58)), outline=OL),
               box(cx, cy, w, d, 0.2, 0.85, P.m("body", (60, 62, 70)), bevel=0.012, outline=OL),
               box(cx, P.y0 - 0.008, w * 0.4, 0.016, 0.35, 0.6, P.g("fire", (255, 140, 50), 2.0)),
               box(cx, P.y0 - 0.02, w - 0.1, 0.03, 0.6, 0.65, P.m("rail", (120, 126, 134))),
               cyl(P.x0 + 0.3, cy + 0.2, 0.1, 0.85, h, P.m("chimney", (70, 72, 80)), seg=14, outline=OL),
               cyl(P.x0 + 0.45, cy - 0.1, 0.16, 0.85, 0.89, P.m("pan", (40, 40, 44)), seg=16),
               tube([(P.x0 + 0.6, cy - 0.1, 0.88), (P.x0 + 0.85, cy - 0.15, 0.9)], 0.015, P.m("handle", (40, 40, 44)), seg=6),
               cyl(P.x1 - 0.5, cy, 0.14, 0.85, 0.95, P.m("pot", (120, 80, 50)), seg=16, outline=OL)]
        return out
    if k == "spieluhr":
        out = [cyl(cx, cy, 0.3, 0.0, 0.06, P.m("foot", BRASS), seg=20, outline=OL),
               cyl(cx, cy, 0.05, 0.06, h * 0.45, P.m("stem", (201, 162, 76)), seg=12),
               box(cx, cy, 0.5, 0.42, h * 0.45, h * 0.75, P.m("box", (118, 80, 50)), bevel=0.012, outline=OL),
               obox((cx, cy + 0.2, h * 0.75 + 0.18), (0.5, 0.02, 0.4), P.m("lid", (128, 86, 54)), roll=-75.0, outline=OL),
               box(cx, cy, 0.42, 0.34, h * 0.75, h * 0.76, P.m("velvet", (150, 40, 60))),
               tube([(P.x1 - 0.1, cy, h * 0.6), (P.x1 + 0.1, cy, h * 0.6), (P.x1 + 0.1, cy, h * 0.5)], 0.012, P.m("crank", BRASS), seg=6)]
        return out
    if k == "nachtlicht":
        out = tripod(P, cx, cy, 0.9, spread=0.3, r=0.012, mat=P.m("tripod", (50, 50, 56)))
        out.append(lathe(cx, cy, [(0.0, 0.85), (0.2, 0.92), (0.26, 1.15), (0.2, 1.38), (0.0, 1.45)], P.g("globe", (255, 220, 140), 2.6), seg=16))
        return out
    if k == "lampe":
        st = P.m("post", (50, 52, 58))
        x = cx
        y = P.base + 0.15
        out = [cyl(x, y, 0.1, 0.0, 0.06, st, seg=12, outline=OL), cyl(x, y, 0.03, 0.06, h - 0.3, st, seg=10)]
        out.append(lathe(x, y, [(0.0, h - 0.3), (0.06, h - 0.3), (0.14, h - 0.05), (0.0, h)], P.g("lamp", (255, 230, 170), 2.4), seg=12))
        return out
    if k == "stuetze":
        return [box(cx, cy, w, min(d, w), 0.0, 0.08, P.m("foot", (118, 80, 50)), outline=OL),
                box(cx, cy, w * 0.8, min(d, w) * 0.8, 0.08, h, P.m("col", (176, 182, 190)), bevel=0.02, outline=OL),
                box(cx, cy, w * 0.9, min(d, w) * 0.9, h - 0.08, h, P.m("cap", (150, 156, 164)), outline=OL)]
    if k == "stele":
        stone = P.m("stone", (150, 140, 126))
        out = [box(cx, cy, w, min(d, 0.6), 0.0, h * 0.7, stone, bevel=0.015, outline=OL),
               box(cx, cy, w * 0.55, min(d, 0.6) * 0.5, h * 0.7, h, stone, bevel=0.01, outline=OL)]
        b = box(cx, P.y0 - 0.006, w * 0.5, 0.012, h * 0.3, h * 0.65, P.m("plaque", (226, 196, 130)), outline=OL)
        out.append(b)
        for j in range(6):
            out.append(box(cx, P.y0 - 0.012, w * 0.35, 0.004, h * 0.35 + j * 0.05, h * 0.35 + j * 0.05 + 0.012, P.m("text", (120, 90, 50))))
        return out
    if k == "mast":
        st = P.m("steel", (200, 204, 210))
        x, y = (P.vx0 + P.vx1) / 2, P.base + 0.3
        out = [cyl(x, y, 0.35, 0.0, 0.12, P.m("base", (90, 94, 100)), seg=16, outline=OL)]
        for i in range(3):
            a = math.radians(90 + 120 * i)
            out.append(tube([(x + 0.3 * math.cos(a), y + 0.3 * math.sin(a), 0.12), (x, y, h - 0.1)], 0.018, st, seg=6))
            a2 = math.radians(90 + 120 * (i + 1))
            for t in (0.3, 0.6):
                out.append(tube([(x + 0.3 * (1 - t) * math.cos(a), y + 0.3 * (1 - t) * math.sin(a), 0.12 + (h - 0.22) * t), (x + 0.3 * (1 - t) * math.cos(a2), y + 0.3 * (1 - t) * math.sin(a2), 0.12 + (h - 0.22) * t)], 0.01, st, seg=5))
        out.append(lathe(x, y, [(0.0, h - 0.12), (0.05, h - 0.06), (0.0, h)], P.g("beacon", (255, 60, 50), 3.0), seg=8))
        out.append(box(x - 0.3, y - 0.1, 0.2, 0.12, 0.12, 0.3, P.m("box", (200, 170, 60)), outline=OL))
        return out
    if k == "tank":
        r = min(w, d) * 0.42
        zc = h * 0.55
        out = []
        for a in range(4):
            aa = math.radians(45 + 90 * a)
            out.append(cyl(cx + r * 0.7 * math.cos(aa), cy + r * 0.7 * math.sin(aa), 0.05, 0.0, zc - r * 0.5, P.m("leg", (70, 72, 80)), seg=8))
        out.append(lathe(cx, cy, [(0.0, zc - r), (r * 0.6, zc - r * 0.8), (r * 0.95, zc - r * 0.3), (r, zc), (r * 0.95, zc + r * 0.3), (r * 0.6, zc + r * 0.8), (0.0, zc + r)], P.m("tank", (120, 160, 200)), seg=24, outline=OL))
        im = Image.new("RGB", (160, 64), (120, 160, 200))
        from PIL import ImageDraw, ImageFont
        try:
            f = ImageFont.truetype("arialbd.ttf", 40)
        except Exception:
            f = ImageFont.load_default()
        ImageDraw.Draw(im).text((80, 32), "H2O", fill=(236, 240, 244), font=f, anchor="mm")
        s = box(cx, cy - r + 0.006, 0.7, 0.012, zc - 0.15, zc + 0.15, P.m("label", (120, 160, 200)))
        s["front"] = P.tex("h2o", im)
        out.append(s)
        out.append(lathe(cx, cy, [(0.0, zc + r), (0.25, zc + r), (0.0, zc + r + 0.3)], P.m("cap", (90, 110, 140)), seg=16))
        out.append(tube([(cx - r * 0.3, cy - r * 0.5, zc - r * 0.5), (cx - r * 0.3, cy - r * 0.5, 0.0)], 0.03, P.m("pipe", (90, 94, 100)), seg=8))
        return out
    if k == "lieferwagen":
        white, dk = P.m("van", (236, 238, 240)), P.m("van_d", (60, 62, 68))
        hb = min(h, 2.6)
        out = [box(cx, cy, w, d, 0.5, hb, white, bevel=0.03, outline=OL),
               box(cx, cy, w - 0.1, d - 0.1, 0.35, 0.5, dk, outline=OL),
               box(cx, P.y1 - 0.4, w, 0.8, 0.5, hb * 0.65, white, bevel=0.03, outline=OL),
               box(cx, P.y0 + 0.012, w * 0.9, 0.024, 0.55, hb - 0.15, P.m("door", (226, 228, 232)), outline=OL),
               box(cx, P.y0 + 0.0, 0.02, 0.03, 0.55, hb - 0.15, dk),
               box(cx, P.y0 - 0.005, w * 0.3, 0.012, hb * 0.5, hb * 0.6, P.m("win", (120, 140, 170)))]
        for sx in (-1, 1):
            for yy in (P.y0 + 0.5, P.y1 - 0.5):
                out.append(wheel(P, cx + sx * (w / 2 - 0.16), yy, 0.35, 0.35, 0.22, dk, axis="x"))
            out.append(box(cx + sx * w * 0.35, P.y0 - 0.01, 0.2, 0.02, 0.6, 0.7, P.g(f"tail{sx}", (230, 60, 60), 2.0)))
        out.append(box(cx, P.y0 - 0.01, w * 0.6, 0.02, 0.4, 0.5, P.m("bumper", (90, 94, 100))))
        return out
    if k == "boot":
        hull = P.m("hull", (150, 50, 40))
        ell = affinity.scale(sbox(P.x0, P.y0, P.x1, P.y1).centroid.buffer(1.0, 40), w / 2, d / 2)
        out = [prism(ell, 0.0, 0.35, hull, bevel=0.03, outline=OL),
               prism(affinity.scale(ell, 1.02, 1.02), 0.35, 0.4, P.m("gunwale", (118, 80, 50)), outline=OL),
               prism(affinity.scale(ell, 0.85, 0.75), 0.33, 0.35, P.m("inner", (120, 60, 46)))]
        for sx in (-0.28, 0.0, 0.28):
            out.append(box(cx + sx * w, cy, 0.14, d * 0.6, 0.2, 0.36, P.m("seat", (150, 105, 62)), outline=OL))
        out.append(tube([(P.x0 + 0.2, P.y1 - 0.2, 0.4), (P.x1 - 0.4, P.y1 + 0.1, 0.45)], 0.02, P.m("paddle", (150, 105, 62)), seg=6))
        out.append(obox((P.x1 - 0.3, P.y1 + 0.12, 0.45), (0.3, 0.14, 0.02), P.m("paddle", (150, 105, 62)), yaw=10.0))
        return out
    if k == "arena":
        steel = P.m("rail", (210, 170, 60))
        hb = 0.25
        out = [box(cx, cy, w, d, 0.0, hb, P.m("floor", (60, 66, 76)), outline=OL),
               box(cx, cy, w, 0.08, hb, hb + 0.12, steel, outline=OL), box(cx, P.y1 - 0.04, w, 0.08, hb, hb + 0.12, steel, outline=OL)]
        for x in (P.x0 + 0.05, P.x1 - 0.05):
            out.append(cyl(x, cy, 0.04, 0.0, h, P.m("post", (40, 42, 50)), seg=8))
        out.append(box(cx, cy, w, 0.03, h - 0.03, h, steel))
        cars = [((230, 70, 80), -0.25, -0.3), ((240, 200, 70), 0.05, 0.25), ((80, 200, 190), 0.3, -0.05)]
        for j, (c, fx, fy) in enumerate(cars):
            x, y = cx + fx * w, cy + fy * d
            out.append(box(x, y, 0.55, 0.42, hb, hb + 0.18, P.m(f"car{j}_b", (40, 40, 48)), bevel=0.03, outline=OL))
            out.append(box(x, y, 0.5, 0.38, hb + 0.18, hb + 0.38, P.m(f"car{j}", c), bevel=0.03, outline=OL))
            out.append(tube([(x, y - 0.1, hb + 0.38), (x, y + 0.1, h - 0.03)], 0.012, P.m("pole", (90, 94, 100)), seg=6))
            out.append(lathe(x, y + 0.1, [(0.0, h - 0.1), (0.03, h - 0.08), (0.0, h - 0.03)], P.g("spark", (150, 220, 255), 2.6), seg=8))
        return out
    if k == "tunnelwand":
        out = [box(cx, cy, w, min(d, 0.5), 0.0, h, P.m("wall", (90, 60, 110)), bevel=0.01, outline=OL)]
        for j in range(int(w / 0.4)):
            out.append(box(P.x0 + 0.2 + j * 0.4, P.y0 + 0.004, 0.01, 0.01, 0.1, h - 0.1, P.m("seam", (60, 40, 80))))
        for sx in (-1, 1):
            out.append(cyl(cx + 0.3 + sx * 0.07, P.y0 - 0.006, 0.02, h * 0.45, h * 0.47, P.g("eye", (120, 255, 120), 2.8), seg=8))
        out.append(box(cx - 0.4, P.y0 - 0.004, 0.3, 0.008, h * 0.5, h * 0.62, P.m("bat", (30, 24, 40))))
        return out
    return None


# ---- Kisten, Stapel

@model("kiste", "kisten", "holzstapel", "baumstamm", "sarkophag", "bett")
def m_containers(P):
    k = P.kind
    cx, cy, w, d, h = P.cx, P.cy, P.w, P.d, P.h
    if k == "kiste":
        out = M.crate_stack(P.ctx, P.nm, cx, cy, min(w, d) * 0.95, min(h, 1.2), n=1, rgb=(205, 150, 95), dark=(150, 100, 60), seed=P.seed)
        im = Image.new("RGB", (200, 60), (205, 150, 95))
        from PIL import ImageDraw, ImageFont
        try:
            f = ImageFont.truetype("arialbd.ttf", 34)
        except Exception:
            f = ImageFont.load_default()
        ImageDraw.Draw(im).text((100, 30), "FRAGILE", fill=(120, 70, 40), font=f, anchor="mm")
        s = box(cx, cy - min(w, d) * 0.475 - 0.004, min(w, d) * 0.6, 0.008, min(h, 1.2) * 0.45, min(h, 1.2) * 0.65, P.m("label", (205, 150, 95)))
        s["front"] = P.tex("fragile", im)
        out.append(s)
        return out
    if k == "kisten":
        # Wald: drei Holzkisten nebeneinander
        out = []
        n = max(2, int(w / 1.1))
        for j in range(n):
            out += M.crate_stack(P.ctx, f"{P.nm}_{j}", P.x0 + w * (j + 0.5) / n, cy, min(w / n, d) * 0.9, min(h, 1.0), n=1, rgb=(190, 140, 90), dark=(130, 90, 55), seed=P.seed + j)
        return out
    if k == "holzstapel":
        wood = P.m("logend", (210, 170, 110))
        out = [box(P.x0 + 0.05, cy, 0.1, d, 0.0, h, P.m("post", (120, 80, 50)), outline=OL), box(P.x1 - 0.05, cy, 0.1, d, 0.0, h, P.m("post", (120, 80, 50)), outline=OL),
               box(cx, P.y1 - 0.05, w, 0.1, 0.0, h, P.m("back", (150, 105, 62)), outline=OL)]
        r = 0.09
        rows = int(min(h, 1.2) / (2 * r))
        cols = int((w - 0.2) / (2 * r))
        for ro in range(rows):
            for c in range(cols):
                x = P.x0 + 0.1 + r + c * 2 * r + (r if ro % 2 else 0)
                if x + r > P.x1 - 0.1:
                    continue
                zl = r + ro * 2 * r * 0.95
                out.append(lathe(x, cy, [(0.0, zl - d / 2 + 0.05), (r * 0.95, zl - d / 2 + 0.05), (r * 0.95, zl + d / 2 - 0.05), (0.0, zl + d / 2 - 0.05)], wood, seg=10, outline=OL, tilt=(90.0, 90.0, zl)))
        return out
    if k == "baumstamm":
        r = min(d * 0.45, 0.3)
        out = [lathe(cx, cy, [(0.0, r - w / 2), (r, r - w / 2), (r, r + w / 2), (0.0, r + w / 2)], P.m("bark", (150, 105, 62)), seg=14, outline=OL, tilt=(90.0, 0.0, r)),
               lathe(P.x0 + 0.01, cy, [(0.0, r - 0.02), (r * 0.98, r - 0.02), (r * 0.98, r + 0.02), (0.0, r + 0.02)], P.m("logend", (210, 170, 110)), seg=14, tilt=(90.0, 0.0, r))]
        out.append(cyl(cx + 0.3, cy, 0.04, 2 * r, 2 * r + 0.12, P.m("stub", (120, 80, 50)), seg=8))
        return out
    if k == "sarkophag":
        gold = P.m("gold", (214, 170, 60))
        out = [box(cx, cy, w, d, 0.0, 0.25, P.m("plinth", (120, 126, 134)), bevel=0.01, outline=OL),
               prism(sarcophagus_poly(cx, cy, d * 0.9, w * 0.8, 0.0), 0.25, 0.65, gold, bevel=0.02, outline=OL),
               prism(sarcophagus_poly(cx, cy, d * 0.9, w * 0.8, 0.0).buffer(-0.02), 0.65, 0.78, P.m("lid", (226, 186, 70)), bevel=0.03, outline=OL),
               lathe(cx, cy + d * 0.25, [(0.0, 0.78), (0.12, 0.8), (0.1, 0.95), (0.0, 0.98)], P.m("face", (226, 196, 150)), seg=12, outline=OL)]
        for j, c in enumerate(((40, 60, 160), (190, 50, 50), (40, 60, 160))):
            out.append(box(cx, cy - d * 0.1 - j * 0.14, w * 0.6, 0.06, 0.78, 0.79, P.m(f"stripe{j}", c)))
        return out
    if k == "bett":
        return M.bed(P.ctx, P.nm, P.x0, P.y0, P.x1, P.y1, head="N", frame_rgb=(150, 105, 62), mattress_rgb=(70, 100, 90), h_frame=0.3, h_mattress=0.14)
    return None


# ---- Figuren, Stuecke mit Stand

@model("baum", "fels", "lagerfeuer", "turm", "hochsitz", "hochsitz_front", "hochsitz_roof", "dino")
def m_figures(P):
    k = P.kind
    cx, cy, w, d, h = P.cx, P.cy, P.w, P.d, P.h
    if k == "baum":
        return M.tree(P.ctx, P.nm, cx, P.base + 0.4, h=h, trunk_r=0.14, crown_r=w * 0.45, trunk_rgb=(100, 70, 46), leaf_rgb=(50, 120, 60), seed=P.seed)
    if k == "fels":
        mats = (P.m("rock", (150, 154, 160)), P.m("rock_d", (110, 114, 120)), P.m("moss", (110, 150, 70)))
        return [boulder(cx, cy, w * 0.45, d * 0.42, h, mats, seed=P.seed, seg=16, rings=8, cap=0.85, outline=OL)]
    if k == "lagerfeuer":
        out = M.campfire(P.ctx, P.nm, cx, cy, r=min(w, d) * 0.4, stone_rgb=(150, 150, 150), seed=P.seed)
        for i in range(3):
            a = math.radians(90 + 120 * i)
            out.append(tube([(cx + 0.5 * math.cos(a), cy + 0.5 * math.sin(a), 0.0), (cx, cy, 1.3)], 0.02, P.m("stick", (110, 80, 50)), seg=6))
        out.append(lathe(cx, cy, [(0.0, 0.85), (0.12, 0.85), (0.14, 1.0), (0.0, 1.0)], P.m("pot", (50, 50, 56)), seg=12, outline=OL))
        out.append(tube([(cx, cy, 1.0), (cx, cy, 1.28)], 0.006, P.m("chain", (90, 90, 96)), seg=4))
        return out
    if k == "turm":
        wood = P.m("wood", (150, 105, 62))
        hf = h * 0.55
        out = []
        for x in (P.x0 + 0.15, P.x1 - 0.15):
            for y in (P.y0 + 0.15, P.y1 - 0.15):
                out.append(box(x, y, 0.14, 0.14, 0.0, hf, wood, outline=OL))
        out.append(box(P.x0 + 0.15, cy, 0.06, d - 0.3, hf * 0.45, hf * 0.5, wood))
        out.append(box(P.x1 - 0.15, cy, 0.06, d - 0.3, hf * 0.45, hf * 0.5, wood))
        out += ladder(P, cx, P.y0 + 0.1, P.y0 + 0.1, 0.0, hf, wood, w=0.5, lean=0.0)
        out.append(box(cx, cy, w, d, hf, hf + 0.1, wood, outline=OL))
        out.append(box(cx, cy, w - 0.1, d - 0.1, hf + 0.1, hf + 0.15, P.m("floor", (170, 125, 80))))
        for x in (P.x0 + 0.1, P.x1 - 0.1):
            for y in (P.y0 + 0.1, P.y1 - 0.1):
                out.append(box(x, y, 0.1, 0.1, hf + 0.1, h * 0.8, wood))
        out.append(roof_hip(P, P.x0, P.y0, P.x1, P.y1, h * 0.8, h, P.m("roof", (160, 60, 50)), over=0.25))
        return out
    if k in ("hochsitz", "hochsitz_front", "hochsitz_roof"):
        wood = P.m("wood", (150, 105, 62))
        if k == "hochsitz_roof":
            return [roof_gable(P, P.x0, P.y0, P.x1, P.y1, h - 0.6, h, P.m("roof", (120, 80, 50)), over=0.1, along="y")]
        if k == "hochsitz_front":
            out = []
            for x in (P.x0 + 0.06, P.x1 - 0.06):
                out.append(box(x, P.y0 + 0.06, 0.12, 0.12, 0.0, h, wood, outline=OL))
            out.append(box(cx, P.y0 + 0.06, w, 0.06, 0.0, 0.12, wood))
            out.append(cyl(P.x1 - 0.15, P.y0 - 0.02, 0.06, 0.4, 0.55, P.g("lantern", (255, 200, 110), 2.4), seg=8))
            return out
        hf = h * 0.45
        out = []
        for x in (P.x0 + 0.15, P.x1 - 0.15):
            for y in (P.y0 + 0.15, P.y1 - 0.15):
                out.append(box(x, y, 0.14, 0.14, 0.0, hf, wood, outline=OL))
        out.append(box(P.x0 + 0.15, cy, 0.06, d - 0.3, hf * 0.5, hf * 0.55, wood))
        out.append(box(P.x1 - 0.15, cy, 0.06, d - 0.3, hf * 0.5, hf * 0.55, wood))
        out += ladder(P, cx, P.y0 + 0.08, P.y0 + 0.08, 0.0, hf, wood, w=0.5)
        out.append(box(cx, cy, w, d, hf, hf + 0.12, wood, outline=OL))
        out.append(box(cx, P.y1 - 0.04, w, 0.08, hf + 0.12, h, wood, outline=OL))
        for x in (P.x0 + 0.04, P.x1 - 0.04):
            out.append(box(x, cy, 0.08, d, hf + 0.12, h, wood, outline=OL))
            out.append(box(x, cy - d * 0.1, 0.09, 0.3, hf + 0.6, hf + 0.9, P.m("window", (40, 50, 60))))
        out.append(box(cx, P.y1 - 0.04, 0.5, 0.09, hf + 0.6, hf + 0.9, P.m("window", (40, 50, 60))))
        return out
    return None


# ---- Wandschmuck und Bodenstuecke

@model("staffelei")
def m_walls(P):
    k = P.kind
    if k == "staffelei":
        wood = P.m("wood", (150, 105, 62))
        out = tripod(P, P.cx, P.cy, 1.5, spread=0.35, r=0.016, mat=wood)
        out.append(tube([(P.cx - 0.35, P.cy - 0.25, 0.55), (P.cx + 0.35, P.cy - 0.25, 0.55)], 0.016, wood, seg=6))
        z0p, z1p = 0.6, 1.35
        fr = box(P.cx, P.cy - 0.22, 0.7, 0.04, z0p, z1p, P.m("frame", BRASS), bevel=0.008, outline=OL)
        out.append(fr)
        im = P.img(P.vx0 + 0.1, P.base + 0.35, P.vx1 - 0.1, P.vytop - 0.25)
        c = box(P.cx, P.cy - 0.245, 0.6, 0.012, z0p + 0.05, z1p - 0.05, P.m("canvas", (60, 80, 60)))
        if im is not None:
            c["front"] = P.tex("founder", im)
        out.append(c)
        return out
    return None


# Modelle optionaler Erweiterungen (bm_ext.py): melden sich beim Import ueber model() / variant() an
import bm_ext                                                                                                      # noqa: E402
bm_ext.load_models()
