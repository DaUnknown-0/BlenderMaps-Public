# Skeld / Shields - am Kartenfoto gemessen (zoomgrid.py, Raster 0,25).
# Aufbau wie Weapons: Plankenkreuz (begehbar) ueber einem Maschinendeck mit gelben Leiterbahnen. Gruben 0,6 tief:
#   Nordwest (Schildroehren an der Schraege, ausserhalb der Collider, wird dazugenommen), Ost (drei Roehren an der
#   Ostwand, innerhalb der Gelaenderkurve), Suedwest (zwischen Westarm und der unteren Stufe).
# Schildroehren (Sprites bulb ...): leuchtend (255,255,252), r 0,22, Sockel (74,89,96); stehen im Grubenboden, ihre
#   gezeichneten Fusspunkte liegen um k*d suedlicher. Gelaender (143,60,60) an allen Kanten Plattform/Grube.
# Konsole unten links auf Stufe (74,89,96). Emblem und Leiterbahnen = Zeichnung.

from shapely.geometry import box as sbox

from bm_spec import art_block, art_floor, box, cyl, lathe, pit_rails, vent

D = 0.6
WALL = (52, 64, 72)
PITS = [
    {"poly": [(6.88, -11.95), (8.1, -11.95), (8.5, -11.75), (8.85, -11.3), (8.95, -10.8), (8.95, -10.45), (7.65, -10.45),
              (6.88, -11.05)],
     "d": D, "add": True, "cut": "floor", "wall": WALL},                  # ragt in die Plattform, Schnitt = Bodenkante
    {"poly": [(10.35, -10.86), (11.95, -10.86), (11.95, -14.6), (10.30, -14.6), (10.42, -14.45), (10.45, -13.55),
              (10.62, -13.15), (10.70, -12.5), (10.62, -11.8), (10.42, -11.3)], "d": D, "wall": WALL},
    {"poly": [(7.05, -12.9), (7.85, -12.9), (8.3, -13.2), (8.72, -13.6), (8.72, -13.97), (7.05, -13.97)], "d": D, "add": True,
     "wall": WALL},
]
BULBS = [(7.38, -11.75), (7.65, -11.47), (7.87, -11.22), (8.12, -10.99), (11.50, -12.90), (11.50, -12.52), (11.50, -12.13)]


def floor(ctx):
    return art_floor(ctx, "floor_Shields", [])


def props(ctx):
    k = ctx.k
    parts = []
    red = ctx.color("shi_rail", (143, 60, 60))
    parts += pit_rails(ctx, red, z_top=0.42)
    # Grubenkante zur Comms-Nische (x 7,05): seit der senkrechte Wandbalken weg ist (User 19.10. abends), grenzt die
    # Grube 2 dort an Comms-Boden; pit_rails sieht nur die eigene Plattform -> Gelaender hier dazu
    from bm_spec import railing
    parts += railing([(7.07, -13.64), (7.07, -13.99), (7.26, -13.99)], 0.42, red, r=0.022, post_r=0.018, post_step=0.4)
    glow = ctx.glow("shi_bulb", (255, 255, 252), 0.8)
    sock = ctx.color("shi_socket", (74, 89, 96))
    prof = [(0.0, 0.12), (0.18, 0.14), (0.22, 0.25), (0.22, 1.05), (0.18, 1.18), (0.0, 1.22)]
    for bx, by in BULBS:
        by += k * D                                                      # gezeichnet tiefer -> Welt nordwaerts
        parts.append(cyl(bx, by, 0.24, -D, 0.14 - D, sock, seg=24, outline=(16, 24, 24)))
        parts.append(lathe(bx, by, [(r, z - D * 0.5) for r, z in prof], glow, seg=24))
        parts.append(cyl(bx, by, 0.2, 0.14 - D, 0.12 - D * 0.5, sock, seg=24))
    from bm_models import console_block
    from bm_spec import box as _box
    step = ctx.color("shi_step", (77, 94, 104))
    parts.append(_box(7.90, -14.56 - k * 0.12, 1.62, 0.82, 0.0, 0.12, step, bevel=0.02, outline=(0, 0, 0)))
    parts.append(_box(7.90, -14.56 - k * 0.12, 1.5, 0.7, 0.12, 0.125, ctx.color("shi_step_top", (90, 108, 118))))
    parts += console_block(ctx, "shi_console", 7.27, -14.05 - k * 0.62, 7.78, -13.72 - k * 0.62, 0.62, rgb=(74, 89, 96), screens=1, seed=2)
    parts += vent(ctx, "Shields/ShieldsVent")
    return parts
