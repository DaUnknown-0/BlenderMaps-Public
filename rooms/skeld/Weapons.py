# Skeld / Weapons - am Kartenfoto gemessen (zoomgrid.py, bm_analyze.py, Raster 0,25).
# Aufbau wie im Spiel: Plankenplattform (begehbar, saubere Zeichnung) ueber einem Maschinendeck. Die dunklen Flaechen
#   mit Leitungen sind Gruben (0,6 tief): Nordwest (Tank + grosses Rohr, ausserhalb der Collider, wird dazugenommen),
#   Suedwest unter dem Westarm, Suedost unter dem Fenster. Kanten Plattform/Grube: Gelaender (143,60,60).
# Geschuetz: Sockel (140,170,173) r 0,62/0,45, vier Griffe (189,56,63), Schuetzensitz (38,55,85).
# Tank: Koerper (60,60,90)/(82,93,115), Kuppel mit roten Rippen (187,42,47), Bild x 7,02..7,62, Fuss 3,04, Kuppel 4,40.
# Rohre (110,51,79), Kontur (40,16,30), Breite im Bild ~0,6: Nordwest senkrecht bei x 7,3 vom Tank bis unter den
#   Westarm, Suedost von der Ostwand (11,7 / 1,2) nach Suedwesten und dann nach Sueden in den Grubenboden.

import math

from shapely.geometry import box as sbox

from bm_spec import art_floor, box, cyl, lathe, office_chair, pit_rails, tube, vent

D = 0.6
PITS = [
    {"poly": [(6.85, 1.55), (8.45, 1.55), (8.45, 3.66), (6.85, 3.66)], "d": D, "add": True, "cut": "floor",
     "wall": (52, 64, 72)},
    {"poly": [(6.5, -1.6), (8.77, -1.6), (8.77, 0.43), (6.5, 0.43)], "d": D, "wall": (52, 64, 72)},
    {"poly": [(10.12, -1.6), (12.2, -1.6), (12.2, 1.55), (10.12, 1.55)], "d": D, "wall": (52, 64, 72)},
]


def floor(ctx):
    return art_floor(ctx, "floor_Weapons", [sbox(8.35, 0.85, 9.75, 2.35)])


def props(ctx):
    k = ctx.k
    parts = []
    red = ctx.color("weap_rail", (143, 60, 60))
    parts += pit_rails(ctx, red, z_top=0.42)
    # Geschuetz
    base = ctx.color("weap_base", (140, 170, 173))
    inner = ctx.color("weap_base_in", (127, 159, 164))
    grip = ctx.color("weap_grip", (189, 56, 63))
    cx, cy = 9.05, 1.50 - k * 0.15
    parts.append(cyl(cx, cy, 0.62, 0.0, 0.08, base, seg=56, outline=(0, 0, 0)))
    parts.append(cyl(cx, cy, 0.45, 0.08, 0.18, inner, seg=48, outline=(0, 0, 0)))
    for dx, dy in ((-0.52, 0.0), (0.52, 0.0), (0.0, -0.40), (0.0, 0.40)):
        parts.append(box(cx + dx, cy + dy, 0.12, 0.12, 0.08, 0.30, grip, bevel=0.03, outline=(60, 16, 20)))
    parts += office_chair(ctx, "weap_seat", cx, cy, (38, 55, 85), (24, 37, 69), (0, 0, 0), back="W", w=0.42, seat_z=0.42,
                          back_top=0.85)
    # Tank in der Nordwestgrube
    tb = ctx.color("weap_tank", (70, 70, 102))
    tc = ctx.color("weap_tank_cap", (60, 60, 90))
    rib = ctx.color("weap_tank_rib", (187, 42, 47))
    tx, ty, tr = 7.32, 3.34, 0.30
    parts.append(lathe(tx, ty, [(0.0, -D), (tr, -D), (tr, 0.92), (tr * 0.97, 0.98)], tb, seg=40, outline=(0, 0, 0)))
    dome = [(tr * 0.97, 0.98)] + [(tr * 0.97 * math.cos(a), 0.98 + 0.28 * math.sin(a))
                                   for a in [i * math.pi / 2 / 8 for i in range(1, 9)]]
    parts.append(lathe(tx, ty, dome, tc, seg=40, outline=(0, 0, 0)))
    for i in range(5):                                                   # rote Rippen auf der Kuppel (Suedseite)
        a = math.radians(-150 + i * 30)
        rx, ry = tx + math.cos(a) * tr * 0.72, ty + math.sin(a) * tr * 0.72
        parts.append(box(rx, ry, 0.05, 0.05, 1.00, 1.18, rib, rot=math.degrees(a)))
    # Rohre
    pipe = ctx.color("weap_pipe", (110, 51, 79))
    line = (40, 16, 30)
    zc = -D + 0.28
    parts.append(tube([(7.32, 3.10, zc), (7.32, 1.90, zc), (7.28, 0.70, zc), (7.22, 0.20, zc - 0.05), (7.20, -0.05, -D)],
                      0.28, pipe, seg=20, outline=line))
    parts.append(tube([(7.58, 3.30, 0.30), (7.90, 3.30, 0.30), (7.92, 3.22, 0.05), (7.92, 3.18, -D)], 0.13, pipe, seg=16,
                      outline=line))
    parts.append(tube([(7.55, 2.55, zc + 0.05), (7.95, 2.45, zc + 0.05)], 0.12, pipe, seg=14, outline=line))
    parts.append(tube([(11.85, 1.28, zc + 0.10), (11.55, 1.10, zc), (11.15, 0.90, zc), (11.00, 0.55, zc), (11.10, 0.10, zc),
                       (11.40, -0.35, zc), (11.55, -0.90, zc - 0.05), (11.58, -1.15, -D)], 0.29, pipe, seg=20, outline=line))
    for x, y, z in ((11.05, 0.35, zc), (7.32, 2.30, zc), (7.30, 1.60, zc)):     # Flansche
        parts.append(tube([(x, y - 0.05, z), (x, y + 0.05, z)], 0.33, ctx.color("weap_flange", (90, 40, 66)), seg=20,
                          outline=line))
    parts += vent(ctx, "Weapons/WeaponsVent")
    return parts
