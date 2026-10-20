# Polus / Weapons - am Kartenfoto gemessen.
#
# Boden: dunkelgruene Dielen (Zeichnung) mit Kabel. Nordwand: graugruene Paneele (Zeichnung).
# Waffenpult rot (142,75,86), Oberseite Zeichnung (gruener Radarschirm, Steuerknueppel), Seiten (67,76,79), Hoehe 0,5.
# Kanone: liegende Kapsel innen (Bild 9,65..12,20 / -25,2..-23,95), Koerper (107,108,153)/(66,73,104), drei
#   leuchtende Streifen (149,250,245); draussen vor der Westwand der Lauf (Sprite gun0001): Sockel (137,170,170),
#   Rohr (106,107,152)/(54,72,105), zwei Sensoren oben.

import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import VFAC                                                          # noqa: E402
from shapely.geometry import Polygon, box as sbox                                 # noqa: E402
from bm_spec import art_floor, box, cyl, lathe, prism, tube                   # noqa: E402


def floor(ctx):
    return art_floor(ctx, "floor_Weapons", holes=[sbox(9.65, -25.25, 12.25, -23.9), sbox(9.70, -23.75, 11.25, -22.2)])


def props(ctx):
    parts = []
    # Waffenpult (Fehlerrunde 19.10. abends): Grundflaeche = gezeichneter Umriss bis an die Collider-Kante (Polus legt den
    # Collider an die Pultfront; die alte Fassung war um k*h nach Sueden verschoben und ragte 0,7 in den Laufweg und bis
    # x 11,2 an der Nordwand entlang). Radarschirm als runder Monitor auf Fuss, Steuerknueppel und Tastatur auf der Platte.
    desk = Polygon([(9.72, -22.18), (10.76, -22.25), (10.74, -22.40), (10.66, -22.62), (10.25, -22.70), (10.10, -23.04),
                    (10.10, -23.74), (9.72, -23.74)])
    parts.append(prism(desk, 0.0, 0.50, ctx.color("wp_desk_side", (67, 76, 79)), top=ctx.color("wp_desk_top", (142, 75, 86)),
                       bevel=0.015, outline=(24, 25, 35)))
    from bm_models import monitor
    parts += monitor(ctx, "wp_radar", 9.98, -22.36, 0.50, 0.40, 0.34, yaw=45.0, rgb=(150, 160, 175),
                     screen_rgb=(90, 220, 120), glow=2.0)
    parts.append(box(10.10, -22.60, 0.26, 0.12, 0.50, 0.53, ctx.color("wp_keys", (150, 160, 175)), rot=-20))
    stick = ctx.color("wp_stick", (40, 42, 48))
    parts.append(cyl(10.30, -22.40, 0.06, 0.50, 0.53, stick, seg=12))
    parts.append(tube([(10.30, -22.40, 0.53), (10.30, -22.40, 0.68)], 0.02, stick, seg=8))
    parts.append(lathe(10.30, -22.40, [(0.0, 0.66), (0.035, 0.67), (0.03, 0.72), (0.0, 0.73)], ctx.color("wp_knob", (230, 140, 60)), seg=10))
    # Kapsel (Kanonenverschluss) liegend, Achse West-Ost
    body = ctx.color("wp_capsule", (107, 108, 153))
    dark = ctx.color("wp_capsule_dark", (66, 73, 104))
    glow = ctx.glow("wp_capsule_glow", (149, 250, 245), 2.0)
    # Zeichnung 9,65..12,20 / -25,2..-23,95 -> liegender Zylinder r 0,52, Achse y -24,75 (Bildlage = y + k*z); r 0,55
    # ragte 0,2 durch die duenne Suedwand nach draussen
    r = 0.52
    cy, cz = -24.75, r + 0.02
    parts.append(tube([(9.55, cy, cz), (11.75, cy, cz)], r, body, seg=28, outline=(24, 25, 35)))
    parts.append(lathe(11.75, cy, [(0.0, cz), (r, cz), (r * 0.92, cz + 0.22), (r * 0.6, cz + 0.38), (0.0, cz + 0.44)], body,
                       seg=28, outline=(24, 25, 35), tilt=(90.0, 0.0, cz)))          # Kuppel nach Osten
    for i, dz in enumerate((-0.25, 0.0, 0.25)):
        parts.append(box(10.35, cy - r * math.cos(math.asin(dz / r)) + 0.02, 1.25, 0.04, cz + dz - 0.05, cz + dz + 0.05, glow))
    parts.append(box(9.75, cy, 0.25, 2 * r * 0.95, 0.02, 2 * r, dark, outline=(24, 25, 35)))
    # Lauf draussen: Sockel, schraeges Rohr, Kopf mit zwei Sensoren
    base = ctx.color("wp_gun_base", (137, 170, 170))
    tubec = ctx.color("wp_gun", (106, 107, 152))
    tubed = ctx.color("wp_gun_dark", (54, 72, 105))
    gx, gy = 9.05, -24.55
    parts.append(cyl(gx, gy, 0.52, 0.0, 0.35, base, seg=36, bevel=0.04, outline=(24, 25, 35)))
    top = (gx - 0.15, gy + 0.55, 3.0)
    parts.append(tube([(gx, gy, 0.3), (gx - 0.05, gy + 0.2, 1.4), top], 0.38, tubec, seg=24, outline=(24, 25, 35)))
    parts.append(lathe(top[0], top[1], [(0.0, top[2] - 0.1), (0.40, top[2] - 0.1), (0.42, top[2] + 0.1), (0.3, top[2] + 0.35),
                                        (0.0, top[2] + 0.42)], tubed, seg=24, outline=(24, 25, 35)))
    for sx in (-0.22, 0.22):
        parts.append(tube([(top[0] + sx * 0.5, top[1], top[2] + 0.3), (top[0] + sx * 1.6, top[1] + 0.2, top[2] + 1.0)], 0.07,
                          tubed, seg=10, outline=(24, 25, 35)))
    return parts
