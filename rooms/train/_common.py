# Polaris Express (Zugkarte, Unknown's Atlas) - gemeinsame Bausteine: Wand- und Bodentexturen (prozedural, die Karte
# ist im Spiel noch eine Graubox), Nachtfenster, Konsolen je Aufgabenart, Tueren, Faltenbaelge.
#
# Stil: Nachtzug der 1920er. Holzvertaefelung (Walnuss) mit Messingleiste, Stoffbespannung darueber, Fenster mit
# Nachtlandschaft (Sterne, Huegel, ferne Lichter) als Bild im Rahmen: durch ein echtes Loch in der Wand saehe man nur
# die Wandmasse der Karte. Technikraeume in Stahl mit Nieten.

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from bm_spec import box, cyl, lathe, tube, obox, prism, rot3
import bm_models as M

H = 1.73
OL = (18, 20, 24)
WALNUT = (92, 58, 38)
WALNUT_D = (66, 40, 26)
CREAM = (214, 196, 160)
GREEN = (58, 92, 70)
BURGUNDY = (112, 32, 44)
BRASS = (201, 162, 76)
STEEL = (118, 124, 132)
STEEL_D = (74, 78, 86)
RIVET = (150, 156, 164)
NIGHT = (14, 18, 40)

_FONT = None


