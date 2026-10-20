# Polus / Office (Besprechungsraum, Buero Ost, Flur) - am Kartenfoto gemessen.
#
# Boden: Zeichnung (blauer Teppich, Holzdielen, gestreifter Flur). Waende: Zeichnung (Fenster, Bilder, Tapete).
# Besprechungstisch oval (Sprite caftable 17,71..21,40 / -17,45..-16,69), Holz (126,104,82), Notfallknopf.
# Projektor (Sprite projector), Wasserspender (Sprite panel_waterjug, (46,165,217)), Topfpflanzen (_common).
# Buero Ost an der Nordwand: ID-Scanner (Bild 24,50..25,12 / -16,50..-15,93) und Schreibtisch (25,30..27,40,
#   Front -16,45, cremefarbene Platte mit Ablage, Tastatur); Monitore und Bild bleiben Wandzeichnung.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import POTS, VFAC, front_box, potted_plant, sprite_tex               # noqa: E402
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, cyl, lathe, sprite, vent                      # noqa: E402

BAND_HOLES = [sbox(24.45, -16.55, 27.45, -15.95), sbox(15.95, -16.5, 16.2, -16.1), sbox(23.5, -16.5, 23.8, -16.1)]
Z_TABLE = 0.45


def floor(ctx):
    return art_floor(ctx, "floor_Office", holes=[sbox(17.65, -17.5, 21.45, -16.6), sbox(22.2, -17.6, 23.4, -16.5),
                                                sbox(16.55, -16.3, 17.0, -15.7)]
                     + [sbox(x - 0.14, y - 0.02, x + 0.14, y + 0.6) for x, y in POTS if y > -19.5])


