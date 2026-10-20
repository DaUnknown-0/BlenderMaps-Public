# Polus / Security (Teil des Electrical-Gebaeudes) - am Kartenfoto gemessen.
#
# Boden: rosa Teppich (126,63,99) mit dem Lichtschein der Monitore. Waende: olivgruenes Band (85,98,88).
# Ueberwachungspult (Sprite Surv_Panel, 1,58..4,36 / -13,00..-12,40): steht im Spiel OHNE Collider an der Suedwand,
#   der Spieler laeuft darueber (Meldung #253: Kamera stand im 0,55 hohen Pult). Daher flaches U-Pult (Oberkante
#   0,30) an der Suedwand, die drei Bildschirme haengen darueber an der Wand.
# Schrank rot (Front x 3,77..4,30, Bild -11,32..-10,62): rotes Buecherregal mit Ordnern (#254: magentafarbene
#   Platte), Schreibtisch Holz (123,101,79) mit Monitor.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import VFAC                                                          # noqa: E402
from shapely.geometry import Polygon, box as sbox                                 # noqa: E402
from bm_spec import art_floor, box, obox, prism                                   # noqa: E402

PROCEDURAL = True
BAND_HOLES = [sbox(3.10, -11.40, 4.32, -10.55)]
WALL = (85, 98, 88)
CARPET = (126, 63, 99)


def floor(ctx):
    import bm_style
    return ctx.tex("sec_carpet", bm_style.floor_image("carpet", CARPET, (104, 50, 82), seed=3), uv="world", scale=[1.0, 1.0])


def _wall(ctx):
    import bm_style
    return ctx.tex("sec_wall", bm_style.wall_image("panels", WALL, trim=(60, 74, 74), H=ctx.scene.H, seed=4), uv="world",
                   scale=[ctx.scene.H, ctx.scene.H])


def north(ctx, e):
    return _wall(ctx)


def side(ctx):
    return _wall(ctx)


def props(ctx):
    parts = []
    from bm_models import bookcase, monitor, table
    # rotes Regal mit Ordnern und Buechern (Front Sueden)
    parts += bookcase(ctx, "sec_shelf", 3.74, -11.36, 4.32, -11.0, 1.1, facing="S", rgb=(120, 40, 50), shelves=3, seed=6,
                      book_colors=((200, 200, 205), (150, 155, 165), (60, 70, 90), (190, 60, 60), (220, 210, 180)))
    parts += table(ctx, "sec_desk", 3.12, -11.34, 3.70, -10.98, h=0.62, top_rgb=(123, 101, 79), leg_rgb=(70, 56, 44))
    parts += monitor(ctx, "sec_desk_mon", 3.42, -11.12, 0.62, 0.36, 0.26, yaw=0.0, screen_rgb=(90, 170, 120))
    paper = ctx.color("sec_paper", (230, 228, 220))
    parts.append(obox((3.22, -11.26, 0.625), (0.18, 0.13, 0.008), paper, yaw=12.0))
    # flaches U-Pult an der Suedwand: Fluegel schraeg, Mitte gerade, Oberkante 0,30
    side_m = ctx.color("sec_console_side", (41, 51, 49))
    top_m = ctx.color("sec_console_top", (56, 70, 68))
    keys = ctx.glow("sec_console_keys", (120, 200, 200), 0.6)
    hh = 0.30
    y_wall = -13.0
    for poly in (Polygon([(1.62, y_wall), (2.30, y_wall), (2.30, -12.80), (1.62, -12.42)]),
                 Polygon([(2.30, y_wall), (3.68, y_wall), (3.68, -12.78), (2.30, -12.78)]),
                 Polygon([(3.68, y_wall), (4.33, y_wall), (4.33, -12.42), (3.68, -12.80)])):
        parts.append(prism(poly, 0.0, hh, side_m, top=top_m, bevel=0.012, outline=(10, 14, 14)))
    parts.append(box(2.99, -12.88, 1.2, 0.1, hh, hh + 0.008, keys))
    # drei Bildschirme an der Suedwand ueber dem Pult (Schirm nach Norden)
    frame = ctx.color("sec_mon_frame", (30, 36, 36))
    for i, mx in enumerate((2.05, 2.99, 3.93)):
        parts.append(box(mx, y_wall + 0.03, 0.62, 0.05, 0.62, 1.04, frame, bevel=0.01, outline=(5, 8, 8)))
        scr = ctx.glow(f"sec_surv_scr{i}", (120, 200, 200), 1.3)
        b = box(mx, y_wall + 0.062, 0.54, 0.012, 0.66, 1.0, scr)
        b["face_n"] = scr
        parts.append(b)
    return parts
