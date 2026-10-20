# Airship / Ventilation - am Kartenfoto gemessen. Boden dunkelrosa (96,53,63) mit zwei Gitterbuehnen (Zeichnung als
# Oberseite, 0,35 hoch) und Gelaendern (Sprites ventilation_railing1/2, Rohr (148,164,173)). Luefter: Wandzeichnung.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import art_tex                                                       # noqa: E402
from bm_spec import box, railing                                                  # noqa: E402

DECKS = [(25.30, -0.20, 26.65, 1.60), (28.10, -2.55, 29.60, -0.90)]
Z_D = 0.35


def props(ctx):
    parts = []
    side = ctx.color("av_deck", (55, 59, 60))
    rail = ctx.color("av_rail", (148, 164, 173))
    for i, (x0, y0, x1, y1) in enumerate(DECKS):
        top = art_tex(ctx, f"av_deck_top{i}", x0, y0 + ctx.k * Z_D, x1, y1 + ctx.k * Z_D)
        parts.append(box((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, 0.0, Z_D, side, top=top, outline=(33, 36, 41)))
        parts += railing([(x0 + 0.05, y0 + 0.05), (x1 - 0.05, y0 + 0.05)], Z_D + 0.55, rail, r=0.022, post_step=0.4,
                         post_r=0.02, outline=(33, 36, 41))
    return parts
