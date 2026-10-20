# Skeld / Security - am Kartenfoto gemessen.
# Boden: Teal mit Lichtkegel (Zeichnung). Monitore und Serverschraenke = gezeichnete Fronten.
# Monitortisch (66,56,49) Oberseite im Bild x -13,85..-12,25, y -2,87..-2,50, Hoehe 0,45.
# Stuhl (security_chair) (107,106,74), L-Schreibtisch (104,85,63) Hoehe 0,45, Hocker (107,127,99) r 0,17 h 0,32.

# Ich-Sicht (Meldungen 18.10.): Pult zwischen den Schraegen vor der Nordwand (Kante -2,95 = Pultfront, Wand -2,77 aus
# dem Wandband, Streifen ueber _map.FLOOR_ADD_ROOMS), Oberseite = Zeichnung (-2,75..-2,47) -> Hoehe 0,45; Stuhl an
# seinem Collider (-13,30 | -3,19); Serverschrank an der Nordwestschraege aus dem Foto (wall_face_panel).

from shapely.geometry import Polygon, box as sbox

import bm_tex as T
from bm_spec import art_block, art_box, art_floor, box, cyl, office_chair, prism, vent, wall_face_panel

LINE = (16, 24, 24)


def floor(ctx):
    holes = [sbox(-13.9, -3.45, -12.2, -2.45), sbox(-12.85, -6.05, -11.8, -4.8), sbox(-12.85, -7.25, -12.2, -6.75)]
    return art_floor(ctx, "floor_Security", holes)


def props(ctx):
    k = ctx.k
    r = ctx.ref
    desk = Polygon([(-13.52, -2.95), (-12.60, -2.95), (-12.76, -2.79), (-13.36, -2.79)])
    bx0, by0, bx1, by1 = desk.bounds
    from bm_models import monitor
    parts = [prism(desk, 0.0, 0.45, ctx.color("sec_desk_side", (66, 56, 49)), top=ctx.color("sec_desk_top", (84, 70, 60)),
                   bevel=0.01, outline=(0, 0, 0))]
    parts += monitor(ctx, "sec_desk_mon", -13.06, -2.84, 0.45, 0.42, 0.3, yaw=0.0, screen_rgb=(90, 170, 120))
    parts.append(box(-13.06, -2.92, 0.3, 0.1, 0.45, 0.46, ctx.color("sec_keys", (40, 42, 46))))
    parts += office_chair(ctx, "sec_chair", -13.30, -3.19, (107, 106, 74), (70, 70, 50), (30, 30, 20), w=0.40, back_top=0.66)
    parts.append(wall_face_panel(ctx, "sec_servers", (-13.59, -2.97), (-14.42, -3.80), 0.0, 1.39, off=0.01))
    # L-Tisch auf seinem Collider (Laufkante -4,68 / -12,92 / -5,99), Oberseite = gezeichnetes L (-5,95..-4,85);
    # vorher um k*h nach Sueden verschoben, man stand im Tisch (Meldung 18.10.)
    L = Polygon([(-12.90, -4.70), (-11.95, -4.70), (-11.95, -5.97), (-12.36, -5.97), (-12.36, -5.22), (-12.90, -5.22)])
    parts.append(prism(L, 0.0, 0.45, ctx.color("sec_ldesk_side", (104, 85, 63)), top=ctx.color("sec_ldesk_top", (130, 108, 80)),
                       bevel=0.01, outline=LINE))
    parts.append(box(-12.4, -5.6, 0.22, 0.28, 0.45, 0.458, ctx.color("sec_paper", (236, 232, 220)), rot=6))
    top = ctx.color("sec_stool_top", (107, 127, 99))
    side = ctx.color("sec_stool_side", (66, 89, 66))
    parts.append(cyl(-12.62, -5.45 - k * 0.32, 0.17, 0.0, 0.32, side, top=top, seg=32, bevel=0.02, outline=LINE))
    parts += vent(ctx, "Security/Ground/SecurityVent")
    return parts
