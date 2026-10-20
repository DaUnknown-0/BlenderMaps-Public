# Mira HQ / Laboratory - am Kartenfoto gemessen (k 0,53).
# Echte Koerper: Labortisch mit Mikroskop, Papieren und Probentablett (Sort Samples), L-Theke rechts mit Schubladen
# und Kolben, niedrige Bank unten, Vent als Gitter.

from shapely.geometry import box as sbox

from bm_models import bench, lab_bench, microscope, table, vent_grate
from bm_spec import art_floor, box, cyl, lathe, sprite

SIDE = (226, 232, 234)
K = 0.53
# Nordwand = Theken + Glasschraenke, gezeichnet 1,25 hoch (Kante 14,15 bis Wandkrone 15,40) -> Raumhoehe 1,25 / k
BAND_H = 1.25
H = 2.36


def floor(ctx):
    return art_floor(ctx, "floor_Laboratory", [sbox(8.1, 10.55, 10.6, 11.8), sbox(9.8, 12.4, 12.15, 13.45), sbox(11.25, 10.45, 12.15, 12.6),
                                                 sbox(7.85, 9.6, 11.7, 9.95)])


def props(ctx):
    p = []
    zt = (10.82 - 10.60) / K
    p += table(ctx, "lab_table", 8.13, 10.60, 10.53, 11.52, h=zt, top_rgb=(236, 240, 242), leg_rgb=(200, 206, 210))
    p += microscope(ctx, "lab_micro", 8.5, 11.15, zt)
    paper = ctx.color("lab_paper", (246, 246, 240))
    p.append(box(8.95, 10.85, 0.24, 0.3, zt, zt + 0.008, paper, rot=6))
    # Probentablett (Sort Samples): Wanne, vier Proben in Glaeschen
    tray = ctx.color("lab_tray", (120, 128, 136))
    glass = ctx.glow("lab_glass", (190, 230, 240), 0.8)
    p.append(box(9.66, 11.1, 1.3, 0.42, zt, zt + 0.04, tray, bevel=0.01, outline=(60, 66, 72)))
    for i, col in enumerate(((120, 230, 140), (230, 120, 120), (120, 160, 240), (230, 220, 120))):
        x = 9.2 + i * 0.3
        p.append(cyl(x, 11.1, 0.045, zt + 0.04, zt + 0.16, glass, seg=12))
        p.append(cyl(x, 11.1, 0.04, zt + 0.04, zt + 0.1, ctx.glow(f"lab_sample{i}", col, 1.6), seg=12))
    # L-Theke: oberer Riegel und rechte Saeule
    p += lab_bench(ctx, "lab_right_top", 9.81, 12.45, 11.25, 13.16, h=(12.68 - 12.45) / K, rgb=SIDE, items=False)
    p += lab_bench(ctx, "lab_right_col", 11.30, 10.50, 12.10, 12.28, h=(10.72 - 10.50) / K, rgb=SIDE, items=True, seed=2)
    p.append(lathe(10.3, 12.8, [(0.0, 0.43), (0.08, 0.43), (0.03, 0.56), (0.03, 0.62), (0.0, 0.62)], glass, seg=14))
    p += bench(ctx, "lab_bottom", 7.90, 9.65, 11.64, 9.77, h=(9.76 - 9.65) / K, rgb=(200, 206, 210), leg_rgb=(150, 156, 160))
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "Laboratory/LabVent")
    p += vent_grate(ctx, "lab_vent", vx0, vy0, vx1, vy1)
    return p
