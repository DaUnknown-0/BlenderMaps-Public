# Airship / Gap Room, unterer Boden rechts (Leiter ladder_gap, Band 1,345). Boden = Zeichnung (10,46..14,25 /
# 5,57..6,30), unter der gezeichneten Stegfront fortgesetzt. Waende bis zur Hallendecke (6,1).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, vent                                               # noqa: E402
PROCEDURAL = True      # zeichnet Boden/Waende selbst (keine Spieltextur), bleibt bei bm_style aktiv

Z = -1.345
H = 6.1 + 1.345
FULL_WALLS = True


def floor(ctx):
    return art_floor(ctx, "floor_GapLower", holes=[sbox(9.5, 6.30, 15.2, 7.8)], period_x=None)


def side(ctx):
    return ctx.color("gaplow_side", (166, 98, 105))


def north(ctx, e):
    return ctx.color("gaplow_side", (166, 98, 105))


def props(ctx):
    return vent(ctx, "GapRoom/GaproomVent2")
