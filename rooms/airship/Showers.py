# Airship / Showers - am Kartenfoto gemessen. Duschkabinen: Wandzeichnung. Drei Holzbaenke (shower_bench1/2,
# showers_bench3) als Lattenbaenke mit Beinen, Hoehe 0,45 (3D, 19.10.); Handtuecher bleiben Bodenzeichnung.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, sprite, vent                                  # noqa: E402
from bm_models import bench                                                       # noqa: E402

BENCHES = ["Showers/shower_bench1", "Showers/shower_bench2", "Showers/showers_bench3"]


def floor(ctx):
    holes = []
    for suf in BENCHES:
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        holes.append(sbox(x0, y0, x1, y1))
    return art_floor(ctx, "floor_Showers", holes=holes)


def props(ctx):
    parts = []
    k = ctx.k
    for i, suf in enumerate(BENCHES):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        cy, d = (y0 + y1) / 2 - k * 0.22, max(0.3, (y1 - y0) * 0.8)
        parts += bench(ctx, f"sh_bench{i}", x0, cy - d / 2, x1, cy + d / 2, h=0.45, rgb=(140, 101, 87), leg_rgb=(123, 85, 74),
                       slats=3 if d < 0.6 else 5)
    parts += vent(ctx, "Showers/ShowersVent")
    return parts
