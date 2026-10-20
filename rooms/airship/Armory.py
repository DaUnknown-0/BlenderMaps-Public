# Airship / Armory - am Kartenfoto gemessen.
#
# Boden: Dielen oben, violetter Teppich unten (Zeichnung). Zickzack-Waende mit Waffenhalterungen (Zeichnung).
# Zwei Vitrinen (armory_table): Unterschrank (60,66,79) mit Schubladen, Glasaufsatz (209,224,225), Gewehre auf Haltern
#   darin, Hoehe 0,7 (3D, 19.10.).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box                                                # noqa: E402
from bm_models import display_case                                                # noqa: E402

TABLES = [(-11.48, -4.51, -9.92, -3.70), (-11.47, -9.40, -9.91, -8.60)]
Z_T = 0.7


def floor(ctx):
    return art_floor(ctx, "floor_Armory", holes=[sbox(x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02) for x0, y0, x1, y1 in TABLES])


def props(ctx):
    parts = []
    for i, (x0, y0, x1, y1) in enumerate(TABLES):
        cy, d = (y0 + y1) / 2 - ctx.k * Z_T * 0.5, (y1 - y0) * 0.8
        parts += display_case(ctx, f"arm_case{i}", x0, cy - d / 2, x1, cy + d / 2, h=Z_T, seed=i)
    return parts