def props(ctx):
    parts = []
    k = ctx.k
    # Besprechungstisch: Platte = Sprite (mit Aufdruck), Fuss mittig
    img, (x0, y0, x1, y1) = sprite(ctx, "Office/caftable")
    top = sprite_tex(ctx, "Office/caftable", "of_table_top", bg=(126, 104, 82))
    wood = ctx.color("of_table_wood", (126, 104, 82))
    woodd = ctx.color("of_table_wood_dark", (96, 76, 58))
    # Platte auf dem Collider (ShortObjects caftable -17,45..-16,81), vorher 0,5 weiter suedlich im Laufweg
    cx, cy = (x0 + x1) / 2, (-17.45 - 16.81) / 2
    parts.append(cyl(cx, cy, (x1 - x0) / 2, Z_TABLE - 0.06, Z_TABLE, woodd, top=top, ry=0.34, seg=64, bevel=0.015,
                     outline=(42, 34, 25)))
    for dx in (-1.1, 1.1):
        parts.append(box(cx + dx, cy, 0.22, 0.22, 0.0, Z_TABLE - 0.06, woodd, outline=(42, 34, 25)))
    _, (ex0, ey0, ex1, ey1) = sprite(ctx, "caftable/EmergencyButton")
    dome = ctx.color("of_emergency", (232, 120, 150))
    parts.append(lathe((ex0 + ex1) / 2, (ey0 + ey1) / 2 - k * Z_TABLE, [(0.0, Z_TABLE), (0.12, Z_TABLE), (0.11, Z_TABLE + 0.05),
                                                                      (0.07, Z_TABLE + 0.09), (0.0, Z_TABLE + 0.1)], dome, seg=24,
                       outline=(20, 20, 24)))
    # Projektor auf Staender
    _, (px0, py0, px1, py1) = sprite(ctx, "Office/projector")
    body = ctx.color("of_projector", (190, 190, 190))
    pcx = px0 + 0.38
    parts.append(cyl(pcx, py0 + 0.15, 0.04, 0.0, 0.55, ctx.color("of_projector_stand", (40, 40, 44)), seg=8))
    parts.append(box(pcx, py0 + 0.15, 0.3, 0.22, 0.55, 0.72, body, bevel=0.02, outline=(30, 30, 34)))
    beam = ctx.glow("of_projector_lens", (230, 240, 255), 2.0)
    parts.append(cyl(pcx + 0.16, py0 + 0.15, 0.05, 0.6, 0.67, beam, seg=12))
    # Wasserspender
    _, (wx0, wy0, wx1, wy1) = sprite(ctx, "Office/panel_waterjug")
    wcx = (wx0 + wx1) / 2
    stand = ctx.color("of_cooler", (220, 225, 230))
    jug = ctx.color("of_cooler_jug", (46, 165, 217))
    parts.append(box(wcx, wy0 + 0.12, 0.3, 0.24, 0.0, 0.62, stand, bevel=0.02, outline=(40, 44, 50)))
    parts.append(lathe(wcx, wy0 + 0.12, [(0.0, 0.62), (0.13, 0.62), (0.14, 0.7), (0.14, 0.9), (0.06, 0.98), (0.0, 0.99)], jug,
                       seg=20, outline=(10, 40, 70)))
    # Buero Ost: Scanner und Schreibtisch an der Nordwand
    from bm_models import console_block, laptop, monitor, table
    parts += console_block(ctx, "of_scanner", 24.50, -16.50, 25.12, -16.08, 0.57 / VFAC, rgb=(180, 178, 160), screens=1, seed=7)
    parts += table(ctx, "of_desk", 25.30, -16.45, 27.40, -16.0, h=0.42, top_rgb=(170, 160, 128), leg_rgb=(110, 100, 80))
    parts += monitor(ctx, "of_desk_mon1", 25.75, -16.15, 0.42, 0.4, 0.3, yaw=0.0, screen_rgb=(90, 170, 220))
    parts += monitor(ctx, "of_desk_mon2", 26.7, -16.15, 0.42, 0.44, 0.3, yaw=0.0, screen_rgb=(120, 200, 150))
    parts += laptop(ctx, "of_laptop", 26.25, -16.3, 0.42, yaw=5.0, w=0.26)
    # Trophaeenablage an der Trennwand zum Buero Ost (x 23,45..23,85 / -17,95..-16,45, Front Osten; #280):
    # Unterschrank, Platte, zwei Pokale, Buecherstapel, Becher
    cab = ctx.color("of_trophy_cab", (190, 170, 120))
    parts.append(box(23.66, -17.2, 0.36, 1.48, 0.0, 0.62, cab, bevel=0.01, outline=(60, 50, 30)))
    parts.append(box(23.66, -17.2, 0.40, 1.52, 0.62, 0.66, ctx.color("of_trophy_top", (220, 205, 160)), outline=(60, 50, 30)))
    for k in range(3):
        parts.append(box(23.845, -17.2 - 0.48 + 0.48 * k, 0.012, 0.4, 0.1, 0.55, ctx.color("of_trophy_door", (170, 150, 104))))
    silver = ctx.color("of_trophy", (200, 205, 215))
    for ty_ in (-16.62, -17.62):
        parts.append(lathe(23.66, ty_, [(0.0, 0.66), (0.07, 0.66), (0.07, 0.69), (0.02, 0.71), (0.02, 0.78), (0.08, 0.86),
                                         (0.09, 0.95), (0.0, 0.9)], silver, seg=16, outline=(60, 60, 70)))
    parts.append(box(23.66, -17.05, 0.2, 0.26, 0.66, 0.72, ctx.color("of_trophy_book", (60, 90, 170)), bevel=0.005))
    parts.append(cyl(23.66, -17.32, 0.04, 0.66, 0.76, ctx.color("of_trophy_cup", (190, 40, 50)), seg=12))
    for x, y in POTS:
        if y > -19.5:
            parts += potted_plant(ctx, x, y)
    # Buesten auf schwarzen Schraenkchen vor den Flur-Wandbloecken (Zeichnung 19,65..20,05 und 23,12..23,55, Wandfuss
    # -18,64; Fehlerrunde 19.10. abends, #293: der Block war Boden, die Buesten fehlten)
    from bm_spec import blob
    cab = ctx.color("of_bust_cab", (34, 34, 40))
    stone = (ctx.color("of_bust_light", (222, 222, 226)), ctx.color("of_bust", (176, 178, 186)))
    for bx0, bx1 in ((19.66, 20.06), (23.13, 23.55)):
        cxb, cyb = (bx0 + bx1) / 2, -18.72
        parts.append(box(cxb, cyb, bx1 - bx0, 0.16, 0.0, 0.40, cab, bevel=0.01, outline=(10, 10, 12)))
        parts.append(box(cxb, cyb - 0.082, bx1 - bx0 - 0.06, 0.004, 0.06, 0.34, ctx.color("of_bust_cab_door", (52, 52, 60))))
        parts.append(cyl(cxb, cyb, 0.07, 0.40, 0.48, stone[1], seg=14))
        parts.append(blob(cxb, cyb, 0.55, 0.1, 0.07, 0.07, stone, seed=int(bx0 * 10)))
        parts.append(blob(cxb, cyb, 0.68, 0.07, 0.075, 0.09, stone, seed=int(bx0 * 10) + 1))
    parts += vent(ctx, "Office/OfficeVent")
    return parts
