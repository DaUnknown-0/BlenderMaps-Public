# Polus / BoilerRoom (Kesselraum unter O2) - am Kartenfoto gemessen.
#
# Boden: Zeichnung (blaugraue Fliesen, zwei Wasserrinnen mit Gitter). Nordwand: dunkelgruen mit Rohren (Zeichnung).
# Rohre mit Ventilraedern (Sprites pipe1/pipe2): Rohr (71,55,54)/(90,80,74), Rad (165,142,132), Kontur schwarz.
#   Links Knierohr aus der Wand in die Rinne, Rad Bild (0,85 | -24,15); rechts senkrechtes Rohr x 3,5..4,15, Rad
#   Bild (3,75 | -24,10).
# Boiler weiss (172,192,194)/(120,147,163), Wasserkanister (46,165,217) (Sprite panel_waterjug).

import math
from shapely.geometry import box as sbox
from bm_spec import art_floor, box, cyl, lathe, tube


def floor(ctx):
    return art_floor(ctx, "floor_BoilerRoom", holes=[sbox(0.30, -23.55, 0.82, -22.55), sbox(0.95, -23.42, 1.32, -22.8),
                                                    sbox(0.28, -25.0, 1.30, -23.85), sbox(3.45, -24.95, 4.20, -23.65)])


def wheel(ctx, cx, cy, cz, r=0.26):
    rim = ctx.color("boil_wheel", (165, 142, 132))
    out = [lathe(cx, cy, [(r - 0.04, cz - 0.025), (r, cz - 0.025), (r, cz + 0.025), (r - 0.04, cz + 0.025),
                          (r - 0.04, cz - 0.025)], rim, seg=32, outline=(0, 0, 0))]
    for i in range(8):
        a = math.radians(i * 45)
        out.append(tube([(cx, cy, cz), (cx + (r + 0.06) * math.cos(a), cy + (r + 0.06) * math.sin(a), cz)], 0.022, rim, seg=6))
    out.append(cyl(cx, cy, 0.06, cz - 0.04, cz + 0.05, rim, seg=16, outline=(0, 0, 0)))
    return out


def props(ctx):
    parts = []
    pipe = ctx.color("boil_pipe", (71, 55, 54))
    pipel = ctx.color("boil_pipe_light", (90, 80, 74))
    # links: Knierohr aus der Westwand in die Rinne
    parts.append(tube([(0.28, -24.55, 0.42), (0.75, -24.55, 0.42), (0.92, -24.55, 0.28), (0.95, -24.55, -0.2)], 0.17, pipe,
                      seg=16, outline=(0, 0, 0)))
    parts.append(cyl(0.95, -24.55, 0.2, 0.0, 0.08, pipel, seg=20, outline=(0, 0, 0)))
    parts.append(cyl(0.88, -24.55, 0.05, 0.42, 0.72, pipel, seg=10))
    parts += wheel(ctx, 0.88, -24.55, 0.74)
    # rechts: senkrechtes Rohr aus der Rinne
    parts.append(cyl(3.82, -24.45, 0.32, -0.2, 0.62, pipe, top=pipel, seg=32, bevel=0.03, outline=(0, 0, 0)))
    parts.append(cyl(3.82, -24.45, 0.05, 0.62, 0.80, pipel, seg=10))
    parts += wheel(ctx, 3.82, -24.45, 0.82)
    # Boiler und Wasserkanister an der Nordwand
    wb = ctx.color("boil_tank", (172, 192, 194))
    wd = ctx.color("boil_tank_dark", (120, 147, 163))
    blk = ctx.color("boil_tank_cap", (33, 28, 24))
    parts.append(cyl(0.55, -23.30, 0.25, 0.0, 0.95, wd, top=wb, seg=28, bevel=0.03, outline=(20, 24, 28)))
    parts.append(cyl(0.48, -23.30, 0.08, 0.95, 1.15, blk, seg=12))
    jug = ctx.color("boil_jug", (46, 165, 217))
    jugd = ctx.color("boil_jug_dark", (90, 143, 181))
    parts.append(box(1.13, -23.22, 0.34, 0.26, 0.0, 0.32, ctx.color("boil_jug_stand", (60, 64, 70)), outline=(10, 10, 12)))
    parts.append(lathe(1.13, -23.22, [(0.0, 0.32), (0.15, 0.32), (0.16, 0.36), (0.16, 0.68), (0.10, 0.75), (0.05, 0.77),
                                      (0.05, 0.82), (0.0, 0.82)], jug, seg=24, outline=(10, 40, 70)))
    parts.append(cyl(1.13, -23.22, 0.162, 0.44, 0.48, jugd, seg=24))
    return parts
