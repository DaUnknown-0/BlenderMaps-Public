# Polus / Storage - am Kartenfoto gemessen (Zoom 3,2: x = 17,1 + px/166, y = -9,9 - py/166).
#
# Boden: dunkle Dielen (Zeichnung); Kisten- und Fassflaechen haengen im Wand-Collider und werden in _map.py
#   (FLOOR_ADD_ROOMS) zu Boden. Regal an der Nordwand bleibt Wandzeichnung.
# Kisten wie Skeld (Seite (63,97,90), Deckel (90,130,112), Kontur (24,36,33)): (Mitte x, Frontunterkante y, Kante,
#   Drehung, Hoehe). Faesser (71,108,126) mit roter Banderole, Benzinkanister (198,44,78) (Sprite panel_gascan).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, barrel, box, crate, vent                           # noqa: E402

CRATES = [(20.70, -11.29, 0.82, 0, 1.00), (22.19, -10.86, 0.70, 25, 0.70), (22.30, -11.77, 0.75, 30, 0.75),
          (21.56, -10.92, 0.60, 20, 0.60), (22.28, -13.03, 0.65, 25, 0.55), (17.93, -13.03, 0.90, 10, 0.85),
          (19.42, -12.90, 0.70, 5, 0.30)]   # flache Kiste rechts neben dem Fass (Fehlerrunde 19.10.)
BARRELS = [(21.25, -11.35, 0.24, 0.75), (21.66, -11.60, 0.25, 0.75), (18.79, -12.61, 0.24, 0.70)]


def floor(ctx):
    holes = [sbox(x - s * 0.7, yb - 0.02, x + s * 0.7, yb + s + h * 0.8) for x, yb, s, rot, h in CRATES]
    holes += [sbox(x - r - 0.02, yb - 0.02, x + r + 0.02, yb + 2 * r + h * 0.8) for x, yb, r, h in BARRELS]
    holes.append(sbox(20.9, -11.55, 21.3, -11.05))
    return art_floor(ctx, "floor_Storage", holes=holes)


def props(ctx):
    parts = []
    from bm_models import au_crate, shelf_unit
    for i, (x, yb, s, rot, h) in enumerate(CRATES):
        # Kisten als gegliederte Koerper (Deckel, Kantenleisten, Griffmulden) statt glatter Quader (#257..#259)
        parts += au_crate(ctx, "polus_crate", x, yb + s / 2, s, rot, h)
    # Werkzeugregal an der Nordwand (Zeichnung 18,3..19,85 / -10,15..-10,85, Boden per _map FLOOR_ADD_ROOMS)
    parts += shelf_unit(ctx, "st_shelf", 18.35, -10.72, 19.85, -10.35, h=1.25, boards=3, rgb=(150, 110, 70), facing="S", seed=5,
                        item_colors=((190, 60, 60), (120, 130, 140), (200, 170, 90), (80, 90, 100)))
    for x, yb, r, h in BARRELS:
        parts += barrel(ctx, x, yb + r, r, h, prefix="polus_barrel")
    can = ctx.color("st_gascan", (198, 44, 78))
    parts.append(box(21.10, -11.38, 0.30, 0.18, 0.0, 0.40, can, bevel=0.03, outline=(40, 12, 20)))
    parts.append(box(21.10, -11.38, 0.12, 0.10, 0.40, 0.46, ctx.color("st_gascan_cap", (40, 40, 44))))
    parts.append(box(21.02, -11.38, 0.05, 0.16, 0.40, 0.44, can))
    parts += vent(ctx, "Storage/StorageVent")
    return parts
