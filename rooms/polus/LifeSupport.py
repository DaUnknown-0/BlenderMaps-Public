# Polus / LifeSupport (O2: Baumraum, Flaschenlager, Gang) - am Kartenfoto gemessen.
#
# Baum: Stamm (114,95,74)/(86,62,50), Mitte Bild (1,75 | -15,6), Fuss -16,2; Krone (24,85,60)/(16,65,55), hell
#   (50,126,82), Kontur (9,42,26), gezeichnet x 0,3..3,2 / -14,45..-15,3 vor der Rueckwand (138,132,127) -> in
#   Hoehe ~1,8 ueber dem Stamm (Bild - k*z). Ranken (50,126,82) bei x 0,6 und 2,85. Wurzeln bleiben Bodenzeichnung.
# Flaschenlager: Tank (100,98,81)/(65,59,49) auf blauem Ring, Fuellstation (Sprite panel_fill02), Maschine
#   (96,130,133)/(117,151,154), O2-Flaschen (132,167,187)/(71,97,126).
# Freistehende Zwischenwand (storage_middlewall) bleibt Wand (_map.py KEEP_WALLS).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import VFAC, art_tex, front_box, sprite_tex                          # noqa: E402
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, blob, box, cyl, lathe, tube, vent                  # noqa: E402

H = 2.2

BOTTLES = [(0.93, -18.72), (1.05, -18.68), (2.08, -18.78), (2.20, -18.70), (2.30, -18.84), (2.16, -18.90),
           (0.42, -20.15), (0.55, -20.10)]


def floor(ctx):
    return art_floor(ctx, "floor_LifeSupport", holes=[sbox(0.25, -20.05, 0.80, -18.10), sbox(0.85, -19.80, 1.65, -19.20),
                                                       sbox(1.40, -16.25, 2.10, -15.2), sbox(0.35, -17.95, 0.95, -16.9)])


