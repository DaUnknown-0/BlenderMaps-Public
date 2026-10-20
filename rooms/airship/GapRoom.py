# Airship / Gap Room (obere Ebene: zwei Stege) - am Kartenfoto gemessen.
#
# Rueckwand gezeichnet 3,3 hoch (Bild 9,7..13,0, Rosa (166,98,105) mit Wolkenfenstern) -> Raumhoehe 3,3 / k = 6,1.
# Stegkanten senkrecht (Front (73,84,97) mit Zeichnung), Gelaender (Sprites gap_railing1/2), Plattform
#   (Platform 5,98..7,15 / 8,07..9,06, Riffelplatte mit Holzrahmen) in Startlage am linken Steg, Abgasschale rechts
#   (exhaustporthing, Drehkoerper; 3D 19.10.),
#   Leiter ladder_gap x 10,80 vom unteren Boden (-1,345) auf den Steg.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import face, ladder                                                  # noqa: E402
from bm_spec import art_floor, box, railing, sprite, vent                         # noqa: E402
from bm_models import exhaust_bowl, hatch_platform                                # noqa: E402
PROCEDURAL = True      # zeichnet Boden/Waende selbst (keine Spieltextur), bleibt bei bm_style aktiv

H = 6.1
BAND_H = 3.3
LOW, PIT = -1.345, -1.796


def side(ctx):
    return ctx.color("gap_wall", (166, 98, 105))


def props(ctx):
    parts = []
    # Rueckwand als eine durchgehende Scheibe ueber alle drei Ebenen: oben die Zeichnung (Bild 9,72..13,02 -> z 0..6,1),
    # darunter bis zur Grubensohle Rosa
    pink = ctx.color("gap_wall", (166, 98, 105))
    parts.append(face(ctx, "gap_back", 2.92, 16.20, 9.66, 0.0, H, art=(2.92, 9.72, 16.20, 13.02), rgb=(166, 98, 105)))
    parts.append(box((2.92 + 16.20) / 2, 9.68, 16.20 - 2.92, 0.04, PIT, 0.0, pink))
    # Stegkanten
    parts.append(face(ctx, "gap_rface", 9.74, 15.06, 7.70, LOW, 0.0, art=(9.74, 6.30, 15.06, 7.74)))
    parts.append(face(ctx, "gap_lface1", 2.93, 4.29, 6.19, PIT, 0.0, art=(2.93, 5.52, 4.29, 6.23)))
    parts.append(face(ctx, "gap_lface2", 4.52, 5.76, 7.68, PIT, 0.0, art=(4.52, 6.60, 5.76, 7.72)))
    dark = ctx.color("gap_side", (73, 84, 97))
    for x, y0, y1 in ((5.98, 7.88, 9.47), (4.53, 6.63, 7.72)):
        parts.append(box(x + 0.02, (y0 + y1) / 2, 0.04, y1 - y0, PIT, 0.0, dark))
    parts.append(box(9.53, (7.86 + 9.51) / 2, 0.04, 9.51 - 7.86, PIT, 0.0, dark))
    parts.append(box(9.53, (5.53 + 7.74) / 2, 0.04, 7.74 - 5.53, PIT, LOW, dark))
    # Gelaender an den Stegkanten
    rail = ctx.color("gap_rail", (118, 139, 156))
    parts += railing([(2.98, 6.28), (4.25, 6.28), (4.48, 6.66), (4.48, 7.77), (5.72, 7.77)], 0.55, rail, r=0.022,
                     post_step=0.4, post_r=0.02, outline=(33, 38, 42))
    parts += railing([(9.85, 7.80), (10.45, 7.80)], 0.55, rail, r=0.022, post_step=0.4, post_r=0.02, outline=(33, 38, 42))
    parts += railing([(11.15, 7.80), (13.75, 7.80)], 0.55, rail, r=0.022, post_step=0.4, post_r=0.02, outline=(33, 38, 42))
    # Plattform
    _, (x0, y0, x1, y1) = sprite(ctx, "GapRoom/Platform")
    parts += hatch_platform(ctx, "gap_platform", x0, y0, x1, y1, -0.25, -0.05)
    # Abgasschale und Leiter
    _, (ex0, ey0, ex1, ey1) = sprite(ctx, "GapRoom/exhaustporthing")
    parts += exhaust_bowl(ctx, "gap_exhaust", (ex0 + ex1) / 2, ey0 + 0.32, 0.44, 0.5)
    parts += ladder(ctx, 10.80, (7.62, LOW), (7.72, 0.0))
    parts += vent(ctx, "GapRoom/GaproomVent1")
    return parts
