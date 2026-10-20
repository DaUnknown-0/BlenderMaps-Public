# Polus / Comms - am Kartenfoto gemessen.
#
# Boden: dunkelgruene Dielen (Zeichnung). Nordwand: Spinde, WLAN-Kasten, Schreibtisch mit zwei Monitoren (Zeichnung).
# Ostseite: gruenes Pult (L-Form, Bild 12,55..13,30 / -16,40..-15,00) mit Tastatur und blauem Schirm, gebaut, Hoehe 0,55.
# Tisch rund (Sprite commstable 10,93..11,92 / -17,07..-16,38), Platte (132,166,143), Fuss (90,121,107).
# Satellitenschuessel an der Nordostecke aussen: Sockelkasten 13,30..13,75 (Fuss Bild -15,95, Kopf -14,85, mit
#   Sprite panel_comms), Mast bis z 3,0, Schale (99,111,115)/(186,207,230) schraeg nach Suedwesten.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import VFAC, art_tex, sprite_tex                                     # noqa: E402
from shapely.geometry import Polygon, box as sbox                                 # noqa: E402
from bm_spec import art_block, art_floor, box, cyl, lathe, vent                   # noqa: E402

BAND_HOLES = [sbox(12.50, -16.45, 13.35, -14.95)]


def floor(ctx):
    return art_floor(ctx, "floor_Comms", holes=[sbox(10.90, -17.10, 11.95, -16.35), sbox(12.50, -16.45, 13.35, -15.5)])


def props(ctx):
    parts = []
    console = Polygon([(12.55, -15.0), (13.30, -15.0), (13.30, -16.40), (12.95, -16.40), (12.80, -15.95), (12.55, -15.75)])
    from bm_models import console_block
    # Grundflaeche innerhalb der Collider-Kante (Comms/Walls (12,87|-15,60)-(13,00|-16,18)); um k*h nach Sueden verschoben
    # ragte das Pult 0,6 in den Laufweg, seit Comms als begehbar erkannt wird (Tuer-Schatten sperrt nicht mehr,
    # Fehlerrunde 19.10. abends)
    parts += console_block(ctx, "cm_console", 12.93, -16.16, 13.34, -15.50, 0.55, rgb=(90, 121, 107), screens=2,
                           facing="W", seed=3)
    # Tisch: Platte einfarbig, darauf zwei Becher und ein Teller (Koerper)
    img_top = ctx.color("cm_table_top", (150, 176, 158))
    cx, cy = 11.42, -16.73                                             # Mitte des Colliders commstable
    foot = ctx.color("cm_table_foot", (90, 121, 107))
    parts.append(cyl(cx, cy, 0.08, 0.0, 0.40, foot, seg=16, outline=(20, 30, 26)))
    parts.append(cyl(cx, cy, 0.25, 0.0, 0.04, foot, seg=24))
    parts.append(cyl(cx, cy, 0.47, 0.40, 0.46, foot, top=img_top, ry=0.34, seg=48, bevel=0.015, outline=(20, 30, 26)))
    cup = ctx.color("cm_cup", (180, 50, 60))
    plate = ctx.color("cm_plate", (230, 230, 225))
    for px, py in ((cx - 0.25, cy + 0.05), (cx + 0.22, cy + 0.08)):
        parts.append(lathe(px, py, [(0.0, 0.46), (0.035, 0.46), (0.04, 0.56), (0.0, 0.56)], cup, seg=12, outline=(60, 20, 24)))
    parts.append(cyl(cx, cy - 0.1, 0.1, 0.46, 0.47, plate, seg=20, outline=(120, 120, 120)))
    # Satellitenschuessel
    grey = ctx.color("cm_dish_grey", (99, 111, 115))
    dark = ctx.color("cm_dish_dark", (62, 68, 72))
    light = ctx.color("cm_dish_light", (186, 207, 230))
    b = box(13.52, -15.78, 0.45, 0.36, 0.0, 1.37, grey, top=dark, bevel=0.03, outline=(20, 24, 26))
    b["front"] = art_tex(ctx, "cm_dish_base", 13.30, -15.95, 13.88, -14.85)
    parts.append(b)
    parts.append(cyl(13.48, -15.70, 0.11, 1.37, 3.0, grey, seg=16, outline=(20, 24, 26)))
    parts.append(lathe(13.48, -15.70, [(0.0, 2.95), (0.12, 2.96), (0.30, 3.02), (0.45, 3.13), (0.47, 3.16), (0.0, 3.06)],
                       light, seg=40, outline=(20, 24, 26), tilt=(35.0, 225.0, 3.0)))
    parts.append(cyl(13.48, -15.70, 0.03, 3.0, 3.35, dark, seg=8))
    # Nordwand (Fehlerrunde 19.10., #282/#283): zwei Spinde, WLAN-Kasten mit Antennen, Schreibtisch mit zwei Monitoren
    from bm_models import locker_row, monitor, table
    parts += locker_row(ctx, "cm_locker", 10.30, -15.45, 10.90, -15.02, h=1.15, n=2, facing="S", rgb=(60, 62, 92), dark=(30, 30, 46))
    # WLAN-Geraet (Sprite panel_wifi 10,94..11,15 / -15,53..-15,07): stehender violetter Kasten auf dem Boden mit
    # Leuchtstreifen und zwei Antennen (vorher Wandkasten in 0,8 Hoehe; bm_objects setzte daneben einen eigenen Klotz)
    wifi = ctx.color("cm_wifi", (96, 70, 128))
    led = ctx.glow("cm_wifi_led", (90, 230, 120), 2.0)
    parts.append(box(11.045, -15.38, 0.2, 0.22, 0.0, 0.52, wifi, bevel=0.012, outline=(20, 24, 26)))
    parts.append(box(11.045, -15.492, 0.12, 0.006, 0.40, 0.43, led))
    from bm_spec import tube as _tube
    for ax in (10.99, 11.10):
        parts.append(_tube([(ax, -15.34, 0.52), (ax + (ax - 11.045) * 0.8, -15.34, 0.78)], 0.009, wifi, seg=5))
    parts += table(ctx, "cm_desk", 11.25, -15.45, 12.25, -15.02, h=0.62, top_rgb=(90, 121, 107), leg_rgb=(50, 60, 56))
    parts += monitor(ctx, "cm_desk_mon1", 11.5, -15.15, 0.62, 0.36, 0.26, yaw=0.0, screen_rgb=(90, 170, 220))
    parts += monitor(ctx, "cm_desk_mon2", 11.98, -15.15, 0.62, 0.36, 0.26, yaw=0.0, screen_rgb=(120, 200, 150))
    parts.append(box(11.74, -15.33, 0.34, 0.1, 0.62, 0.635, ctx.color("cm_keys", (40, 44, 50))))
    parts += vent(ctx, "Comms/CommsVent")
    return parts
