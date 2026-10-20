# Skeld / MedBay - am Kartenfoto gemessen (zoomgrid.py, bm_analyze.py).
#
# Boden: Zeichnung (Gang mit Grossfliesen, Bettstreifen, Kabel) in Originalpalette; unter Betten, Scanner und
#   Vent ergaenzt. Seitenwaende: Spalte der SO-Schraege (Blau 49,133,172 / Hellblau / Blassblau mit Fugen).
# Betten (Collider 1,11 x 0,83): Matratze oben im Bild x -11,12..-10,03 bzw. -8,10..-6,98, y -1,80..-1,28 bzw.
#   -3,12..-2,60; sichtbare Front 0,32 -> Liegeflaeche 0,54, Matratze 0,17, Rahmen mit Leiste (156,186,214) bei
#   0,21..0,25; Kissen (219,235,247) am Kopfende 0,32 breit, 0,12 hoch. Kontur (16,56,74).
# Scanner (Sprite MedScanner): Plattform Ellipse 0,62 x 0,25, Hoehe 0,30, Oberseite (176,207,211), Seite
#   (99,153,162), Glas 0,40 x 0,14 (Sprite-Ausschnitt), vier Eier r 0,14 h 0,30 an den Ellipsenenden, Kontur schwarz.

from shapely.geometry import box as sbox

import bm_tex as T
from bm_spec import (art_box, art_decals, art_floor, box, cyl, ellipse, lathe, prism, side_from_column, sprite,
                     flat_rgb, vent)

LINE = (16, 56, 74)
Z_BED = 0.54
BEDS = [((-11.12, -10.03), (-1.80, -1.28), "L"), ((-11.12, -10.03), (-3.12, -2.60), "L"),
        ((-8.10, -6.98), (-1.80, -1.28), "R"), ((-8.10, -6.98), (-3.12, -2.60), "R")]
SCAN = (-7.35, -5.10)                                     # Plattformmitte im Bild


def floor(ctx):
    holes = []
    for (x0, x1), (y0, y1), _ in BEDS:
        holes.append(sbox(x0 - 0.03, y0 - 0.36, x1 + 0.03, y1 + 0.12))      # Bett mit Frontband
    holes.append(sbox(-8.25, -5.85, -6.45, -4.66))                         # Scanner
    holes.append(sbox(-10.9, -4.45, -10.3, -4.0))                          # Vent
    return art_floor(ctx, "floor_Medical", holes)


def side(ctx):
    # SO-Schraege, Mitte der Kante (-5,82,-4,82) -> (-5,27,-5,35); Band dort 0,86 hoch
    return side_from_column(ctx, "side_Medical", -5.545, -5.085, art_h=0.86, spread=0.03)


def bed(ctx, xs, ys_art, head):
    mx0, mx1 = xs
    k = ctx.k
    top = ctx.color("med_mattress_top", (41, 141, 192))
    mside = ctx.color("med_mattress_side", (33, 89, 165))
    frame = ctx.color("med_bed_frame", (82, 108, 112))
    rail = ctx.color("med_bed_rail", (156, 186, 214))
    leg = ctx.color("med_bed_leg", (110, 134, 137))
    pil = ctx.color("med_pillow", (219, 235, 247))
    pils = ctx.color("med_pillow_side", (205, 222, 240))
    y0w, y1w = ys_art[0] - k * Z_BED, ys_art[1] - k * Z_BED                  # Liegeflaeche in Weltlage
    parts = [box((mx0 + mx1) / 2, (y0w + y1w) / 2, mx1 - mx0, y1w - y0w, 0.37, Z_BED, mside, top=top, bevel=0.03, outline=LINE),
             box((mx0 + mx1) / 2, (y0w + y1w) / 2, mx1 - mx0 - 0.06, y1w - y0w - 0.04, 0.30, 0.37, frame, outline=LINE),
             box((mx0 + mx1) / 2, y0w + 0.02, mx1 - mx0 - 0.02, 0.04, 0.21, 0.25, rail, outline=LINE)]
    for lx in (mx0 + 0.08, mx1 - 0.08):
        for ly in (y0w + 0.06, y1w - 0.06):
            parts.append(cyl(lx, ly, 0.035, 0.0, 0.30, leg, seg=12, outline=LINE))
    px0, px1 = (mx0, mx0 + 0.32) if head == "L" else (mx1 - 0.32, mx1)
    parts.append(box((px0 + px1) / 2, (y0w + y1w) / 2 + 0.01, px1 - px0 - 0.02, y1w - y0w - 0.06, Z_BED, Z_BED + 0.12, pils,
                     top=pil, bevel=0.02, outline=LINE))
    return parts


def props(ctx):
    parts = []
    for xs, ys, head in BEDS:
        parts += bed(ctx, xs, ys, head)
    # gefaltetes Tuch auf dem Bett oben links
    import numpy as np
    parts += art_decals(ctx, "med_towel", (-10.62, -1.78, -10.0, -1.33), Z_BED,
                        lambda a, wx, wy: (a.sum(-1) / 3 > 150) | (np.abs(a - [16, 56, 74]).sum(-1) < 40) & (wx > -10.58),
                        thick=0.02)
    # Scanner (Sockel, Leuchtring, vier flache Sensor-Pods) und Probenkonsole "Inspect Sample" (Schrank, Monitor,
    # Glaszylinder mit Proben), beide echte Koerper (User 18.10.: Scanner deformiert, Flaschen-Task fehlte)
    k = ctx.k
    zp = 0.36
    cx, cy = SCAN[0], SCAN[1] - k * zp
    from bm_models import sample_console, scanner
    parts += scanner(ctx, "med_scan", cx, cy, r=0.62, rgb=(176, 207, 211), side_rgb=(99, 153, 162))
    # Probenkonsole steht an der Ostwand: Front nach Westen in den Raum (Meldung 19.10. "falsch ausgerichtet")
    parts += sample_console(ctx, "med_sample", -6.05, -4.55, yaw=270.0, rgb=(128, 170, 178), dark=(70, 110, 120))
    parts += vent(ctx, "Medical/Ground/MedVent")
    return parts