def props(ctx):
    parts = []
    # O2-Baum (Fehlerrunde 19.10., #250/#251): Stamm mit Wurzelanlauf im Graszimmer, Aeste in eine Krone UNTER der
    # Decke (H 2,2, Krone bis z 2,0), Wurzeln als sich verjuengende Straenge am Boden, Ranken aus der Krone, die Aufgabe
    # (panel_Tree) als kleines Geraet am Stamm statt eines Fernsehers.
    import math
    import bm_style
    from shapely.geometry import box as _bx
    trunk = ctx.color("o2_trunk", (114, 95, 74))
    trunkd = ctx.color("o2_trunk_dark", (86, 62, 50))
    leaf = (ctx.color("o2_leaf_light", (50, 126, 82)), ctx.color("o2_leaf", (24, 85, 60)))
    grass = ctx.tex("o2_grass", bm_style.floor_image("grass", (50, 126, 82), (40, 104, 66), seed=8), uv="world", scale=[1.0, 1.0])
    room = ctx.scene.rooms.get("LifeSupport")
    gpoly = _bx(0.3, -17.55, 4.05, -14.2)
    if room is not None:
        gpoly = gpoly.intersection(room).buffer(-0.01)
    from bm_spec import prism
    for g in getattr(gpoly, "geoms", [gpoly]):
        if g.geom_type == "Polygon" and g.area > 0.05:
            parts.append(prism(g, 0.0, 0.006, grass))
    tx, ty = 1.80, -15.85
    parts.append(lathe(tx, ty, [(0.0, 0.0), (0.52, 0.0), (0.40, 0.05), (0.31, 0.22), (0.26, 0.7), (0.25, 1.1), (0.29, 1.35),
                                (0.36, 1.5), (0.0, 1.5)], trunk, seg=22, outline=(40, 28, 22)))
    for k in range(8):                                                   # Rindenrippen
        a = math.radians(k * 45 + 10)
        parts.append(tube([(tx + 0.3 * math.cos(a), ty + 0.3 * math.sin(a), 0.15), (tx + 0.255 * math.cos(a), ty + 0.255 * math.sin(a), 0.9),
                           (tx + 0.28 * math.cos(a), ty + 0.28 * math.sin(a), 1.35)], 0.035, trunkd, seg=6))
    for a, l in ((200, 1.0), (330, 1.1), (20, 0.9), (150, 0.8), (260, 0.7)):     # Wurzeln
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        pts = [(tx + 0.3 * ca, ty + 0.3 * sa, 0.18), (tx + 0.55 * ca, ty + 0.55 * sa, 0.08), (tx + l * ca, ty + l * sa, 0.04)]
        parts.append(tube(pts[:2], 0.1, trunk, seg=8))
        parts.append(tube(pts[1:], 0.06, trunkd, seg=8))
        parts.append(tube([pts[2], (tx + (l + 0.3) * ca + 0.1 * sa, ty + (l + 0.3) * sa - 0.1 * ca, 0.02)], 0.035, trunkd, seg=6))
    # Aeste und Krone
    crown = [(0.75, -15.45, 1.62, 0.45, 0.4, 0.26), (1.25, -15.3, 1.72, 0.5, 0.42, 0.28), (1.85, -15.25, 1.75, 0.55, 0.45, 0.28),
             (2.45, -15.35, 1.7, 0.5, 0.42, 0.27), (2.95, -15.5, 1.6, 0.42, 0.38, 0.25), (1.2, -15.95, 1.6, 0.45, 0.4, 0.24),
             (1.85, -16.1, 1.65, 0.5, 0.42, 0.25), (2.5, -15.95, 1.6, 0.45, 0.4, 0.24), (1.85, -15.65, 1.82, 0.45, 0.4, 0.22)]
    seed = 0
    for cx, cy, cz, rx, ry, rz in crown:
        seed += 1
        if abs(cx - tx) > 0.3 or abs(cy - ty) > 0.3:
            parts.append(tube([(tx, ty, 1.3), ((tx + cx) / 2, (ty + cy) / 2, (1.3 + cz) / 2 + 0.05), (cx, cy, cz - 0.1)], 0.06, trunk, seg=8))
        parts.append(blob(cx, cy, cz, rx, ry, rz, leaf, seed=seed, outline=(9, 42, 26)))
    vine = ctx.color("o2_vine", (50, 126, 82))
    for vx, vy, low in ((0.6, -15.4, 0.7), (1.0, -15.15, 0.95), (2.7, -15.2, 0.85), (3.05, -15.55, 1.0), (1.4, -16.25, 1.1),
                        (2.3, -16.25, 0.9)):
        parts.append(tube([(vx, vy, 1.5), (vx + 0.04, vy - 0.03, (1.5 + low) / 2), (vx - 0.02, vy - 0.05, low)], 0.025, vine, seg=6))
        parts.append(blob(vx - 0.02, vy - 0.05, low, 0.06, 0.05, 0.05, leaf, seed=int(vx * 10), outline=(9, 42, 26)))
    # Aufgabe am Stamm (panel_Tree): kleines Geraet mit blauer Anzeige auf der Suedseite
    dev = ctx.color("o2_tree_panel", (60, 66, 84))
    scr = ctx.glow("o2_tree_panel_scr", (110, 170, 230), 1.3)
    parts.append(box(tx - 0.05, ty - 0.29, 0.24, 0.07, 0.55, 0.78, dev, bevel=0.01, outline=(20, 22, 30)))
    b = box(tx - 0.05, ty - 0.33, 0.17, 0.01, 0.6, 0.73, scr)
    b["front"] = scr
    parts.append(b)
    parts.append(tube([(tx - 0.05, ty - 0.27, 0.78), (tx + 0.02, ty - 0.24, 1.1)], 0.012, ctx.color("o2_tree_cable", (40, 60, 160)), seg=5))
    # Tank im Baumraum (links unten) und im Lager
    tank = ctx.color("o2_tank", (100, 98, 81))
    tankd = ctx.color("o2_tank_dark", (65, 59, 49))
    ring = ctx.color("o2_tank_ring", (60, 110, 200))
    for bx, by, h in ((0.62, -17.75, 1.1), (0.50, -18.75, 0.95)):
        parts.append(cyl(bx, by, 0.26, 0.0, 0.10, ring, seg=32, outline=(20, 30, 60)))
        parts.append(cyl(bx, by, 0.25, 0.10, h, tankd, top=tank, seg=32, bevel=0.03, outline=(30, 26, 20)))
    # Maschine mit Luefter und Anzeigen, Fuellstation
    # Maschine mit Luefter und Anzeigen, Fuellstation (gegliedert statt glatter Kisten, #250)
    from bm_models import console_block, fan_unit
    parts += console_block(ctx, "o2_machine", 0.25, -20.02, 0.80, -18.85, 0.85, rgb=(96, 130, 133), screens=2, facing="E", seed=4,
                           screen_rgbs=[(120, 200, 160), (200, 170, 80)])
    parts += fan_unit(ctx, "o2_machine_fan", 0.81, -19.12, 0.62, r=0.13, yaw=0.0, rgb=(117, 151, 154), blade_rgb=(50, 60, 64))
    parts += console_block(ctx, "o2_fill", 0.86, -19.78, 1.62, -19.30, 0.5, rgb=(79, 101, 112), screens=1, facing="N", seed=9,
                           screen_rgbs=[(110, 180, 220)])
    nozzle = ctx.color("o2_fill_nozzle", (40, 44, 50))
    parts.append(tube([(1.25, -19.40, 0.5), (1.25, -19.40, 0.75), (1.25, -19.24, 0.75), (1.25, -19.24, 0.62)], 0.025, nozzle, seg=8))
    # Spind am Suedende der Zwischenwand: beige Tuer mit gruenem Streifen, Griff, Lueftungsschlitze (#250).
    # Gezeichnet bis y -21,35, davon sind k*h = 0,35 die Schraegblick-Front: Standflaeche endet bei -21,0
    # (Meldung #250 stand bei 2,65/-21,09 im Laufbereich).
    from bm_models import locker_row
    parts += locker_row(ctx, "o2_locker", 2.10, -21.00, 2.50, -20.64, h=1.3, n=1, facing="S", rgb=(170, 160, 130), dark=(80, 74, 60))
    parts.append(box(2.30, -21.018, 0.36, 0.012, 0.3, 0.38, ctx.color("o2_locker_stripe", (40, 150, 90))))
    # Sauerstoffflaschen
    bl = ctx.color("o2_bottle", (132, 167, 187))
    bd = ctx.color("o2_bottle_dark", (71, 97, 126))
    for bx, by in BOTTLES:
        parts.append(lathe(bx, by, [(0.0, 0.0), (0.075, 0.0), (0.075, 0.42), (0.05, 0.48), (0.022, 0.50), (0.022, 0.55),
                                    (0.0, 0.55)], bl, seg=16, outline=(30, 40, 60)))
        parts.append(cyl(bx, by, 0.077, 0.08, 0.14, bd, seg=16))
    parts += vent(ctx, "LifeSupport/LifeSuppVent")
    return parts
