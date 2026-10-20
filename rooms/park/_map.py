# park (eigene Karte) - Requisiten aus den Sprites des Spiels, Grundriss = Collider (rooms/_atlas_props.py).
#
# Die drei grossen Attraktionen sind eigens gebaut (User 18.10.: "Design der 3D-Karten verbessern"); als Sprite-Tafel
# standen sie als dunkle Scheiben im Weg:
#   Riesenrad (Sprite riesenrad + radnabe, Grundriss Glass0 -3,7..2,7 / 11,4..14,6): senkrechtes Rad in der x-z-Ebene,
#     Achse nach Norden, Radius 3,2, Nabe auf 3,7; A-Boecke in Lila (99,76,140), Kranz und Speichen in Messing
#     (176,140,60), 12 Gondeln rot/creme; Nabenhaus = Sprite radnabe (Creme-Scheibe mit Goldkappe) am Boden.
#   Karussell (Sprite karussell, Grundriss Glass3 -16,8..-11,2 / -1,3..4,3): Plattform r 2,8 braun mit rotem Kranz,
#     Mittelsaeule lila, Kegeldach creme (232,214,180) mit rotem Rand, sechs Pferde an Messingstangen, Fahne.
#   Lichtturm (Sprite turm, Fuss 10,6..13,0 / 12,6): Gittermast aus vier Beinen mit Querstreben, oben roter Balken
#     mit vier Leuchten.

import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _atlas_props as AP                                                         # noqa: E402
from bm_spec import box, cyl, lathe, obox, tube                                  # noqa: E402

PURPLE = (99, 76, 140)
BRASS = (176, 140, 60)
CREAM = (232, 214, 180)
RED = (206, 62, 72)
BROWN = (128, 86, 54)
STEEL = (62, 64, 88)
OL = (20, 20, 24)


