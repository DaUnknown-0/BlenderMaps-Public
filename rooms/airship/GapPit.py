# Airship / Gap Room, Grube zwischen den Stegen (-1,796, Nightfall-Messung). Boden dunkles Rosa (102,51,73)/(140,77,93)
# mit Rohren (Zeichnung). Grosses Rohr aus der Grube (Sprite pipesRight) als gebogene Roehre.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bm_spec import art_floor, tube                                               # noqa: E402
PROCEDURAL = True      # zeichnet Boden/Waende selbst (keine Spieltextur), bleibt bei bm_style aktiv

Z = -1.796
H = 6.1 + 1.796
FULL_WALLS = True


def side(ctx):
    return ctx.color("gappit_side", (102, 51, 73))


def north(ctx, e):
    return ctx.color("gappit_side", (102, 51, 73))


def props(ctx):
    pipe = ctx.color("gappit_pipe", (148, 175, 178))
    piped = ctx.color("gappit_pipe_dark", (93, 114, 132))
    out = [tube([(8.2, 5.9, 0.0), (8.2, 6.9, 0.6), (8.6, 7.6, 1.4), (9.1, 8.2, 1.6)], 0.32, pipe, seg=18, outline=(33, 38, 42)),
           tube([(7.6, 5.8, 0.0), (7.5, 6.6, 0.9), (7.9, 7.4, 1.7)], 0.22, piped, seg=14, outline=(33, 38, 42)),
           tube([(5.2, 6.0, 0.0), (5.25, 6.4, 0.9), (5.9, 6.5, 1.0), (6.6, 6.5, 1.0)], 0.12, ctx.color("gappit_rust", (89, 61, 57)),
                seg=10, outline=(28, 22, 20))]
    return out
