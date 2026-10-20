# Mira HQ / Cafeteria - am Kartenfoto gemessen (k 0,53).
# Echte Koerper: zwei lange Tische mit Beinen, Baenke mit Latten, Laptop und Papiere/Becher auf den Tischen, Notfall-
# knopf, drei Verkaufsautomaten (Korpus, Fenster mit Produktreihen, Tastenfeld, Ausgabe), Regal an der Ostwand.

from shapely.geometry import box as sbox

from bm_models import bench, laptop, shelf_unit, table, vending_machine
from bm_spec import art_floor, box, lathe

LINE = (97, 35, 11)
Z_TOP, Z_BENCH = 0.42, 0.26
K = 0.53


def floor(ctx):
    holes = [sbox(23.1, 0.75, 25.0, 3.9), sbox(25.95, 0.75, 27.85, 3.9), sbox(27.0, 5.1, 28.8, 6.2), sbox(28.7, 0.9, 29.2, 5.25)]
    return art_floor(ctx, "floor_Cafe", holes)


BAND_HOLES = [sbox(27.0, 5.1, 28.8, 6.25)]


def props(ctx):
    p = []
    for (tx0, tx1), (bl, br) in (((23.42, 24.66), ((23.16, 23.38), (24.70, 24.92))), ((26.25, 27.55), ((25.98, 26.20), (27.58, 27.82)))):
        p += table(ctx, f"mcafe_table{int(tx0)}", tx0, 0.95 - K * Z_TOP, tx1, 3.80 - K * Z_TOP, h=Z_TOP, top_rgb=(239, 154, 112),
                   leg_rgb=(139, 137, 136))
        for bx0, bx1 in (bl, br):
            p += bench(ctx, f"mcafe_bench{int(bx0 * 10)}", bx0, 1.05 - K * Z_BENCH, bx1, 3.75 - K * Z_BENCH, h=Z_BENCH, rgb=(180, 99, 68),
                       leg_rgb=(139, 137, 136), slats=3)
    # Kleinkram: Laptop auf Tisch 1, Papiere und Becher auf Tisch 2
    p += laptop(ctx, "mcafe_laptop", 24.33, 3.1 - K * Z_TOP, Z_TOP, yaw=-15.0, w=0.3)
    paper = ctx.color("mcafe_paper", (236, 232, 220))
    cup = ctx.color("mcafe_cup", (200, 60, 60))
    p.append(box(26.55, 1.6 - K * Z_TOP, 0.22, 0.28, Z_TOP, Z_TOP + 0.008, paper, rot=8))
    p.append(box(26.7, 1.75 - K * Z_TOP, 0.2, 0.26, Z_TOP + 0.008, Z_TOP + 0.016, paper, rot=-5))
    p.append(lathe(26.45, 1.95 - K * Z_TOP, [(0.0, Z_TOP), (0.035, Z_TOP), (0.04, Z_TOP + 0.09), (0.0, Z_TOP + 0.09)], cup, seg=12, outline=LINE))
    frame = ctx.color("mcafe_em_frame", (60, 62, 70))
    dome = ctx.color("mcafe_em_dome", (232, 120, 150))
    ex, ey = 24.045, 1.665 - K * (Z_TOP + 0.08)
    p.append(box(ex, ey, 0.42, 0.34, Z_TOP, Z_TOP + 0.08, frame, bevel=0.01, outline=(20, 20, 24)))
    p.append(lathe(ex, ey, [(0.0, Z_TOP + 0.08), (0.1, Z_TOP + 0.08), (0.095, Z_TOP + 0.11), (0.06, Z_TOP + 0.15), (0.0, Z_TOP + 0.16)],
                   dome, seg=28, outline=(20, 20, 24)))
    # Automaten an der Nordwand (Fronten nach Sueden), schmaler Automat und Regal an der Ostwand
    p += vending_machine(ctx, "mcafe_vend", 27.07, 5.19, 27.91, 5.75, h=(6.12 - 5.19) / K, rgb=(222, 218, 209), dark=(46, 47, 44), rows=4, seed=1)
    p += vending_machine(ctx, "mcafe_snack", 28.09, 5.20, 28.74, 5.75, h=(6.12 - 5.20) / K, rgb=(46, 47, 44), dark=(30, 30, 28),
                         glass=(90, 120, 170), rows=5, seed=2, products=((240, 200, 60), (230, 90, 60), (90, 170, 230), (240, 240, 240)))
    p += vending_machine(ctx, "mcafe_vend_e", 28.73, 4.25, 29.14, 4.75, h=(5.05 - 4.25) / K, rgb=(46, 47, 44), dark=(24, 24, 22),
                         glass=(120, 150, 200), rows=3, seed=3)
    p += shelf_unit(ctx, "mcafe_shelf", 28.78, 0.96 - K * 0.9, 29.16, 3.80 - K * 0.9, h=0.9, boards=3, rgb=(159, 167, 184), facing="W", seed=4)
    return p
