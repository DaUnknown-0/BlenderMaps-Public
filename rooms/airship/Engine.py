# Airship / Engine - am Kartenfoto gemessen.
#
# Zwei Motorbloecke (Sprites engine_enginetop (1) -6,63..-1,63 / -0,61..1,21 und engine_enginebot -6,63..-1,62 /
#   -3,15..-1,54): Sockel (120,142,148), fuenf Kolben (165,192,189)/(129,151,156), Sammelrohr oben (145,150,162).
# Kohlehaufen (38,43,52) im Osten, gelber Kran (244,214,107)/(201,149,71) auf Sockel.

import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, blob, box, cyl, lathe, sprite, tube, vent          # noqa: E402

COAL = [(2.6, 1.6, 0.9, 0.6), (3.4, 1.1, 0.8, 0.55), (2.2, -1.6, 0.8, 0.5), (3.2, -2.0, 0.9, 0.6), (3.6, -1.4, 0.6, 0.4)]


def floor(ctx):
    holes = [sbox(-6.7, -0.65, -1.55, 1.25), sbox(-6.7, -3.2, -1.55, -1.5), sbox(0.4, 0.5, 4.1, 3.0),
             sbox(1.4, -2.7, 4.1, -0.8)]
    return art_floor(ctx, "floor_Engine", holes=holes)


def engine(ctx, x0, x1, yb, i):
    base = ctx.color("eng_base", (120, 142, 148))
    pis = ctx.color("eng_piston", (165, 192, 189))
    pisd = ctx.color("eng_piston_dark", (129, 151, 156))
    pipe = ctx.color("eng_pipe", (145, 150, 162))
    line = (38, 43, 52)
    cy = yb + 0.55
    out = [box((x0 + x1) / 2, cy, x1 - x0 - 0.3, 1.0, 0.0, 0.45, base, top=pisd, bevel=0.04, outline=line)]
    n = 5
    for j in range(n):
        px = x0 + 0.65 + j * (x1 - x0 - 1.3) / (n - 1)
        out.append(lathe(px, cy, [(0.0, 0.45), (0.30, 0.45), (0.30, 1.15), (0.26, 1.22), (0.20, 1.24), (0.20, 1.40),
                                  (0.0, 1.40)], pis, seg=24, outline=line))
        out.append(cyl(px, cy, 0.305, 0.75, 0.82, pisd, seg=24))
    out.append(tube([(x0 + 0.3, cy + 0.15, 1.45), (x1 - 0.3, cy + 0.15, 1.45)], 0.11, pipe, seg=12, outline=line))
    return out


def props(ctx):
    parts = []
    _, (x0, y0, x1, y1) = sprite(ctx, "Engine/engine_enginetop (1)")
    parts += engine(ctx, x0, x1, y0, 0)
    _, (x0, y0, x1, y1) = sprite(ctx, "Engine/engine_enginebot")
    parts += engine(ctx, x0, x1, y0, 1)
    coal = (ctx.color("eng_coal_light", (60, 64, 74)), ctx.color("eng_coal", (38, 43, 52)))
    for i, (cx, cy, r, h) in enumerate(COAL):
        parts.append(blob(cx, cy, 0.0, r, r * 0.8, h, coal, seed=40 + i))
    yel = ctx.color("eng_crane", (244, 214, 107))
    yeld = ctx.color("eng_crane_dark", (201, 149, 71))
    parts.append(cyl(1.15, 1.15, 0.42, 0.0, 0.7, ctx.color("eng_crane_base", (120, 113, 99)), seg=24, outline=(38, 43, 52)))
    parts.append(box(1.15, 1.25, 0.6, 0.55, 0.7, 1.25, yel, top=yeld, bevel=0.03, outline=(80, 50, 20)))
    parts.append(tube([(1.3, 1.3, 1.15), (2.2, 1.6, 1.9), (3.0, 1.8, 1.6)], 0.09, yel, seg=10, outline=(80, 50, 20)))
    parts += vent(ctx, "Engine/EngineVent")
    return parts
