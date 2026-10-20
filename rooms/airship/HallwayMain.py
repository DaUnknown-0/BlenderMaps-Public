# Airship / Main Hall mit Nischen - am Kartenfoto gemessen. Betten in drei Nischen (Decke rot (211,86,87), Kissen
# (201,215,222), Gestell (156,143,132)), Truhe (task_bigolchest) mit Deckel und Baendern (3D, 19.10.), Leiter nach Electrical (ladder_electrical,
# x 12,87, Band 1,665) an der Suedwand.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import ladder                                                        # noqa: E402
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, sprite, vent                                  # noqa: E402
from bm_models import chest                                                       # noqa: E402

BEDS = [(4.72, 5.42, 2.95, 4.20, "N"), (7.50, 8.40, -4.20, -2.95, "S"), (13.60, 14.50, -4.20, -2.95, "S")]


def floor(ctx):
    holes = [sbox(x0, y0, x1, y1) for x0, x1, y0, y1, d in BEDS] + [sbox(6.2, 3.25, 6.95, 3.95)]
    return art_floor(ctx, "floor_HallwayMain", holes=holes)


def props(ctx):
    parts = []
    frame = ctx.color("hm_bed_frame", (156, 143, 132))
    blanket = ctx.color("hm_bed_blanket", (211, 86, 87))
    pillow = ctx.color("hm_bed_pillow", (201, 215, 222))
    for x0, x1, y0, y1, d in BEDS:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        parts.append(box(cx, cy, x1 - x0, y1 - y0, 0.0, 0.32, frame, outline=(41, 48, 49)))
        parts.append(box(cx, cy, x1 - x0 - 0.04, y1 - y0 - 0.04, 0.32, 0.44, blanket, bevel=0.02, outline=(90, 30, 30)))
        py = y1 - 0.18 if d == "N" else y0 + 0.18
        parts.append(box(cx, py, x1 - x0 - 0.12, 0.26, 0.44, 0.52, pillow, bevel=0.03, outline=(90, 100, 110)))
    _, (x0, y0, x1, y1) = sprite(ctx, "HallwayMain/task_bigolchest")
    parts += chest(ctx, "hm_chest", (x0 + x1) / 2, y0 + 0.22, x1 - x0, 0.44, 0.5, facing="S")
    for v in ("HallwayMain/HallwayVent1", "HallwayMain/HallwayVent2"):
        parts += vent(ctx, v)
    return parts
