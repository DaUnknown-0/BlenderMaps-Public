# Skeld / Reactor - am Kartenfoto gemessen.
# Kern an der Westwand: Zylinder r 0,78 (Bildbreite 1,55), Hoehe 2,3 (Bild 1,35 / k), Koerper (60,69,110), fuenf
# leuchtende Roehren (214,250,250) zur Raumseite, Deckelring (33,44,82). Raum 2,8 hoch. Westwand-Maschinerie als Block
# mit der Zeichnung, Startkonsole (85,94,135), vier Lichtroehren am Boden. Zwei Vents.

import math

from shapely.geometry import LineString, box as sbox

from bm_spec import art_block, art_box, cyl, art_floor, tube, vent

H = 2.8
FLOOR_TUBES = [[(-20.85, -4.73), (-19.25, -4.73)], [(-20.85, -6.30), (-19.25, -6.30)],
               [(-21.75, -3.55), (-20.35, -2.95)], [(-21.90, -7.55), (-20.85, -8.35)]]


def floor(ctx):
    holes = [sbox(-23.65, -5.25, -21.95, -3.1)] + [LineString(t).buffer(0.09) for t in FLOOR_TUBES]
    return art_floor(ctx, "floor_Reactor", holes)


def props(ctx):
    parts = []
    body = ctx.color("rea_body", (60, 69, 110))
    cap = ctx.color("rea_cap", (33, 44, 82))
    glow = ctx.glow("rea_glow", (214, 250, 250), 4.0)
    cx, cy, r = -22.83, -4.55, 0.78
    parts.append(cyl(cx, cy, r, 0.0, 2.25, body, seg=56, outline=(16, 20, 40)))
    parts.append(cyl(cx, cy, r + 0.04, 2.15, 2.32, cap, seg=56, outline=(16, 20, 40)))
    parts.append(cyl(cx, cy, r + 0.06, 0.0, 0.18, cap, seg=56, outline=(16, 20, 40)))
    for a in (200, 235, 270, 305, 340):
        x, y = cx + (r - 0.02) * math.cos(math.radians(a)), cy + (r - 0.02) * math.sin(math.radians(a))
        parts.append(tube([(x, y, 0.3), (x, y, 2.05)], 0.11, glow, seg=12))
    # Westwand-Schrankreihe: Korpus mit Anzeigen nach Osten; Konsole mit Schraege auf ihrem Collider
    from bm_models import console_block, floor_console
    dy = ctx.k * 1.6
    parts += console_block(ctx, "rea_westwall", -23.62, -8.40 - dy, -23.18, -1.55 - dy, 1.6, rgb=(60, 69, 110), screens=3, facing="E", seed=3)
    # Startkonsole neben dem Kern: Schraege und Schirm nach Osten zur Raummitte (Meldung 19.10.)
    parts += floor_console(ctx, "rea_console", -21.745, -5.58, 0.6, 0.45, 0.65, body_rgb=(85, 94, 135), screen_rgb=(214, 250, 250), yaw=90.0)
    lamp = ctx.glow("rea_floorlight", (220, 240, 255), 3.0)
    for t in FLOOR_TUBES:
        parts.append(tube([(x, y, 0.05) for x, y in t], 0.05, lamp, seg=10))
    parts += vent(ctx, "Reactor/Ground/ReactorVent") + vent(ctx, "Reactor/Ground/UpperReactorVent")
    return parts
