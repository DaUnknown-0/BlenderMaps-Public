# Airship / Leiterschacht Gap Room -> Meeting Room (ladder_meeting, x 4,54, Band 4,147). Schacht zwischen den
# Shadow-Fluchten x 3,87..5,19; schraege Schiffsleiter vom Steg (y 9,72, z 0) zum Meeting Room (y 13,84, z 4,147).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import ladder                                                        # noqa: E402
PROCEDURAL = True      # zeichnet Boden/Waende selbst (keine Spieltextur), bleibt bei bm_style aktiv

H = 4.147 + 1.39
FULL_WALLS = True


def side(ctx):
    return ctx.color("meetshaft_side", (166, 98, 105))


def north(ctx, e):
    return ctx.color("meetshaft_side", (166, 98, 105))


def props(ctx):
    return ladder(ctx, 4.54, (9.75, 0.0), (13.84, 4.147))