def font(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _sh(rgb, f):
    return tuple(max(0, min(255, int(v * f))) for v in rgb)


def _noise(d, w, h, rgb, n, amp, seed):
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.randrange(w), rnd.randrange(h)
        f = 1 + rnd.uniform(-amp, amp)
        d.point((x, y), fill=_sh(rgb, f))


# ------------------------------------------------------------------------------------------- Wandtexturen

def night_scene(w, h, seed=0, moon=False):
    """Nachtlandschaft hinter dem Fenster: Himmelsverlauf, Sterne, Huegelkette, ferne Lichter."""
    im = Image.new("RGB", (w, h), NIGHT)
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        c = (int(10 + 20 * t), int(14 + 24 * t), int(40 + 40 * t))
        d.line([(0, y), (w, y)], fill=c)
    rnd = random.Random(seed)
    for _ in range(int(w * h / 180)):
        x, y = rnd.randrange(w), rnd.randrange(int(h * 0.7))
        b = rnd.randint(150, 255)
        d.point((x, y), fill=(b, b, min(255, b + 20)))
    if moon:
        r = int(h * 0.09)
        mx, my = int(w * 0.72), int(h * 0.22)
        d.ellipse([mx - r, my - r, mx + r, my + r], fill=(236, 232, 210))
    # Huegel
    pts = [(0, h)]
    for i in range(0, w + 1, max(4, w // 24)):
        pts.append((i, int(h * (0.66 + 0.08 * math.sin(i / w * 6.3 + seed) + 0.04 * math.sin(i / w * 17 + seed * 2)))))
    pts.append((w, h))
    d.polygon(pts, fill=(18, 24, 34))
    pts2 = [(0, h)]
    for i in range(0, w + 1, max(4, w // 20)):
        pts2.append((i, int(h * (0.78 + 0.06 * math.sin(i / w * 4.1 + seed * 3)))))
    pts2.append((w, h))
    d.polygon(pts2, fill=(10, 14, 22))
    for _ in range(3):
        x, y = rnd.randrange(w), int(h * rnd.uniform(0.8, 0.92))
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 220, 140))
    return im


def wall_tile(ctx, name, style="wood", window=True, seed=0, size=512):
    """Quadratische Wandkachel H x H (uv world, Kachel laengs der Wand): Vertaefelung + Bespannung + Fenster."""
    s = size
    px = s / H
    im = Image.new("RGB", (s, s), CREAM)
    d = ImageDraw.Draw(im)
    if style in ("wood", "wood_green", "wood_red"):
        upper = {"wood": CREAM, "wood_green": GREEN, "wood_red": BURGUNDY}[style]
        d.rectangle([0, 0, s, s], fill=upper)
        _noise(d, s, s, upper, s * s // 10, 0.06, seed)
        zr = int(s - 0.95 * px)                                            # Oberkante Vertaefelung (0,95 m)
        d.rectangle([0, zr, s, s], fill=WALNUT)
        for i in range(6):                                                 # Paneelfugen
            x = int(s * (i + 0.5) / 6)
            d.line([(x, zr + 10), (x, s)], fill=WALNUT_D, width=3)
            d.rectangle([x - int(s / 12) + 12, zr + 24, x + int(s / 12) - 12, s - 20], outline=_sh(WALNUT, 1.25), width=2)
        d.rectangle([0, zr - 8, s, zr + 4], fill=BRASS)                    # Messingleiste
        d.rectangle([0, s - int(0.08 * px), s, s], fill=WALNUT_D)          # Fussleiste
        d.rectangle([0, 0, s, int(0.05 * px)], fill=_sh(upper, 0.75))       # Deckenleiste
        if window:
            wx0, wx1 = int(s * 0.18), int(s * 0.82)
            wz0, wz1 = int(s - 1.62 * px), int(s - 1.0 * px)
            d.rectangle([wx0 - 14, wz0 - 14, wx1 + 14, wz1 + 14], fill=WALNUT_D)
            d.rectangle([wx0 - 8, wz0 - 8, wx1 + 8, wz1 + 8], fill=BRASS)
            sc = night_scene(wx1 - wx0, wz1 - wz0, seed=seed, moon=(seed % 3 == 1))
            im.paste(sc, (wx0, wz0))
            d.line([(wx0 + 10, wz0 + 10), (wx0 + 40, wz0 + 10), (wx0 + 10, wz0 + 40)], fill=(90, 110, 160), width=3)
            d.line([((wx0 + wx1) // 2, wz0), ((wx0 + wx1) // 2, wz1)], fill=BRASS, width=4)
            d.rectangle([wx0 - 20, wz1 + 14, wx1 + 20, wz1 + 26], fill=WALNUT)        # Fensterbank
            # Vorhaenge
            for cx0 in (wx0 - 34, wx1 + 2):
                d.rectangle([cx0, wz0 - 30, cx0 + 32, wz1 + 14], fill=BURGUNDY if style != "wood_red" else GREEN)
                for k in range(4):
                    d.line([(cx0 + 6 + k * 7, wz0 - 30), (cx0 + 6 + k * 7, wz1 + 14)], fill=_sh(BURGUNDY if style != "wood_red" else GREEN, 0.7), width=2)
            d.rectangle([wx0 - 40, wz0 - 36, wx1 + 40, wz0 - 24], fill=BRASS)
    elif style in ("steel", "steel_dark"):
        base = STEEL if style == "steel" else STEEL_D
        d.rectangle([0, 0, s, s], fill=base)
        _noise(d, s, s, base, s * s // 6, 0.08, seed)
        for i in range(3):
            y = int(s * i / 3)
            d.line([(0, y), (s, y)], fill=_sh(base, 0.7), width=4)
            for j in range(8):
                x = int(s * (j + 0.5) / 8)
                d.ellipse([x - 5, y + 14, x + 5, y + 24], fill=RIVET, outline=_sh(base, 0.6))
        d.line([(s // 2, 0), (s // 2, s)], fill=_sh(base, 0.72), width=4)
        d.rectangle([0, s - int(0.06 * px), s, s], fill=_sh(base, 0.6))
        if window:
            wx0, wx1 = int(s * 0.3), int(s * 0.7)
            wz0, wz1 = int(s - 1.55 * px), int(s - 1.1 * px)
            d.rectangle([wx0 - 10, wz0 - 10, wx1 + 10, wz1 + 10], fill=_sh(base, 0.5))
            im.paste(night_scene(wx1 - wx0, wz1 - wz0, seed=seed), (wx0, wz0))
            for k in range(8):
                a = 2 * math.pi * k / 8
                d.ellipse([(wx0 + wx1) / 2 + (wx1 - wx0) * 0.58 * math.cos(a) - 4, (wz0 + wz1) / 2 + (wz1 - wz0) * 0.72 * math.sin(a) - 4,
                           (wx0 + wx1) / 2 + (wx1 - wx0) * 0.58 * math.cos(a) + 4, (wz0 + wz1) / 2 + (wz1 - wz0) * 0.72 * math.sin(a) + 4], fill=RIVET)
    elif style == "brick":
        base = (120, 66, 52)
        d.rectangle([0, 0, s, s], fill=(70, 60, 56))
        bw, bh = s // 6, s // 14
        for r in range(15):
            off = (bw // 2) if r % 2 else 0
            for c in range(-1, 7):
                x0, y0 = c * bw + off, r * bh
                d.rectangle([x0 + 3, y0 + 3, x0 + bw - 3, y0 + bh - 3], fill=_sh(base, 1 + 0.12 * math.sin(r * 3.1 + c * 1.7)))
    elif style == "tile":
        d.rectangle([0, 0, s, s], fill=(226, 228, 224))
        n = 8
        for r in range(n):
            for c in range(n):
                f = 1.0 if (r + c) % 2 == 0 else 0.92
                d.rectangle([c * s / n + 2, r * s / n + 2, (c + 1) * s / n - 2, (r + 1) * s / n - 2], fill=_sh((226, 228, 224), f))
        d.rectangle([0, s - int(0.08 * px), s, s], fill=(90, 94, 100))
        if window:
            wx0, wx1 = int(s * 0.3), int(s * 0.7)
            wz0, wz1 = int(s - 1.55 * px), int(s - 1.1 * px)
            d.rectangle([wx0 - 10, wz0 - 10, wx1 + 10, wz1 + 10], fill=(90, 94, 100))
            im.paste(night_scene(wx1 - wx0, wz1 - wz0, seed=seed), (wx0, wz0))
    return ctx.tex(name, im, uv="world", scale=[H, H])


def floor_tile(ctx, name, style="carpet", size=512, seed=0):
    """Bodenkachel 1 x 1 m (uv world)."""
    s = size
    im = Image.new("RGB", (s, s), BURGUNDY)
    d = ImageDraw.Draw(im)
    if style in ("carpet", "carpet_green"):
        base = BURGUNDY if style == "carpet" else GREEN
        d.rectangle([0, 0, s, s], fill=base)
        _noise(d, s, s, base, s * s // 4, 0.1, seed)
        g = _sh(BRASS, 0.8)
        for i in range(2):
            for j in range(2):
                cx, cy = int(s * (i + 0.5) / 2), int(s * (j + 0.5) / 2)
                r = s // 7
                d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], outline=g, width=3)
                d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=g)
    elif style == "planks":
        base = (150, 108, 66)
        n = 6
        for i in range(n):
            f = 1 + 0.1 * math.sin(i * 2.3 + seed)
            d.rectangle([0, i * s / n, s, (i + 1) * s / n], fill=_sh(base, f))
            d.line([(0, i * s / n), (s, i * s / n)], fill=_sh(base, 0.55), width=3)
            off = int(s * ((i * 0.37 + seed * 0.1) % 1.0))
            d.line([(off, i * s / n), (off, (i + 1) * s / n)], fill=_sh(base, 0.55), width=3)
            rnd = random.Random(seed * 10 + i)
            for _ in range(5):
                y = rnd.uniform(i * s / n + 6, (i + 1) * s / n - 6)
                d.line([(0, y), (s, y + rnd.uniform(-4, 4))], fill=_sh(base, 0.9), width=1)
    elif style == "plate":
        base = (104, 110, 118)
        d.rectangle([0, 0, s, s], fill=base)
        _noise(d, s, s, base, s * s // 5, 0.08, seed)
        for i in range(8):
            for j in range(8):
                cx, cy = int(s * (i + 0.5) / 8), int(s * (j + 0.5) / 8)
                a = 45 if (i + j) % 2 == 0 else -45
                dx, dy = int(14 * math.cos(math.radians(a))), int(14 * math.sin(math.radians(a)))
                d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=_sh(base, 1.3), width=5)
                d.line([(cx - dx, cy - dy + 3), (cx + dx, cy + dy + 3)], fill=_sh(base, 0.7), width=2)
    elif style == "tiles":
        n = 4
        for i in range(n):
            for j in range(n):
                c = (226, 228, 224) if (i + j) % 2 == 0 else (40, 42, 48)
                d.rectangle([i * s / n + 2, j * s / n + 2, (i + 1) * s / n - 2, (j + 1) * s / n - 2], fill=c)
        d.rectangle([0, 0, s, s], outline=(90, 94, 100), width=4)
    elif style == "grating":
        base = (70, 74, 80)
        d.rectangle([0, 0, s, s], fill=base)
        for i in range(0, s, s // 10):
            d.line([(i, 0), (i, s)], fill=_sh(base, 1.4), width=4)
            d.line([(0, i), (s, i)], fill=_sh(base, 1.4), width=4)
    elif style == "coal":
        d.rectangle([0, 0, s, s], fill=(30, 28, 30))
        _noise(d, s, s, (40, 38, 42), s * s // 2, 0.5, seed)
    return ctx.tex(name, im, uv="world", scale=[1.0, 1.0])


# ------------------------------------------------------------------------------------------- Konsolen

YAW = {"S": 0.0, "E": 90.0, "N": 180.0, "W": 270.0}


def _f(facing):
    return M._fx(YAW[facing])


def console(ctx, key, x, y, facing="S", wall=True):
    """Aufgabenkonsole an Position (x, y); facing = Seite, auf der der Spieler steht. Wandgeraet (Kasten an der Wand,
    Oberkante 1,45) oder Standgeraet, Ausfuehrung nach Aufgabenart."""
    kind = key.split("/")[1]
    nm = "tc_" + key.replace("/", "_")
    f = _f(facing)
    yaw = YAW[facing]
    body = ctx.color(nm + "_body", (84, 76, 70))
    dark = ctx.color(nm + "_dark", (40, 38, 40))
    brass = ctx.color("train_brass", BRASS)
    parts = []

    def at(lx, ly, lz):
        o = f(lx, ly, lz)
        return (x + o[0], y + o[1], o[2])

    def ob(lx, ly, lz, size, mat, **kw):
        c = at(lx, ly, lz)
        return obox(c, size, mat, yaw=yaw, **kw)

    def screen(lx, ly, z0, z1, w, rgb=(120, 190, 170), glow=1.5):
        c = at(lx, ly, 0.0)
        return M.screen_panel(ctx, nm + f"_scr{int(z0 * 100)}", c[0], c[1], z0, z1, w, facing, None, rgb, glow=glow)

    if kind in ("FixWiringConsole",):
        parts.append(ob(0, 0.08, 1.15, (0.55, 0.14, 0.6), body, outline=OL))
        parts.append(ob(0, 0.0, 1.15, (0.45, 0.02, 0.5), dark))
        for i, c in enumerate(((230, 60, 60), (70, 120, 230), (240, 200, 60), (230, 120, 200))):
            wm = ctx.glow(nm + f"_w{i}", c, 1.0)
            a = at(-0.17, -0.012, 1.35 - i * 0.1)
            b = at(0.17, -0.012, 1.3 - ((i * 2) % 4) * 0.1)
            parts.append(tube([a, b], 0.008, wm, seg=5))
        parts.append(ob(0, -0.015, 0.84, (0.57, 0.02, 0.03), brass))
    elif kind in ("DivertPowerConsole", "SwitchConsole", "AirlockConsole"):
        parts.append(ob(0, 0.08, 1.1, (0.5, 0.14, 0.55), body, outline=OL))
        parts.append(ob(0, 0.0, 1.1, (0.4, 0.02, 0.45), dark))
        n = 6 if kind != "AirlockConsole" else 1
        for i in range(n):
            lx = -0.14 + 0.056 * i if n > 1 else 0.0
            up = (i % 3 != 1)
            parts.append(ob(lx, -0.02, 1.1 + (0.06 if up else -0.06), (0.03, 0.03, 0.12), brass))
            parts.append(obox(at(lx, -0.04, 1.1 + (0.12 if up else -0.12)), (0.04, 0.04, 0.04), ctx.color(nm + "_knob", (200, 50, 50) if up else (60, 60, 60)), yaw=yaw))
        parts.append(screen(0, -0.012, 1.26, 1.3, 0.3, (240, 200, 70), 1.4))
    elif kind in ("UploadDataConsole", "DataConsole", "FixCommsConsole", "CalibrateConsole", "StartReactorConsole", "ChartCourseConsole", "ShieldConsole", "WeaponConsole", "StabilizeSteeringConsole"):
        if kind in ("ChartCourseConsole", "WeaponConsole", "StabilizeSteeringConsole", "ShieldConsole"):
            # Standpult mit Schraege
            c = at(0, 0.3, 0)
            parts += M.floor_console(ctx, nm, c[0], c[1], 0.9, 0.6, 0.95, body_rgb=(84, 76, 70), yaw=yaw, slope=True)
            if kind == "StabilizeSteeringConsole":
                w = ctx.color(nm + "_wheel", (120, 80, 50))
                c2 = at(0, 0.05, 1.05)
                parts.append(lathe(c2[0], c2[1], [(0.2, c2[2] - 0.02), (0.24, c2[2] - 0.02), (0.24, c2[2] + 0.02), (0.2, c2[2] + 0.02)], w, seg=20, outline=OL, tilt=(90.0, YAW[facing] + 90.0, c2[2])))
                for i in range(6):
                    a = math.radians(i * 60)
                    e = rot3((0.2 * math.cos(a), 0.0, 0.2 * math.sin(a)), yaw, 0.0)
                    parts.append(tube([c2, (c2[0] + e[0], c2[1] + e[1], c2[2] + e[2])], 0.012, w, seg=6))
            return parts
        parts.append(ob(0, 0.08, 1.15, (0.6, 0.14, 0.55), body, outline=OL))
        parts.append(screen(0, -0.006, 0.98, 1.36, 0.46, {"FixCommsConsole": (110, 230, 120), "StartReactorConsole": (240, 120, 60), "CalibrateConsole": (240, 200, 70)}.get(kind, (120, 190, 220))))
        for i in range(3):
            parts.append(obox(at(-0.16 + 0.16 * i, -0.02, 0.92), (0.05, 0.03, 0.03), ctx.glow(nm + f"_b{i}", [(230, 70, 60), (80, 220, 90), (240, 200, 70)][i], 1.6), yaw=yaw))
        if kind == "FixCommsConsole":
            parts.append(ob(0.22, -0.03, 1.2, (0.04, 0.04, 0.14), brass))
    elif kind in ("NoOxyConsole",):
        parts.append(ob(0, 0.06, 1.2, (0.3, 0.1, 0.42), body, outline=OL))
        parts.append(screen(0, -0.006, 1.3, 1.38, 0.22, (120, 220, 140), 1.6))
        for r in range(3):
            for c in range(3):
                parts.append(obox(at(-0.07 + 0.07 * c, -0.015, 1.05 + 0.08 * r), (0.05, 0.015, 0.05), ctx.color(nm + "_key", (200, 200, 196)), yaw=yaw))
    elif kind in ("GarbageConsole",):
        parts.append(ob(0, 0.1, 0.55, (0.6, 0.2, 1.0), body, outline=OL))
        parts.append(ob(0, 0.0, 0.9, (0.45, 0.03, 0.35), dark))
        parts.append(ob(-0.22, -0.04, 1.0, (0.03, 0.03, 0.35), brass))
        parts.append(obox(at(-0.22, -0.06, 1.18), (0.05, 0.05, 0.05), ctx.color(nm + "_knob", (200, 50, 50)), yaw=yaw))
    elif kind in ("CleanFilterConsole",):
        parts.append(ob(0, 0.08, 1.1, (0.6, 0.16, 0.5), ctx.color(nm + "_steel", STEEL), outline=OL))
        parts.append(ob(0, -0.005, 1.1, (0.5, 0.02, 0.4), dark))
        for i in range(5):
            parts.append(ob(0, -0.01, 0.95 + i * 0.08, (0.48, 0.012, 0.02), ctx.color(nm + "_slat", STEEL)))
        parts.append(ob(0.2, -0.03, 1.35, (0.03, 0.03, 0.12), brass))
    elif kind in ("AlignEngineConsole", "UnlockManifoldsConsole"):
        parts.append(ob(0, 0.08, 1.15, (0.55, 0.14, 0.5), ctx.color(nm + "_steel", STEEL), outline=OL))
        parts.append(ob(0, -0.006, 1.25, (0.3, 0.012, 0.3), ctx.color(nm + "_dial", (236, 232, 220))))
        parts.append(ob(0, -0.016, 1.25, (0.012, 0.012, 0.12), dark))
        if kind == "UnlockManifoldsConsole":
            for i in range(3):
                c2 = at(-0.18 + 0.18 * i, -0.03, 0.95)
                parts.append(lathe(c2[0], c2[1], [(0.0, c2[2] - 0.02), (0.06, c2[2] - 0.02), (0.06, c2[2] + 0.02), (0.0, c2[2] + 0.02)], ctx.color(nm + "_valve", (190, 40, 40)), seg=12, outline=OL, tilt=(90.0, YAW[facing] + 90.0, c2[2])))
    elif kind in ("FuelEngineConsole", "gasCanConsole"):
        c = at(0, 0.3, 0)
        if kind == "FuelEngineConsole":
            parts += M.gas_pump(ctx, nm, c[0] - 0.25, c[1] - 0.2, c[0] + 0.25, c[1] + 0.2, h=1.3, rgb=(170, 60, 50))
        else:
            for i, (dx, dy) in enumerate(((-0.2, 0.0), (0.15, 0.1), (0.05, -0.2))):
                parts.append(box(c[0] + dx, c[1] + dy, 0.26, 0.2, 0.0, 0.4, ctx.color(nm + f"_can{i}", (190, 60, 50)), bevel=0.01, outline=OL))
                parts.append(box(c[0] + dx, c[1] + dy, 0.1, 0.04, 0.4, 0.46, dark))
        return parts
    elif kind in ("SwipeCardConsole",):
        c = at(0, 0.3, 0)
        parts += M.table(ctx, nm + "_t", c[0] - 0.35, c[1] - 0.25, c[0] + 0.35, c[1] + 0.25, h=0.8, top_rgb=WALNUT, leg_rgb=WALNUT_D)
        parts.append(ob(0.1, 0.3, 0.85, (0.3, 0.14, 0.1), dark, outline=OL))
        parts.append(ob(0.1, 0.3, 0.92, (0.2, 0.012, 0.02), ctx.glow(nm + "_slot", (90, 230, 120), 1.6)))
        parts.append(obox(at(-0.2, 0.3, 0.805), (0.16, 0.1, 0.01), ctx.color(nm + "_card", (230, 230, 226)), yaw=yaw + 15))
        return parts
    elif kind in ("MedBayConsole",):
        c = at(0, 0.3, 0)
        parts += M.table(ctx, nm + "_t", c[0] - 0.4, c[1] - 0.25, c[0] + 0.4, c[1] + 0.25, h=0.8, top_rgb=(200, 204, 210), leg_rgb=STEEL_D)
        for i, col in enumerate(((230, 70, 70), (80, 200, 120), (90, 140, 230), (240, 200, 80))):
            parts.append(lathe(c[0] - 0.24 + i * 0.16, c[1], [(0.0, 0.8), (0.035, 0.8), (0.035, 0.9), (0.015, 0.93), (0.015, 1.0), (0.0, 1.0)], ctx.glow(nm + f"_fl{i}", col, 1.2), seg=8))
        return parts
    elif kind in ("MedScanner",):
        c = at(0, 0.0, 0)
        return M.scanner(ctx, nm, c[0], c[1], r=0.55, pods=3)
    elif kind in ("LowerHandConsole", "UpperHandConsole"):
        parts.append(ob(0, 0.06, 1.1, (0.36, 0.1, 0.42), body, outline=OL))
        parts.append(ob(0, -0.006, 1.1, (0.26, 0.012, 0.32), ctx.glow(nm + "_pad", (120, 220, 240), 1.4)))
        parts.append(ob(0, -0.012, 1.1, (0.14, 0.006, 0.2), ctx.glow(nm + "_hand", (230, 240, 250), 1.8)))
    else:
        parts.append(ob(0, 0.08, 1.1, (0.5, 0.14, 0.5), body, outline=OL))
        parts.append(screen(0, -0.006, 0.95, 1.3, 0.4))
    if not wall:
        # Standsaeule unter dem Wandgeraet
        parts.append(ob(0, 0.08, 0.45, (0.12, 0.12, 0.9), dark))
        parts.append(ob(0, 0.08, 0.02, (0.4, 0.3, 0.04), dark))
    return parts


# ------------------------------------------------------------------------------------------- Tueren, Durchgaenge

def door_frame(ctx, name, cx, cy, w, along="x", h=1.65, rgb=WALNUT, slide=0.0):
    """Tuerrahmen in einer Wand (along = Richtung der Wand) mit Schiebetuer, die um slide (0..1) offen steht."""
    fr = ctx.color(name + "_frame", rgb)
    dk = ctx.color(name + "_door", _sh(rgb, 1.15))
    br = ctx.color("train_brass", BRASS)
    out = []
    if along == "x":
        for sx in (-1, 1):
            out.append(box(cx + sx * (w / 2 + 0.04), cy, 0.08, 0.2, 0.0, h + 0.08, fr, outline=OL))
        out.append(box(cx, cy, w + 0.16, 0.2, h, h + 0.08, fr, outline=OL))
        if slide < 1.0:
            dw = w * (1 - slide)
            out.append(box(cx - w / 2 + dw / 2, cy + 0.06, dw, 0.04, 0.02, h - 0.02, dk, bevel=0.008, outline=OL))
            out.append(box(cx - w / 2 + dw / 2, cy + 0.0, dw * 0.5, 0.012, h * 0.55, h * 0.85, ctx.color(name + "_win", (120, 140, 170))))
            out.append(cyl(cx - w / 2 + dw - 0.06, cy + 0.03, 0.015, 0.95, 1.0, br, seg=8))
    else:
        for sy in (-1, 1):
            out.append(box(cx, cy + sy * (w / 2 + 0.04), 0.2, 0.08, 0.0, h + 0.08, fr, outline=OL))
        out.append(box(cx, cy, 0.2, w + 0.16, h, h + 0.08, fr, outline=OL))
        if slide < 1.0:
            dw = w * (1 - slide)
            out.append(box(cx + 0.06, cy - w / 2 + dw / 2, 0.04, dw, 0.02, h - 0.02, dk, bevel=0.008, outline=OL))
    return out


def bellows(ctx, name, x0, x1, y0, y1, h=H):
    """Faltenbalg zwischen zwei Wagen: Rippen an beiden Waenden, Stahlplatte als Schwelle, Rahmen an den Enden."""
    rib = ctx.color("train_bellow", (44, 40, 44))
    rib2 = ctx.color("train_bellow2", (70, 64, 70))
    plate = ctx.color("train_plate", (90, 94, 100))
    out = [box((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, 0.0, 0.03, plate, outline=OL)]
    n = max(3, int((x1 - x0) / 0.18))
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        for y, s in ((y0, 1), (y1, -1)):
            out.append(box(x, y + s * 0.04, 0.07, 0.08, 0.05, h - 0.05, rib if i % 2 else rib2, bevel=0.01))
        out.append(box(x, (y0 + y1) / 2, 0.07, y1 - y0, h - 0.1, h - 0.02, rib if i % 2 else rib2))
    for x in (x0, x1):
        out.append(box(x, (y0 + y1) / 2, 0.08, y1 - y0 + 0.2, h - 0.08, h + 0.04, plate, outline=OL))
        for y in (y0, y1):
            out.append(box(x, y, 0.08, 0.12, 0.0, h + 0.04, plate, outline=OL))
    return out


def stairs_sign(ctx, name, cx, y, facing, text, z=1.15):
    """Messingschild mit Pfeil an der Treppenblock-Wand (Treppen sind im Spiel Teleports per Use-Knopf)."""
    im = Image.new("RGB", (320, 110), BRASS)
    d = ImageDraw.Draw(im)
    d.rectangle([6, 6, 313, 103], outline=(90, 70, 30), width=4)
    d.text((160, 40), text, fill=(50, 38, 20), font=font(36), anchor="mm")
    d.text((160, 82), "▼" if "LOWER" in text else "▲", fill=(50, 38, 20), font=font(28), anchor="mm")
    t = ctx.tex(name, im, uv="part")
    b = M.screen_panel(ctx, name + "_p", cx, y, z - 0.12, z + 0.12, 0.7, facing, None, BRASS, depth=0.02, glow=0.0)
    b[{"S": "front", "N": "face_n", "E": "face_e", "W": "face_w"}[facing]] = t
    b["mat"] = ctx.color("train_brass", BRASS)
    # Handlauf und erste Stufe vor dem Block
    br = ctx.color("train_brass", BRASS)
    f = _f(facing)
    o = f(0.0, 0.3, 0.0)
    out = [b, box(cx + o[0] * 0, y + (0.0), 0.02, 0.02, 0.0, 0.0001, br)]
    for sx in (-1, 1):
        a = f(sx * 0.42, -0.05, 0.0)
        bb = f(sx * 0.42, -0.6, 0.0)
        out.append(cyl(cx + a[0], y + a[1], 0.018, 0.0, 0.95, br, seg=8))
        out.append(tube([(cx + a[0], y + a[1], 0.95), (cx + bb[0], y + bb[1], 0.95)], 0.018, br, seg=8))
        out.append(cyl(cx + bb[0], y + bb[1], 0.018, 0.0, 0.95, br, seg=8))
    return out


def lamp_sconce(ctx, name, x, y, z, facing="S"):
    """Wandleuchte: Messingarm, Glasschirm leuchtend."""
    f = _f(facing)
    br = ctx.color("train_brass", BRASS)
    gl = ctx.glow("train_lampglass", (255, 226, 170), 2.6)
    a = f(0, 0.0, 0)
    b = f(0, -0.14, 0)
    out = [tube([(x + a[0], y + a[1], z), (x + b[0], y + b[1], z + 0.08)], 0.012, br, seg=6),
           lathe(x + b[0], y + b[1], [(0.0, z + 0.08), (0.05, z + 0.1), (0.07, z + 0.22), (0.0, z + 0.24)], gl, seg=12)]
    return out


def ceiling_lamp(ctx, name, x, y, z=H - 0.05):
    br = ctx.color("train_brass", BRASS)
    gl = ctx.glow("train_lampglass", (255, 226, 170), 2.6)
    return [cyl(x, y, 0.04, z - 0.03, z, br, seg=10),
            lathe(x, y, [(0.0, z - 0.03), (0.14, z - 0.05), (0.16, z - 0.14), (0.0, z - 0.18)], gl, seg=16)]


def seat_bench(ctx, name, x0, y0, x1, y1, back="N", rgb=BURGUNDY, h=0.45, back_h=0.5):
    """Sitzbank mit Polster und Rueckenlehne an der Seite back (N/S/E/W), Holzrahmen."""
    wood = ctx.color(name + "_wood", WALNUT)
    uph = ctx.color(name + "_uph", rgb)
    uph_d = ctx.color(name + "_uph_d", _sh(rgb, 0.8))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, d = x1 - x0, y1 - y0
    out = [box(cx, cy, w, d, 0.0, h - 0.12, wood, outline=OL),
           box(cx, cy, w - 0.02, d - 0.02, h - 0.12, h, uph, bevel=0.03, outline=OL)]
    t = 0.14
    if back == "N":
        out.append(box(cx, y1 - t / 2, w, t, h, h + back_h, uph_d, bevel=0.03, outline=OL))
    elif back == "S":
        out.append(box(cx, y0 + t / 2, w, t, h, h + back_h, uph_d, bevel=0.03, outline=OL))
    elif back == "E":
        out.append(box(x1 - t / 2, cy, t, d, h, h + back_h, uph_d, bevel=0.03, outline=OL))
    else:
        out.append(box(x0 + t / 2, cy, t, d, h, h + back_h, uph_d, bevel=0.03, outline=OL))
    return out


def bunk(ctx, name, x0, y0, x1, y1, levels=2, head="W"):
    """Etagenbett im Schlafabteil: Holzrahmen, zwei Liegen mit Decke und Kissen, Leiter."""
    out = []
    for i in range(levels):
        z = 0.3 + i * 0.7
        out += M.lift(M.bed(ctx, f"{name}_{i}", x0, y0, x1, y1, head=head, frame_rgb=WALNUT, mattress_rgb=(222, 226, 236), h_frame=0.18, h_mattress=0.12), z)
        out.append(box((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 0.75, (y1 - y0) - 0.08, z + 0.3, z + 0.36, ctx.color(name + "_blanket", GREEN), bevel=0.02))
    for x in (x0 + 0.03, x1 - 0.03):
        for y in (y0 + 0.03, y1 - 0.03):
            out.append(box(x, y, 0.06, 0.06, 0.0, 1.35, ctx.color(name + "_post", WALNUT_D)))
    return out


def crate(ctx, name, cx, cy, w, d, h, rgb=(150, 108, 66), z0=0.0, rot=0.0, label=None):
    wood = ctx.color(name + "_w", rgb)
    dk = ctx.color(name + "_d", _sh(rgb, 0.7))
    out = [box(cx, cy, w, d, z0, z0 + h, wood, rot=rot, bevel=0.01, outline=OL)]
    for z in (z0 + h * 0.3, z0 + h * 0.7):
        out.append(box(cx, cy, w + 0.012, d + 0.012, z - 0.02, z + 0.02, dk, rot=rot))
    return out
