# Airship / Kitchen - am Kartenfoto gemessen.
#
# Boden weisse Fliesen (228,243,247) mit Punkten (Zeichnung). Arbeitsinseln (kitchen_table1 Herd + Schneidbrett,
#   kitchen_table2 Spuele + Herd): Kuechenzeile mit Schubladen, Kochfeld, Pfanne, Becken, Hahn; Korpus (123,142,148),
#   Hoehe 0,75. Regal an der Westwand (kitchen_shelf) mit roten Flaschen, Front nach Osten (3D, 19.10.).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, sprite, vent                                  # noqa: E402
from bm_models import kitchen_counter, shelf_unit                                  # noqa: E402

Z_T = 0.75


def floor(ctx):
    holes = []
    for suf in ("Kitchen/kitchen_table1", "Kitchen/kitchen_table2"):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        holes.append(sbox(x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02))
    return art_floor(ctx, "floor_Kitchen", holes=holes)


def props(ctx):
    parts = []
    for i, (suf, stove, sink, board) in enumerate((("Kitchen/kitchen_table1", "E", False, True),
                                                   ("Kitchen/kitchen_table2", "E", True, False))):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        cy = (y0 + y1) / 2 - ctx.k * Z_T * 0.5
        d = (y1 - y0) * 0.75
        parts += kitchen_counter(ctx, f"kit_counter{i}", x0, cy - d / 2, x1, cy + d / 2, h=Z_T, stove=stove, sink=sink, board=board, seed=i)
    _, (x0, y0, x1, y1) = sprite(ctx, "Kitchen/kitchen_shelf")
    parts += shelf_unit(ctx, "kit_shelf", x0, y0, x0 + 0.32, y1, h=1.3, boards=4, rgb=(123, 142, 148), facing="E", seed=7,
                        item_colors=((200, 40, 40), (220, 60, 60), (230, 230, 230), (170, 30, 30), (120, 70, 50)))
    parts += vent(ctx, "Kitchen/KitchenVent")
    return parts
