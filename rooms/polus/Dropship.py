# Polus / Dropship - am Kartenfoto gemessen (bm_analyze.py profile/colors, zoomgrid.py).
#
# Among Us zeigt den Innenraum als gemaltes Perspektivbild; nachgebaut als echter Laderaum:
#   Boden (90,102,107) mit gelben Linien (129,121,88) 0,05 breit, senkrecht bei x 15,11 / 16,16 / 17,20 / 18,25
#   (Abstand 1,05), waagerecht bei y -4,74 / -5,37 / -5,98 (Abstand 0,62). Innenraum x 14,47..18,90 bis y -0,5.
#   Seitenwaende dunkle Rippen (52,60,57) auf (36,43,41), Rueckwand (43,51,48) mit rundem Licht, Decke (100,99,96)
#   mit blauer Lichtleiste (13,53,79), Sitzbank links (58,107,124), Leuchte rechts.
# Aussen: Rumpf fast schwarz (5,6,6) bis (41,51,49), Heckflaeche bei y -6,1 mit je einem Triebwerksblock (vier
#   Luefter, Zeichnung als Front, Rahmen (16,43,55)), Tankstutzen (panel_fuel) links und rechts.

import numpy as np
from PIL import Image

import bm_tex as T
from bm_spec import box, cyl, lathe, prism, sprite, flat_rgb
PROCEDURAL = True      # zeichnet Boden/Waende selbst (keine Spieltextur), bleibt bei bm_style aktiv

H = 3.0
FULL_WALLS = True
LINE = (129, 121, 88)
FLOOR = (90, 102, 107)
GX0, GDX = 15.11, 1.05
GY0, GDY = -5.98, 0.62
IX0, IX1, IY1 = 14.47, 18.90, -0.5
HULL = (11.0, 22.4, -6.1, 3.5)               # Rumpf x0, x1, y0 (Heck), y1
HULL_H = 4.2
HULL_DARK, HULL_MID = (20, 24, 24), (41, 51, 49)


def floor(ctx):
    n = 128
    w, h = int(round(GDX * n)), int(round(GDY * n))
    im = np.zeros((h, w, 3), np.uint8) + np.array(FLOOR, np.uint8)
    lw = max(1, int(round(0.05 * n)))
    im[:, :lw] = LINE                                           # Linie am linken Kachelrand (x = GX0 + i*GDX)
    im[h - lw:, :] = LINE                                       # Linie am unteren Kachelrand (y = GY0 + j*GDY)
    return ctx.tex("ds_floor", Image.fromarray(im), uv="world", scale=[GDX, GDY],
                   offset=[GX0 - 0.025, GY0 - 0.025])


def side(ctx):
    """Rippenwand: senkrechte helle Rippen 0,08 breit alle 0,5 auf dunklem Grund, Sockel und Kopfleiste."""
    n = 128
    w, h = 64, int(round(H * n))
    im = np.zeros((h, w, 3), np.uint8) + np.array((36, 43, 41), np.uint8)
    im[:, 22:42] = (52, 60, 57)
    im[h - 20:, :] = (41, 51, 49)
    im[:14, :] = (58, 67, 63)
    return ctx.tex("ds_side", Image.fromarray(im), uv="world", scale=[0.5, H])


def north(ctx, e):
    return ctx.color("ds_back", (43, 51, 48))


