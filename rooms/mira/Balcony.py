# Mira HQ / Balkon (Balcony) - Aussenbereich: Satellitenschuessel (Fuss, Mast, Schirm, Arm), Waffenkonsole mit
# Schraege und Schirm, Wetterautomat (Korpus, Fenster, Anzeigen), Gelaender, Vent als Gitter.

from shapely.geometry import box as sbox

from bm_models import floor_console, vending_machine, vent_grate
from bm_spec import art_floor, cyl, lathe, railing, sprite, tube

SKY = True                                              # Aussenbereich: keine Decke
K = 0.53


def floor(ctx):
    return art_floor(ctx, "floor_Balcony", [sbox(17.7, -3.55, 20.0, -0.85), sbox(28.45, -2.75, 29.2, -1.05)])


def props(ctx):
    k = K
    p = []
    grey = ctx.color("bal_dish", (166, 178, 190))
    dark = ctx.color("bal_dish_dark", (100, 112, 126))
    # Schuessel in der Suedwestecke, Fuss r 0,5 und Schirm r 0,62 (Meldung 18.10. #104)
    cx, cy = 18.35, -3.2
    p.append(cyl(cx, cy, 0.5, 0.0, 0.24, grey, seg=40, outline=(40, 46, 56)))
    p.append(cyl(cx, cy, 0.2, 0.24, 0.8, dark, seg=20, outline=(40, 46, 56)))
    prof = [(0.0, 0.0)] + [(0.62 * t, 0.3 * t * t) for t in (0.2, 0.4, 0.6, 0.8, 1.0)] + [(0.6, 0.32), (0.0, 0.05)]
    p.append(lathe(cx - 0.1, cy + 0.2, [(r, z + 0.78) for r, z in prof], grey, seg=32, outline=(40, 46, 56), tilt=(42, 0, 0.78)))
    p.append(tube([(cx - 0.25, cy + 0.35, 0.95), (cx - 0.6, cy + 0.5, 1.45)], 0.025, dark, outline=(40, 46, 56)))
    p += floor_console(ctx, "bal_console", 19.22, -2.48, 0.69, 0.34, 0.72, body_rgb=(90, 100, 110), screen_rgb=(120, 200, 150))
    p += vending_machine(ctx, "bal_weather", 28.50, -2.70, 29.17, -2.20, h=(-1.60 + 2.70) / k, rgb=(120, 130, 140), dark=(50, 56, 64),
                         glass=(90, 140, 190), rows=3, seed=7)
    fence = ctx.color("bal_fence", (102, 103, 113))
    p += railing([(17.86, -3.70 - k * 0.6), (20.45, -3.70 - k * 0.6)], 0.6, fence, r=0.03, outline=(40, 40, 48))
    p += railing([(20.35, -2.70 - k * 0.6), (29.26, -2.70 - k * 0.6)], 0.6, fence, r=0.03, outline=(40, 40, 48))
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "Cafe/BalconyVent")
    p += vent_grate(ctx, "bal_vent", vx0, vy0, vx1, vy1)
    return p
