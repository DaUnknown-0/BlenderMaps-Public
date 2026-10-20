# Skeld / Life Support (O2) - am Kartenfoto gemessen.
# Sauerstofftank (LifeSuppTank): Sockel (126,166,165) r 0,46 bis 0,35, Glas (124,174,194) bis 1,15 mit Zeichnung als
# Mantel, Deckelring. Eimer (124,174,194)/(30,41,41). Filterkonsole + Behaelter an der Westschraege. Drei
# Luftereinheiten (126,166,165) an der Suedwand mit Gittern (Zeichnung als Oberseite), Pflanzkaesten dazwischen.

from shapely.geometry import Polygon, box as sbox

import bm_tex as T
from bm_spec import art_block, art_box, art_floor, cyl, prism

LINE = (0, 0, 0)


def floor(ctx):
    holes = [sbox(6.25, -3.1, 7.25, -1.65), sbox(6.95, -2.3, 7.55, -1.6), sbox(4.05, -5.2, 7.7, -4.15), sbox(4.9, -3.4, 6.0, -2.55)]
    return art_floor(ctx, "floor_LifeSupport", holes)


def props(ctx):
    k = ctx.k
    parts = []
    base = ctx.color("o2_base", (126, 166, 165))
    glass = ctx.color("o2_glass", (124, 174, 194))
    cx, cy = 6.75, -2.80 + 0.18                               # Fuss des Tanks (Bild-Unterkante + Radius*Stauchung)
    # Sauerstofftank: Sockel, Glaszylinder mit Rippen, Haube, Rohre (echter Koerper)
    from bm_models import tank, console_block, planter, fan_unit
    parts.append(cyl(cx, cy, 0.46, 0.0, 0.35, base, seg=48, outline=LINE))
    parts += tank(ctx, "o2_tank", cx, cy, 0.42, 0.9, z0=0.35, rgb=(124, 174, 194), band_rgb=(84, 120, 134), glass=(190, 235, 245), pipes=2)
    bin_ = ctx.color("o2_bin", (124, 174, 194))
    parts.append(cyl(7.25, -1.95 - k * 0.5, 0.22, 0.0, 0.5, bin_, top=ctx.color("o2_bin_in", (30, 41, 41)), seg=32, outline=LINE))
    # Filterkonsole hinter ihrer Laufkante (5,57 | -3,40 -> 6,08 | -2,98), vorher um k*h in den Laufbereich verschoben
    parts += console_block(ctx, "o2_filter", 5.50, -3.37, 5.98, -2.85, 0.55, rgb=(49, 65, 66), screens=1, seed=4)
    parts.append(cyl(5.20, -2.95 - k * 0.45, 0.24, 0.0, 0.45, base, seg=32, outline=LINE))
    # Luefterschraenke und Pflanzkaesten an der Suedwand (Boden endet bei -5,20). Meldungen 18.10.: die Schraenke
    # zeigten zum Raum hin eine leere Flaeche (Zeichnung lag nur auf der Oberseite), und zwischen ihnen stand man mitten
    # in den Pflanzkaesten (Collider dort erst bei -5,13). Jetzt: Schrank bis zum Collider (-4,30), beide gezeichneten
    # Gitter auf der Raumseite (front_both), Hoehe 0,95; Pflanzkaesten flach an der Wand mit der Zeichnung als Front.
    r = ctx.ref
    # Grundflaechen = Collider (abgeschraegte Nordecken, Luecken zwischen den Schraenken bis -5,13 begehbar); die
    # Kaesten waren breiter und man stand in der Luecke im Schrank (Meldung 18.10.)
    fans = [(4.12, 4.80, [(4.12, -5.20), (4.83, -5.20), (4.83, -4.40), (4.68, -4.26), (4.12, -4.26)]),
            (5.52, 6.20, [(5.57, -5.20), (6.24, -5.20), (6.24, -4.42), (6.11, -4.27), (5.75, -4.27), (5.57, -4.43)]),
            (6.92, 7.62, [(7.03, -5.20), (7.62, -5.20), (7.62, -4.25), (7.19, -4.25), (7.03, -4.50)])]
    for x0, x1, pts in fans:
        nm = f"o2_fan_{int(x0 * 10)}"
        # Luefterschrank: Korpus auf dem Collider, zwei Luefter in der Nordseite (zum Raum), Gitterstege
        p = prism(Polygon(pts), 0.0, 0.95, ctx.color(nm + "_side", (104, 138, 137)), top=ctx.color(nm + "_top", (126, 166, 165)),
                  bevel=0.015, outline=LINE)
        parts.append(p)
        yn = max(q[1] for q in pts)
        for fx in (x0 + 0.2, x1 - 0.2):
            parts += fan_unit(ctx, f"{nm}_fan{int(fx * 10)}", fx, yn + 0.03, 0.55, r=0.14, yaw=90.0, rgb=(60, 80, 80), blade_rgb=(30, 40, 40))
    for x0, x1 in ((4.80, 5.52), (6.20, 6.92)):
        nm = f"o2_plant_{int(x0 * 10)}"
        parts += planter(ctx, nm, x0 + 0.03, -5.20, x1 - 0.03, -4.90, h=0.3, kind="bush", trough_rgb=(74, 101, 107), seed=int(x0 * 10))
    return parts