def props(ctx):
    parts = []
    dark = ctx.color("ds_hull", HULL_DARK)
    mid = ctx.color("ds_hull_mid", HULL_MID)
    x0, x1, y0, y1 = HULL
    # Rumpf (Fehlerrunde 19.10., #256/#284): Seitenwaende bis 2,8, darueber ein gewoelbtes Dach (halbe Ellipse ueber die
    # ganze Breite) mit Stirnflaechen vorn und hinten; vorher ein schwarzer Quader, dessen Unterseite deckungsgleich
    # mit der Laderaumdecke lag (Z-Fighting: "Tarnmuster" an der Decke).
    import math
    from bm_spec import obox
    ZS = 2.8
    parts.append(box((x0 + IX0 - 0.05) / 2, (y0 + y1) / 2, IX0 - 0.05 - x0, y1 - y0, 0.0, ZS, dark, top=mid,
                     bevel=0.05, outline=(3, 4, 3)))
    parts.append(box((IX1 + 0.05 + x1) / 2, (y0 + y1) / 2, x1 - IX1 - 0.05, y1 - y0, 0.0, ZS, dark, top=mid,
                     bevel=0.05, outline=(3, 4, 3)))
    parts.append(box((IX0 + IX1) / 2, (IY1 + 0.05 + y1) / 2, IX1 - IX0 + 0.1, y1 - IY1 - 0.05, 0.0, ZS, dark, top=mid,
                     outline=(3, 4, 3)))
    cxh, a_, b_ = (x0 + x1) / 2, (x1 - x0) / 2, 1.7
    n = 16
    for i in range(n):
        t0, t1 = math.pi * i / n, math.pi * (i + 1) / n
        p0 = (cxh + a_ * math.cos(t0), ZS + b_ * math.sin(t0))
        p1 = (cxh + a_ * math.cos(t1), ZS + b_ * math.sin(t1))
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        parts.append(obox(((p0[0] + p1[0]) / 2, (y0 + y1) / 2, (p0[1] + p1[1]) / 2), (L + 0.02, y1 - y0, 0.14),
                          mid if i % 4 == 0 else dark, pitch=ang, outline=(3, 4, 3)))
    # Stirnflaechen: senkrechte Streifen bis unter die Woelbung, vorn ueber der Laderaumoeffnung erst ab der Decke
    m = 28
    for i in range(m):
        xa, xb = x0 + (x1 - x0) * i / m, x0 + (x1 - x0) * (i + 1) / m
        xm = (xa + xb) / 2
        ztop = ZS + b_ * math.sqrt(max(0.0, 1 - ((xm - cxh) / a_) ** 2)) - 0.02
        zb = H + 0.02 if IX0 - 0.05 < xm < IX1 + 0.05 else ZS - 0.01
        for yy in (y0 + 0.04, y1 - 0.04):
            parts.append(box(xm, yy, xb - xa + 0.01, 0.08, zb, ztop, dark))
    # Decke des Laderaums von aussen: Platte knapp ueber der Decke (nicht deckungsgleich)
    parts.append(box((IX0 + IX1) / 2, (y0 + IY1) / 2, IX1 - IX0 + 0.1, IY1 - y0, H + 0.03, H + 0.06, dark))
    # Triebwerksbloecke am Heck mit vier Luefterhaeusern je Block (Mantel, Fluegel, Nabe, Gitter)
    frame = ctx.color("ds_engine_frame", (16, 43, 55))
    from bm_models import fan_housing, gas_pump
    for i, (ex0, ex1) in enumerate(((11.30, 13.55), (19.75, 22.05))):
        parts.append(box((ex0 + ex1) / 2, y0 - 0.25, ex1 - ex0, 0.5, 0.35, 2.55, frame, bevel=0.02, outline=(3, 4, 3)))
        for j, (fx, fz) in enumerate(((ex0 + 0.55, 0.95), (ex1 - 0.55, 0.95), (ex0 + 0.55, 1.95), (ex1 - 0.55, 1.95))):
            parts += fan_housing(ctx, f"ds_engine_{i}_fan{j}", fx, y0 - 0.53, fz, r=0.42, rgb=(60, 90, 100), blade_rgb=(24, 50, 60), depth=0.1)
    # Tankstutzen (panel_fuel) als Zapfsaeulen mit Schlauch
    for suf in ("Dropship/panel_fuel", "Dropship/panel_fuel (1)"):
        _, (sx0, sy0, sx1, sy1) = sprite(ctx, suf)
        parts += gas_pump(ctx, "ds_" + suf.split("/")[-1].replace(" ", "").replace("(", "").replace(")", ""), sx0, sy0, sx1, sy0 + 0.24,
                          h=(sy1 - sy0) / 0.8, rgb=(74, 63, 114))
    # Laderaum: Sitzbank links, Leuchte rechts, rundes Licht an der Rueckwand, Lichtleiste an der Decke
    bench = ctx.color("ds_bench", (58, 107, 124))
    benchd = ctx.color("ds_bench_dark", (36, 70, 84))
    parts.append(box(IX0 + 0.28, -2.6, 0.5, 2.6, 0.0, 0.42, benchd, top=bench, bevel=0.03, outline=(10, 30, 40)))
    # Lehne unter Augenhoehe: die Bank hat keinen Collider, der Spieler steht im Spiel darauf (Meldung 18.10. #112)
    parts.append(box(IX0 + 0.06, -2.6, 0.1, 2.6, 0.42, 0.56, bench, bevel=0.03, outline=(10, 30, 40)))
    pole = ctx.color("ds_lamp_pole", (60, 66, 70))
    lamp = ctx.glow("ds_lamp", (230, 222, 170), 2.0)
    parts.append(cyl(IX1 - 0.25, -1.4, 0.05, 0.0, 1.9, pole, seg=12, outline=(10, 12, 12)))
    parts.append(box(IX1 - 0.40, -1.4, 0.42, 0.16, 1.9, 2.0, lamp, outline=(10, 12, 12)))
    glow = ctx.glow("ds_porthole", (190, 202, 192), 1.5)
    parts.append(lathe((IX0 + IX1) / 2, IY1 - 0.04, [(0.0, 1.55), (0.6, 1.55), (0.6, 1.58), (0.0, 1.58)], glow, seg=48,
                       tilt=(90.0, 270.0, 1.55)))
    strip = ctx.glow("ds_ceiling_strip", (13, 53, 79), 1.0)
    parts.append(box((IX0 + IX1) / 2, -3.2, 0.25, 5.0, H - 0.04, H - 0.01, strip))
    # Rampe: Sprite als Oberseite einer flachen Platte vor dem Laderaum
    _, (rx0, ry0, rx1, ry1) = sprite(ctx, "Dropship/ramp")
    ramp = ctx.color("ds_ramp_side", (130, 143, 148))
    rib = ctx.color("ds_ramp_rib", (96, 108, 112))
    parts.append(box((rx0 + rx1) / 2, (ry0 + ry1) / 2, rx1 - rx0, ry1 - ry0, 0.0, 0.02, ramp, outline=(19, 26, 26)))
    for j in range(8):
        parts.append(box((rx0 + rx1) / 2, ry0 + (ry1 - ry0) * (j + 0.5) / 8, rx1 - rx0 - 0.2, 0.03, 0.02, 0.03, rib))
    return parts
