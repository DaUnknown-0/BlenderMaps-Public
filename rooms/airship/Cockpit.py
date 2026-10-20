# Airship / Cockpit (Bug) - am Kartenfoto gemessen.
#
# Boden: Holzsteg im U um blauen Teppich (Zeichnung). Nordwand: Konsolenbogen vor der Glaskuppel mit Wolken (Zeichnung).
# Pilotensitz (cockpit_chair, (140,185,239)/(77,124,170)), Steuerpult westlich davon als Standkonsole mit Schraege und
#   Hebel (Front nach Osten zum Piloten), kleine Pulte cockpit_comms/cockpit_elect als Monitore auf Fuss (3D, 19.10.).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, cyl, lathe, office_chair, sprite, tube, vent       # noqa: E402
from bm_models import floor_console, monitor                                      # noqa: E402


def floor(ctx):
    return art_floor(ctx, "floor_Cockpit", holes=[sbox(-20.15, -1.4, -18.6, -0.1), sbox(-24.7, -2.95, -24.1, -2.05),
                                                 sbox(-17.2, -3.3, -16.6, -2.6)])


def props(ctx):
    parts = []
    parts += office_chair(ctx, "cp_chair", -19.05, -0.95, (140, 185, 239), (77, 124, 170), (16, 32, 57), back="E",
                          w=0.6, seat_z=0.42, back_top=1.0)
    # Steuerpult: Standkonsole mit Schraege und Kartenanzeige, Front nach Osten (zum Sitz), dazu Steuerhebel
    parts += floor_console(ctx, "cp_steer", -19.75, -0.85, 0.95, 0.6, 0.8, body_rgb=(153, 158, 165), yaw=90.0,
                           screen_rgb=(120, 200, 120))
    lever = ctx.color("cp_lever", (40, 44, 50))
    parts.append(tube([(-19.6, -0.85, 0.78), (-19.42, -0.85, 1.02)], 0.018, lever, seg=8))
    parts.append(lathe(-19.42, -0.85, [(0.0, 1.0), (0.04, 1.02), (0.04, 1.08), (0.0, 1.1)], lever, seg=10))
    # kleine Pulte: Monitor auf Saeule und Fussplatte
    dark = ctx.color("cp_pole", (40, 44, 50))
    for suf, nm in (("Cockpit/cockpit_comms", "cp_comms"), ("Cockpit/cockpit_elect", "cp_elect")):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        cx, cy = (x0 + x1) / 2, y0 + 0.2
        parts.append(cyl(cx, cy, 0.2, 0.0, 0.04, ctx.color(nm + "_foot", (170, 120, 70)), seg=20, ry=0.14, outline=(0, 0, 0)))
        parts.append(cyl(cx, cy, 0.025, 0.04, 0.42, dark, seg=10))
        parts += monitor(ctx, nm, cx, cy, 0.42, 0.46, 0.38, yaw=0.0, screen_rgb=(150, 170, 190), stand=False)
    parts += vent(ctx, "Cockpit/CockpitVent")
    return parts
