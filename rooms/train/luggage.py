# Polaris Express / luggage: Boden "planks", Waende "wood" (rooms/train/_common.py).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import _common as C                                                             # noqa: E402

OUTER = (1.0, 5.5)


def floor(ctx):
    return C.floor_tile(ctx, "tfloor_luggage", "planks")


def _is_outer(e):
    (ax, ay), (bx, by) = e["a"], e["b"]
    my = (ay + by) / 2
    return any(abs(my - yy) < 0.12 for yy in OUTER) and abs(ay - by) < 0.05


def side(ctx):
    return C.wall_tile(ctx, "twall_luggage_plain", "wood", window=False)


def side_for(ctx, e):
    if False and _is_outer(e):
        return C.wall_tile(ctx, "twall_luggage_win", "wood", window=True, seed=3)
    return None


def north(ctx, e):
    if False and _is_outer(e):
        return C.wall_tile(ctx, "twall_luggage_win", "wood", window=True, seed=3)
    return C.wall_tile(ctx, "twall_luggage_plain", "wood", window=False)
