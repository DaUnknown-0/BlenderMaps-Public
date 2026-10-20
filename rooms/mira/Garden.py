# Mira HQ / Gewaechshaus (Garden) - am Kartenfoto gemessen (k 0,53).
# Alles als echte Koerper (User 18.10.): Pflanzkaesten mit Trog, Erde und Farnwedeln bzw. Buschkugeln (der Spieler
# laeuft im Spiel darueber, deshalb nur 0,26 hoch), Glastank mit Rippenrahmen und rosa Alienpflanze darin,
# Pflanzregal mit drei Topfpflanzen, fuenf Ranken an der Nordwand, Ausgabesaeule, Vent als Gitter.

from shapely.geometry import box as sbox

from bm_models import console_block, floor_console, planter, potted_plant, table, vent_grate, vine
from bm_spec import art_floor, cyl, lathe, tube, blob, sprite

H = 4.2
K = 0.53
PLANTERS = [(14.28, 15.84, 22.12, 22.92), (15.84, 17.40, 22.20, 23.00), (18.23, 19.79, 22.22, 23.02), (21.20, 22.76, 22.23, 23.03),
            (14.19, 15.63, 22.98, 23.96), (15.70, 17.14, 22.93, 23.91), (18.43, 19.88, 23.02, 24.00), (20.41, 21.86, 23.12, 24.10),
            (13.92, 15.48, 23.84, 24.64), (14.79, 16.24, 24.51, 25.49), (19.56, 21.12, 24.29, 25.09)]
FERNS = {0, 1, 2, 3, 8}
VINES = [(21.85, 7), (19.8, 11), (16.7, 13), (15.6, 17), (13.5, 19)]


def floor(ctx):
    holes = [sbox(x0, y0, x1, y1) for x0, x1, y0, y1 in PLANTERS] + [sbox(16.85, 24.0, 18.85, 26.8), sbox(19.8, 22.3, 21.2, 23.25)]
    return art_floor(ctx, "floor_Garden", holes)


def props(ctx):
    p = []
    for i, (x0, x1, y0, y1) in enumerate(PLANTERS):
        p += planter(ctx, f"gar_planter{i}", x0, y0, x1, y1 - K * 0.26, h=0.26, kind="fern" if i in FERNS else "bush", seed=i)
    # Glastank: Sockel, acht Rippen, oberer Ring, Alienpflanze (rosa Stamm, Knollen, Tentakel) innen
    cx, cy = 17.85, 24.45
    base = ctx.color("gar_tank_base", (178, 187, 203))
    rib = ctx.color("gar_tank_rib", (96, 121, 149))
    glass = ctx.glow("gar_tank_glass", (170, 210, 235), 0.5)
    p.append(cyl(cx, cy, 0.95, 0.0, 0.5, base, seg=48, outline=(53, 58, 77)))
    p.append(cyl(cx, cy, 0.84, 0.5, 0.56, rib, seg=48))
    import math
    for i in range(8):
        a = math.radians(i * 45)
        rx, ry = cx + math.cos(a) * 0.82, cy + math.sin(a) * 0.82
        p.append(tube([(rx, ry, 0.5), (rx, ry, 3.3)], 0.035, rib, seg=8, outline=(53, 58, 77)))
    for z in (1.4, 2.3):
        ring = [(cx + math.cos(math.radians(a)) * 0.82, cy + math.sin(math.radians(a)) * 0.82, z) for a in range(0, 361, 15)]
        p.append(tube(ring, 0.02, glass, seg=6))
    p.append(lathe(cx, cy, [(0.84, 3.3), (0.86, 3.3), (0.86, 3.42), (0.4, 3.55), (0.0, 3.58)], rib, seg=48, outline=(53, 58, 77)))
    stem = ctx.color("gar_alien_stem", (170, 70, 120))
    bulb = (ctx.color("gar_alien_light", (235, 130, 190)), ctx.color("gar_alien_dark", (160, 60, 120)))
    p.append(cyl(cx, cy, 0.5, 0.56, 0.7, ctx.color("gar_tank_soil", (70, 50, 60)), seg=32))
    p.append(tube([(cx, cy, 0.7), (cx + 0.1, cy + 0.05, 1.6), (cx - 0.05, cy, 2.5)], 0.08, stem, seg=10))
    for i, (dx, dy, z, r) in enumerate(((0.0, 0.0, 2.65, 0.3), (0.35, 0.1, 1.9, 0.22), (-0.3, -0.1, 1.5, 0.2), (0.1, 0.3, 2.2, 0.18))):
        p.append(blob(cx + dx, cy + dy, z, r, r, r * 0.9, bulb, seed=30 + i, seg=12, rings=7, outline=(90, 30, 60)))
    for i in range(5):
        a = math.radians(i * 72 + 20)
        p.append(tube([(cx, cy, 2.4), (cx + math.cos(a) * 0.45, cy + math.sin(a) * 0.45, 2.0 + 0.2 * (i % 2)),
                       (cx + math.cos(a) * 0.6, cy + math.sin(a) * 0.6, 1.3)], 0.03, stem, seg=6))
    # Konsolen am Tanksockel (Filter, O2)
    p += console_block(ctx, "gar_filter", 17.02, 23.52, 17.42, 23.72, 0.45, rgb=(120, 130, 150), screens=1, lights=False)
    p += console_block(ctx, "gar_o2", 17.70, 23.52, 18.02, 23.72, 0.45, rgb=(120, 130, 150), screens=1, lights=False)
    # Pflanzregal mit Toepfen
    p += table(ctx, "gar_pots", 19.85, 22.36, 21.12, 23.0, h=0.36, top_rgb=(120, 110, 100), leg_rgb=(80, 72, 66))
    for i, (x, flower, leaf) in enumerate(((20.08, (245, 245, 245), (40, 120, 40)), (20.48, (220, 60, 60), (30, 100, 40)),
                                           (20.88, (70, 130, 230), (50, 130, 50)))):
        p += potted_plant(ctx, f"gar_pot{i}", x, 22.68, z0=0.36, r=0.09, h=0.4, leaf_rgb=leaf, flower=flower, seed=i)
    # Ranken an der Nordwand (Wand bei y 29,3), von der Decke herab
    for i, (x, seed) in enumerate(VINES):
        p += vine(ctx, f"gar_vine{i}", x, 29.3, H - 0.3, 3.0, seed=seed)
    # Ausgabesaeule
    p += floor_console(ctx, "gar_stand", 13.85, 22.65, 0.56, 0.4, 1.25, body_rgb=(150, 160, 175), slope=False, screen_rgb=(120, 200, 220))
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "Garden/AgriVent")
    p += vent_grate(ctx, "gar_vent", vx0, vy0, vx1, vy1)
    return p
