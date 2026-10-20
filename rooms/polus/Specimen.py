# Polus / Specimen (Probenraum, achteckig; keine eigene Zone, siehe MAPCFG zones_add) - am Kartenfoto gemessen.
#
# Boden: Eis-Blaugrau mit Rissen, Kabel und Wurzel (Zeichnung). Waende: Bullaugen-Streifen, Konsolen (Zeichnung).
# Probentisch (Sprite specimens 35,25..37,85 / -20,73..-19,50): schwarzer Tisch, fuenf Proben-Roehren gruen
#   (137,223,140)/(90,178,132), hellblau (137,200,222), violett (184,137,222)/(148,105,198), verbunden mit Schlaeuchen.
# Kuehlboxen (Sprites panel_cooler1/2): Pink (181,33,115), Grau (123,158,181)/(178,204,219).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import VFAC, sprite_tex                                               # noqa: E402
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, cyl, lathe, sprite, tube                      # noqa: E402

TUBES = [(35.42, (137, 223, 140), (90, 178, 132)), (35.98, (137, 223, 140), (90, 178, 132)),
         (36.55, (137, 200, 222), (99, 146, 198)), (37.10, (184, 137, 222), (148, 105, 198)),
         (37.68, (184, 137, 222), (148, 105, 198))]
Z_BENCH = 0.42


def floor(ctx):
    return art_floor(ctx, "floor_Specimen", holes=[sbox(35.2, -20.8, 37.9, -19.4), sbox(36.0, -19.1, 36.9, -18.55),
                                                  sbox(38.8, -21.1, 39.4, -20.1)])


def props(ctx):
    parts = []
    k = ctx.k
    bench = ctx.color("sp_bench", (40, 42, 48))
    parts.append(box(36.55, -20.40, 2.55, 0.42, 0.0, Z_BENCH, bench, top=ctx.color("sp_bench_top", (28, 30, 34)),
                     bevel=0.02, outline=(0, 0, 0)))
    by = -20.40
    prev = None
    for x, light, dark in TUBES:
        lm = ctx.glow(f"sp_tube_{x:.2f}", light, 0.8)
        dm = ctx.color(f"sp_tube_rim_{x:.2f}", dark)
        z0 = Z_BENCH
        parts.append(cyl(x, by, 0.12, z0, z0 + 0.06, dm, seg=20, outline=(0, 0, 0)))
        parts.append(lathe(x, by, [(0.0, z0 + 0.06), (0.10, z0 + 0.06), (0.11, z0 + 0.12), (0.11, z0 + 0.55),
                                   (0.08, z0 + 0.63), (0.0, z0 + 0.66)], lm, seg=20, outline=(0, 0, 0)))
        parts.append(cyl(x, by, 0.06, z0 + 0.64, z0 + 0.72, dm, seg=12))
        if prev is not None:
            parts.append(tube([(prev, by, z0 + 0.72), ((prev + x) / 2, by, z0 + 0.85), (x, by, z0 + 0.72)], 0.018, dm, seg=6))
        prev = x
    pink = ctx.color("sp_cooler_pink", (181, 33, 115))
    body = ctx.color("sp_cooler", (123, 158, 181))
    lid = ctx.color("sp_cooler_top", (178, 204, 219))
    dark = ctx.color("sp_cooler_dark", (70, 90, 104))
    _, (x0, y0, x1, y1) = sprite(ctx, "RightPod/panel_cooler1")           # Truhe: pinker Korpus, heller Deckel, Griff
    cx_ = (x0 + x1) / 2
    parts.append(box(cx_, y0 + 0.15, x1 - x0, 0.3, 0.0, 0.3, pink, bevel=0.015, outline=(0, 0, 0)))
    parts.append(box(cx_, y0 + 0.15, x1 - x0 + 0.02, 0.32, 0.3, 0.42, lid, bevel=0.02, outline=(0, 0, 0)))
    parts.append(box(cx_, y0 - 0.01, 0.2, 0.02, 0.33, 0.36, dark))
    # Kuehlschrank (panel_cooler2): voller Korpus auf seinem Collider (38,86..39,36 / -21,04..-20,40), heller Korpus,
    # Tuer nach Sueden mit Griff, pinker Sockel; vorher eine 0,3 tiefe Scheibe, von Norden eine "weisse Platte mit
    # rosa Fuss" (#305)
    fx0, fx1, fy0, fy1 = 38.87, 39.35, -21.03, -20.42
    cx_, cy_ = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    parts.append(box(cx_, cy_, fx1 - fx0, fy1 - fy0, 0.0, 0.12, pink, outline=(0, 0, 0)))
    parts.append(box(cx_, cy_, fx1 - fx0, fy1 - fy0, 0.12, 0.88, lid, top=body, bevel=0.02, outline=(0, 0, 0)))
    parts.append(box(cx_, fy0 - 0.004, fx1 - fx0 - 0.05, 0.008, 0.16, 0.84, body))
    parts.append(box(cx_ - (fx1 - fx0) * 0.3, fy0 - 0.016, 0.025, 0.022, 0.40, 0.66, dark))
    parts.append(box(cx_, fy0 - 0.009, fx1 - fx0 - 0.12, 0.004, 0.70, 0.78, dark))
    # Konsolen an der Nordwest-Diagonale (Wand = Collider (34,34|-19,84)-(35,34|-18,84)): Simon Says oben, Manifolds
    # mit Ablage darunter (#270: standen hinter der Wand)
    from bm_models import wall_console
    parts += wall_console(ctx, "sp_simon", (35.265, -18.985), (34.865, -19.385), 0.5, 0.98, body_rgb=(150, 160, 170),
                          screen=(110, 200, 120), depth=0.12)
    parts += wall_console(ctx, "sp_manifold", (34.805, -19.445), (34.405, -19.845), 0.35, 0.85, body_rgb=(60, 70, 90),
                          screen=(90, 150, 230), depth=0.12)
    return parts
