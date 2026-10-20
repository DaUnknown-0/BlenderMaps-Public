# Mira HQ / Startplattform - am Kartenfoto gemessen (k 0,53).
# Raumschiff: Rumpf (70,84,84) x -7,35..-2,65, Front senkrecht bei y 4,35 bis 2,3, Schraege mit Gitter (148,162,165)
#   bis y 5,6 / 3,2, flaches Dach bis y 11,5 (Deutung, Rumpf reicht ueber den Bildrand). Seitentriebwerke (104,124,123)
#   mit den gezeichneten Lueftern als Front. Gastank (189,152,29) liegend r 0,75, Achse y 1,2..3,15 auf 0,85 (die
#   Zeichnung zeigt die Stirnseite ungestaucht). Kisten im Skeld-Stil, Konsolen mit Zeichnung, Zaun (102,103,113)
#   an den offenen Kanten, Absperrpfosten mit Ketten, Vent.

from shapely.geometry import box as sbox

SKY = True                                              # Aussenbereich: keine Decke

from bm_models import engine_pod, floor_console, gas_pump, console_block, vent_grate
from bm_spec import art_floor, box, crate, cyl, railing, sprite, tube, wedge_box


def floor(ctx):
    holes = [sbox(-9.7, 0.85, -7.3, 4.1), sbox(-10.9, 0.25, -8.5, 1.9), sbox(-2.3, 0.3, -0.5, 4.8), sbox(-8.3, 0.25, -7.55, 1.0)]
    return art_floor(ctx, "floor_LaunchPad", holes)


def props(ctx):
    k = ctx.k
    p = []
    hull = ctx.color("lp_hull", (70, 84, 84))
    dark = ctx.color("lp_hull_dark", (41, 48, 49))
    grille = ctx.color("lp_grille", (148, 162, 165))
    shuttle = wedge_box(-7.35, -2.65, 4.35, 11.5, 0.45, 3.2, 5.6, 2.3, hull, outline=(19, 26, 26))
    shuttle["mats"] = [dark, dark, grille, hull, hull, hull, hull]
    p.append(shuttle)
    # Seitentriebwerke: liegende Zylinder mit Luefter-Einlauf (echte Koerper statt Bildkasten)
    p += engine_pod(ctx, "lp_pod_l", -8.57, 4.90, 6.60, 1.05, 0.95)
    p += engine_pod(ctx, "lp_pod_r", -1.53, 4.90, 6.60, 1.05, 0.95)
    yellow = ctx.color("lp_tank", (189, 152, 29))
    ys = ctx.color("lp_tank_shade", (105, 82, 28))
    p.append(tube([(-8.50, 1.20, 0.85), (-8.50, 3.15, 0.85)], 0.75, yellow, seg=40, outline=(56, 30, 5)))
    p.append(tube([(-8.50, 1.12, 0.85), (-8.50, 1.20, 0.85)], 0.5, ys, seg=32))
    stand = ctx.color("lp_stand", (90, 100, 110))
    for y in (1.45, 2.9):
        p.append(box(-8.5, y, 1.7, 0.2, 0.0, 0.42, stand, outline=(30, 34, 40)))
    # Kisten (Bildmitte der Oberseite -> Welt: y - k * (Sockel + Hoehe))
    for i, (x, y, s, rot, h, z0, side, top) in enumerate([
            (-10.15, 1.45, 0.85, 8, 0.94, 0.0, (62, 97, 89), (90, 129, 111)), (-10.05, 1.95, 0.55, -6, 0.45, 0.94, (62, 97, 89), (90, 129, 111)),
            (-9.00, 0.70, 0.55, 10, 0.55, 0.0, (62, 97, 89), (90, 129, 111)), (-7.90, 0.72, 0.50, 0, 0.50, 0.0, (110, 92, 70), (150, 128, 98)),
            (-1.55, 2.35, 0.85, -8, 0.90, 0.0, (62, 97, 89), (90, 129, 111)), (-1.10, 1.00, 0.60, 12, 0.55, 0.0, (62, 97, 89), (90, 129, 111)),
            (-1.90, 0.90, 0.55, -10, 0.50, 0.0, (110, 92, 70), (150, 128, 98)), (-1.75, 4.45, 0.90, 10, 0.90, 0.0, (62, 97, 89), (90, 129, 111)),
            (-1.55, 3.60, 0.55, -5, 0.55, 0.0, (62, 97, 89), (90, 129, 111)), (-0.90, 4.00, 0.70, 15, 0.60, 0.0, (63, 78, 96), (90, 108, 129))]):
        name = "lp_crate" if side[0] == 62 else ("lp_crate_brown" if side[0] == 110 else "lp_crate_blue")
        p.append(crate(ctx, name, x, y - k * (z0 + h), s, rot, h, z0, side, top, (24, 36, 33)))
    p += gas_pump(ctx, "lp_gascon", -6.84, 1.42, -6.14, 1.62, h=(2.37 - 1.42) / k, rgb=(110, 120, 125))
    p += console_block(ctx, "lp_padcon", -2.78, 1.08, -2.10, 1.32, (2.19 - 1.08) / k, rgb=(110, 120, 125), screens=2, seed=2)
    p += floor_console(ctx, "lp_stand", -6.32, 0.72, 0.56, 0.4, 1.25, body_rgb=(150, 160, 175), slope=False, screen_rgb=(120, 200, 220))
    fence = ctx.color("lp_fence", (102, 103, 113))
    for path in ([(-11.62, 0.12), (-11.62, 8.70), (-0.38, 8.70), (-0.38, 0.12)], [(-11.62, 0.12), (-7.20, 0.12)], [(-2.75, 0.12), (-0.38, 0.12)]):
        p += railing(path, 0.62, fence, r=0.03, outline=(40, 40, 48))
    chain = ctx.color("lp_chain", (60, 64, 70))
    for path in ([(-7.05, 4.0), (-7.05, 0.55)], [(-2.75, 4.0), (-2.75, 1.30)]):
        p += railing([(x, y - k * 0.5) for x, y in path], 0.5, chain, r=0.02, post_step=0.6, outline=(20, 22, 26))
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "LaunchPad/LaunchVent")
    p += vent_grate(ctx, "lp_vent", vx0, vy0, vx1, vy1)
    return p