def ferris_wheel(ctx):
    parts = []
    xc, yc, R = -0.5, 13.0, 3.2
    zc = R + 0.5
    purple = ctx.color("park_purple", PURPLE)
    brass = ctx.color("park_brass", BRASS)
    cream = ctx.color("park_cream", CREAM)
    red = ctx.color("park_red", RED)
    dark = ctx.color("park_dark", (60, 48, 80))
    # Nabenhaus am Boden (Sprite radnabe): Creme-Scheibe, roter Kranz, goldene Kappe
    parts.append(cyl(xc, yc, 1.2, 0.0, 0.3, cream, seg=32, outline=OL))
    parts.append(cyl(xc, yc, 1.22, 0.3, 0.42, red, seg=32))
    parts.append(cyl(xc, yc, 0.6, 0.42, 0.75, brass, seg=24, outline=OL))
    # A-Boecke beidseits (y +- 0.7), Fuesse 2,3 auseinander, oben in der Nabe
    for sgn in (-1, 1):
        y = yc + sgn * 0.7
        for fx in (-2.3, 2.3):
            parts.append(tube([(xc + fx, y, 0.0), (xc, y, zc)], 0.11, purple, seg=10, outline=OL))
        parts.append(tube([(xc - 1.2, y, zc * 0.48), (xc + 1.2, y, zc * 0.48)], 0.06, purple, seg=8))
    # Achse und Nabe
    parts.append(tube([(xc, yc - 0.9, zc), (xc, yc + 0.9, zc)], 0.12, dark, seg=12, outline=OL))
    parts.append(lathe(xc, yc, [(0.0, zc - 0.45), (0.35, zc - 0.3), (0.45, zc), (0.35, zc + 0.3), (0.0, zc + 0.45)], purple,
                       seg=16, outline=OL))
    # Kranz (zwei Ringe), Speichen, Gondeln
    n = 36
    for sgn in (-1, 1):
        y = yc + sgn * 0.45
        ring = [(xc + R * math.cos(2 * math.pi * i / n), y, zc + R * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
        parts.append(tube(ring, 0.06, brass, seg=8, outline=OL))
        for i in range(12):
            a = 2 * math.pi * i / 12
            parts.append(tube([(xc, y, zc), (xc + R * math.cos(a), y, zc + R * math.sin(a))], 0.035, brass, seg=6))
    for i in range(12):
        a = 2 * math.pi * i / 12
        px, pz = xc + R * math.cos(a), zc + R * math.sin(a)
        parts.append(tube([(px, yc - 0.45, pz), (px, yc + 0.45, pz)], 0.04, brass, seg=6))        # Querachse
        col = red if i % 2 == 0 else cream
        parts.append(obox((px, yc, pz - 0.42), (0.6, 0.55, 0.6), ctx.color("park_gondel_" + ("r" if i % 2 == 0 else "c"), RED if i % 2 == 0 else CREAM),
                          outline=OL))
        parts.append(obox((px, yc, pz - 0.08), (0.08, 0.08, 0.14), dark))                            # Aufhaengung
    return parts


def carousel(ctx):
    parts = []
    xc, yc, R = -14.0, 1.5, 2.8
    brown = ctx.color("park_brown", BROWN)
    red = ctx.color("park_red", RED)
    cream = ctx.color("park_cream", CREAM)
    purple = ctx.color("park_purple", PURPLE)
    brass = ctx.color("park_brass", BRASS)
    white = ctx.color("park_white", (240, 236, 228))
    bulb = ctx.glow("park_bulb", (255, 226, 140), 2.0)
    parts.append(cyl(xc, yc, R, 0.0, 0.32, brown, seg=40, outline=OL))
    parts.append(cyl(xc, yc, R + 0.04, 0.32, 0.48, red, seg=40, outline=OL))
    for i in range(20):                                                   # Gluehbirnen am Kranz
        a = 2 * math.pi * i / 20
        parts.append(cyl(xc + (R + 0.07) * math.cos(a), yc + (R + 0.07) * math.sin(a), 0.05, 0.37, 0.45, bulb, seg=6))
    parts.append(cyl(xc, yc, 0.55, 0.48, 3.4, purple, seg=20, outline=OL))
    parts.append(cyl(xc, yc, 0.7, 1.2, 1.9, brass, seg=20))               # Messingband mit dem Spielwerk
    parts.append(lathe(xc, yc, [(0.0, 3.3), (R + 0.3, 3.3), (R + 0.3, 3.42), (0.2, 4.75), (0.0, 4.8)], cream, seg=36,
                       outline=OL))
    parts.append(lathe(xc, yc, [(0.0, 3.3), (R + 0.32, 3.3), (R + 0.32, 3.55), (0.0, 3.55)], red, seg=36))   # roter Rand
    parts.append(tube([(xc, yc, 4.75), (xc, yc, 5.3)], 0.025, brass, seg=6))
    parts.append(obox((xc + 0.2, yc, 5.2), (0.4, 0.02, 0.22), red))       # Fahne
    for i in range(6):                                                    # Pferde an Messingstangen
        a = 2 * math.pi * i / 6 + 0.3
        px, py = xc + 2.0 * math.cos(a), yc + 2.0 * math.sin(a)
        parts.append(cyl(px, py, 0.03, 0.48, 3.3, brass, seg=8))
        yaw = math.degrees(a) + 90.0                                      # Pferd laeuft im Kreis
        parts.append(obox((px, py, 1.45), (0.75, 0.28, 0.34), white, yaw=yaw, outline=OL))
        hx, hy = px + 0.42 * math.cos(a + math.pi / 2), py + 0.42 * math.sin(a + math.pi / 2)
        parts.append(obox((hx, hy, 1.72), (0.3, 0.18, 0.42), white, yaw=yaw, pitch=-25.0, outline=OL))
        parts.append(obox((px, py, 1.66), (0.26, 0.3, 0.08), red, yaw=yaw))                        # Sattel
        for lx in (-0.25, 0.25):
            lxw, lyw = px + lx * math.cos(a + math.pi / 2), py + lx * math.sin(a + math.pi / 2)
            parts.append(obox((lxw, lyw, 1.1), (0.08, 0.2, 0.4), white, yaw=yaw))                 # Beine
    return parts


def light_tower(ctx):
    parts = []
    xc, yc = 11.8, 13.4
    cream = ctx.color("park_cream", CREAM)
    steel = ctx.color("park_steel", STEEL)
    red = ctx.color("park_red", RED)
    lamp = ctx.glow("park_lamp", (255, 236, 170), 3.0)
    parts.append(cyl(xc, yc, 1.2, 0.0, 0.35, cream, seg=28, outline=OL))
    H = 6.4
    legs = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        a = (xc + sx * 0.55, yc + sy * 0.55, 0.35)
        b = (xc + sx * 0.25, yc + sy * 0.25, H)
        legs.append((a, b))
        parts.append(tube([a, b], 0.045, steel, seg=8, outline=OL))
    for t in (0.22, 0.47, 0.72, 0.97):                                    # Querstreben in vier Hoehen
        pts = []
        for a, b in legs:
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t))
        parts.append(tube(pts + [pts[0]], 0.025, steel, seg=6))
    parts.append(box(xc, yc, 1.7, 0.5, H, H + 0.22, red, outline=OL))
    for i in range(4):
        parts.append(lathe(xc - 0.6 + 0.4 * i, yc, [(0.0, H + 0.2), (0.14, H + 0.28), (0.14, H + 0.4), (0.0, H + 0.48)], lamp,
                           seg=10))
    return parts


def extra(sc, ctx):
    meshes = AP.build(sc, ctx, skip=("riesenrad", "radnabe", "karussell", "turm"))
    meshes.append({"name": "park_rides", "coll": "Props", "kind": "parts",
                   "parts": ferris_wheel(ctx) + carousel(ctx) + light_tower(ctx)})
    return meshes


def adjust(sc):
    AP.room_heights(sc)
