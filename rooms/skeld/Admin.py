# Skeld / Admin - am Kartenfoto gemessen.
# Boden: Teppich mit Achteckmuster (Zeichnung). Monitore = gezeichnete Nordfront (an der Wand).
# Pultreihe (Meldungen 18.10.: Pulte nur aufgemalt, Stuehle hinter der Wand): Der Collider liegt an der Vorderkante der
#   Pfosten (-7,0), die Wandflaeche 0,34 dahinter (Oberkante des Wandbands -5,80 -> Wandfuss -6,66; Streifen ueber
#   _map.FLOOR_ADD_ROOMS). Vier Wandpfosten bis zur Decke (Fuss -6,92), dazwischen das Bord mit Tastatur (Zeichnung
#   -6,52..-6,42 -> Hoehe 0,50), Monitore 0,61..1,25 an der Wand.
# Stuehle (Sprite map_ComsChairs): drei Buerostuehle von hinten, (140,35,60) / Schatten (85,48,66), Lehne bis 0,80,
#   im Bild unten bei -6,97 -> halb unter das Bord geschoben (Mitte -6,80).
# Kartentisch (admin_bridge): Oberseite im Bild x 3,33..5,74, y -8,95..-8,08, Front nur 0,27 gezeichnet (bis -9,22)
#   -> Hoehe 0,46, unter Augenhoehe (vorher 0,76: die Holokarte war nie zu sehen). Collider -9,31..-8,26.
#   Sockelstufe vorn x 4,05..4,95, Bild -9,20..-9,32.

from shapely.geometry import box as sbox

import bm_tex as T
from bm_spec import art_block, art_floor, box, office_chair, prism, vent

LINE = (16, 24, 24)
WALL_Y = -6.66                                          # Wandflaeche hinter der Pultreihe
POSTS = [(3.05, 3.20), (4.05, 4.20), (5.02, 5.20), (6.02, 6.17)]
BAND_HOLES = [sbox(3.0, -7.15, 6.2, -6.36)]             # Stuehle, Bord und Pfostenfuesse aus dem Wandband (unter 0,5)


def floor(ctx):
    return art_floor(ctx, "floor_Admin", [sbox(3.25, -9.45, 5.95, -8.0), sbox(3.0, -7.15, 6.2, -6.35),
                                          sbox(2.2, -10.3, 2.9, -9.75)])


def props(ctx):
    parts = []
    k = ctx.k
    # Pultreihe: Bord mit Tastatur (Oberseite = Zeichnung des Tastaturstreifens), Pfosten bis zur Decke
    dark = ctx.color("adm_post", (38, 50, 52))
    shelf_side = ctx.color("adm_shelf_side", (54, 66, 68))
    parts.append(prism(sbox(3.0, -6.93, 6.2, WALL_Y), 0.44, 0.50, shelf_side, top=ctx.color("adm_shelf_top", (70, 86, 88)), outline=LINE))
    keys = ctx.color("adm_keys", (36, 44, 46))
    for kx in (3.6, 4.6, 5.6):
        parts.append(box(kx, -6.82, 0.42, 0.14, 0.50, 0.515, keys, bevel=0.004))
    for x0, x1 in POSTS:
        parts.append(box((x0 + x1) / 2, (-6.95 + WALL_Y) / 2, x1 - x0, WALL_Y + 6.95, 0.0, 1.39, dark, bevel=0.02,
                         outline=LINE))
    for cx in (3.64, 4.64, 5.66):
        parts += office_chair(ctx, "adm_chair", cx, -6.80, (140, 35, 60), (85, 48, 66), (40, 14, 24))
    # Kartentisch mit Holokarte, Sockelstufe davor
    h = 0.27 / k
    from bm_models import map_table
    parts += map_table(ctx, "adm_table", 3.33, -8.95 - k * h, 5.74, -8.08 - k * h, h=h, rgb=(52, 77, 71), holo=(110, 230, 130), seed=2)
    plinth = ctx.color("adm_plinth", (54, 73, 68))
    parts.append(box(4.50, -9.27, 0.90, 0.10, 0.0, 0.12, plinth, outline=LINE))
    parts += vent(ctx, "Admin/Ground/AdminVent")
    return parts
