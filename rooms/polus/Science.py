# Polus / Science (Labor: Wetterraum, Hauptlabor mit Balkon, Krankenstation, Flur) - am Kartenfoto gemessen.
#
# Boden: Zeichnung (weiss-blaue Fliesen, Teppich, Holz). Waende, Spinde, Waschraum, Schraenke: Zeichnung.
# Teleskop (Sprite telescope 33,44..34,30 / -5,66..-4,19) auf dem Balkon: Dreibein, Rohr (215,205,180) mit dunklem Band,
#   schraeg nach Nordwesten. Balkongelaender (182,182,173).
# Labortisch (Sprite sciencetable 33,96..35,77 / -7,67..-6,54): Platte = Sprite, Korpus (82,85,90)/(63,65,71),
#   Glaskolben (150,210,230).
# Krankenstation: vier Betten (Matratze (120,161,243), Rahmen (180,173,161), Kissen (193,210,210)), Vorhaenge
#   (57,76,174) an Stangen, Untersuchungsplattform (Sprite panel_medplatform) gruen/blau (99,153,162).
# Gruene Kiste (45,123,77) liegt gedreht im Flur (Bild 32,75..33,30 / -10,50..-9,95).

import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import VFAC, sprite_tex                                               # noqa: E402
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, cyl, lathe, railing, sprite, tube, vent       # noqa: E402

BEDS = [(37.86, -7.42, "N"), (38.88, -7.42, "N"), (37.86, -7.90, "S"), (38.88, -7.90, "S")]
Z_TABLE = 0.45


def floor(ctx):
    holes = [sbox(33.9, -7.7, 35.8, -6.5), sbox(33.4, -5.7, 34.3, -4.2), sbox(39.6, -7.55, 41.0, -6.65),
             sbox(32.7, -10.55, 33.35, -9.9)]
    holes += [sbox(x - 0.3, -7.5, x + 0.3, -6.6) for x, y, d in BEDS if d == "N"]
    return art_floor(ctx, "floor_Science", holes=holes)


def props(ctx):
    parts = []
    k = ctx.k
    # Teleskop auf dem Balkon (#263: wirkte als kurzer Scheinwerfer): Dreibein mit Kopf, langer schlanker Tubus mit
    # Taukappe, dunklen Ringen, Okular und Sucherfernrohr, schraeg nach Nordwesten
    tri = ctx.color("sc_tripod", (30, 32, 36))
    tubec = ctx.color("sc_scope", (215, 205, 180))
    band = ctx.color("sc_scope_band", (40, 42, 48))
    tx, ty = 33.86, -5.56                                             # Mitte des Colliders Science/telescope
    for a in (90, 210, 330):
        parts.append(tube([(tx, ty, 1.0), (tx + 0.38 * math.cos(math.radians(a)), ty + 0.38 * math.sin(math.radians(a)), 0.0)],
                          0.022, tri, seg=6))
    parts.append(cyl(tx, ty, 0.06, 0.95, 1.08, tri, seg=12, outline=(20, 20, 20)))
    tl = (50.0, 125.0, 1.12)
    parts.append(lathe(tx, ty, [(0.0, 0.55), (0.10, 0.55), (0.10, 1.75), (0.125, 1.8), (0.125, 2.05), (0.0, 2.05)], tubec, seg=24,
                       outline=(30, 30, 30), tilt=tl))
    parts.append(lathe(tx, ty, [(0.0, 1.70), (0.115, 1.70), (0.115, 1.80), (0.0, 1.80)], band, seg=24, tilt=tl))
    parts.append(lathe(tx, ty, [(0.0, 1.05), (0.108, 1.05), (0.108, 1.2), (0.0, 1.2)], band, seg=24, tilt=tl))
    parts.append(lathe(tx, ty, [(0.0, 0.42), (0.035, 0.42), (0.035, 0.56), (0.0, 0.56)], band, seg=12, tilt=tl))
    parts.append(lathe(tx + 0.07, ty + 0.06, [(0.0, 1.2), (0.03, 1.2), (0.03, 1.55), (0.0, 1.55)], band, seg=10, tilt=tl))
    # Balkongelaender
    rail = ctx.color("sc_rail", (182, 182, 173))
    # auf der Collider-Kante des Balkons (Science/Walls (32,62|-5,82)-(33,24|-5,26)-(34,97|-5,28)-(35,62|-5,86)); vorher
    # stand das Gelaender bis 0,2 jenseits der Bodenkante in der Luft (#300)
    parts += railing([(32.62, -5.82), (33.24, -5.27), (34.97, -5.29), (35.62, -5.86)], 0.55, rail,
                     r=0.025, post_step=0.3, post_r=0.02, outline=(40, 40, 40))
    # Labortisch
    from bm_models import microscope, scanner
    top = ctx.color("sc_table_top", (82, 85, 92))
    body = ctx.color("sc_table", (63, 65, 71))
    parts += microscope(ctx, "sc_micro", 34.35, -7.1 - k * Z_TABLE, Z_TABLE)
    _, (mx0, my0, mx1, my1) = sprite(ctx, "Science/panel_medplatform")
    parts += scanner(ctx, "sc_medplatform", (mx0 + mx1) / 2, my0 + 0.35, r=0.55, rgb=(170, 205, 210), side_rgb=(99, 153, 162))
    _, (x0, y0, x1, y1) = sprite(ctx, "Science/sciencetable")
    parts.append(box((x0 + x1) / 2, (y0 + y1) / 2 - k * Z_TABLE, x1 - x0, (y1 - y0) * 0.85, 0.0, Z_TABLE, body, top=top,
                     bevel=0.02, outline=(20, 20, 24)))
    glass = ctx.color("sc_flask", (150, 210, 230))
    for fx, fy in ((35.05, -6.75), (35.45, -6.95)):
        parts.append(lathe(fx, fy - k * Z_TABLE, [(0.0, Z_TABLE), (0.10, Z_TABLE), (0.11, Z_TABLE + 0.05), (0.05, Z_TABLE + 0.16),
                                                  (0.03, Z_TABLE + 0.28), (0.0, Z_TABLE + 0.28)], glass, seg=16,
                           outline=(40, 70, 90)))
    # Betten mit Vorhaengen (#264): Krankenbetten mit Fuessen, Kopf- und Fussteil, Matratze, Kissen, Decke;
    # Vorhaenge in Falten an den Reihenenden, Stange darueber (Unterkante 0,8: die Kamera stand im Gang darin)
    from bm_models import bed
    for x, ye, d in BEDS:
        if d == "N":
            parts += bed(ctx, "sc_bed", x - 0.3, ye, x + 0.3, -6.42, head="N", frame_rgb=(180, 173, 161),
                         mattress_rgb=(120, 161, 243), blanket_rgb=(80, 110, 200), pillow_rgb=(193, 210, 210), h_frame=0.3)
        else:
            # untere Reihe: Collider der Fussenden bei -8,22, Wand -8,6 (kurze Liegen, ragen nicht in den Gang)
            parts += bed(ctx, "sc_bed", x - 0.3, -8.6, x + 0.3, -8.24, head="S", frame_rgb=(180, 173, 161),
                         mattress_rgb=(120, 161, 243), blanket_rgb=(80, 110, 200), pillow_rgb=(193, 210, 210), h_frame=0.3)
    frame = ctx.color("sc_bed_frame", (180, 173, 161))
    cur = ctx.color("sc_curtain", (57, 76, 174))
    curd = ctx.color("sc_curtain_dark", (40, 54, 130))
    from bm_spec import obox
    for yrod in (-7.45, -8.22):
        parts.append(tube([(36.95, yrod, 1.45), (39.70, yrod, 1.45)], 0.018, frame, seg=6))
        for cx0, cx1 in ((36.95, 37.25), (39.40, 39.70)):
            n = 6
            for k in range(n):
                xa = cx0 + (cx1 - cx0) * k / n
                xb = cx0 + (cx1 - cx0) * (k + 1) / n
                yy = yrod + (0.03 if k % 2 else -0.03)
                parts.append(obox(((xa + xb) / 2, yy, 1.11), ((xb - xa) * 1.15, 0.015, 0.62), cur if k % 2 else curd,
                                  yaw=(30.0 if k % 2 else -30.0)))
    # Untersuchungsplattform
    _, (mx0, my0, mx1, my1) = sprite(ctx, "Science/panel_medplatform")
    ring = ctx.color("sc_platform", (99, 153, 162))
    pad = ctx.glow("sc_platform_pad", (110, 200, 140), 1.0)
    pcx, pcy = (mx0 + mx1) / 2, my0 + 0.32
    parts.append(cyl(pcx, pcy, 0.62, 0.0, 0.18, ring, ry=0.42, seg=48, bevel=0.03, outline=(16, 24, 24)))
    parts.append(cyl(pcx, pcy + 0.02, 0.38, 0.18, 0.2, pad, ry=0.25, seg=40))
    # Gruene Kiste im Flur
    # umgefallene Kabinentuer auf dem Flurboden (gruenes Quadrat der Zeichnung), flach statt Wuerfel (#261)
    parts.append(box(33.02, -10.22, 0.50, 0.46, 0.0, 0.035, ctx.color("sc_greenbox", (45, 123, 77)), rot=35, bevel=0.01,
                     outline=(23, 69, 41)))
    parts += _furnish(ctx)
    for v in ("Science/BathroomVent", "Science/SubBathroomVent"):
        parts += vent(ctx, v)
    return parts


def _furnish(ctx):
    """Einrichtung, die frueher nur Wandzeichnung war (Fehlerrunde 19.10., #261/#262/#265): Wetterraum (Teppich, Dielen,
    Computer, Temperaturmonitor, Aktenschrank, Papiere), Spindreihe im Flur, Waschraum mit Kabinen und Waschtisch."""
    import bm_style
    from bm_spec import obox, prism
    from shapely.geometry import box as _bx
    from bm_models import console_block, locker_row, monitor, stalls
    parts = []
    carpet = ctx.tex("sc_weather_carpet", bm_style.floor_image("carpet", (47, 98, 96), (36, 80, 78), seed=12), uv="world",
                     scale=[1.0, 1.0])
    wood = ctx.tex("sc_weather_wood", bm_style.floor_image("planks", (142, 118, 91), seed=13), uv="world", scale=[1.0, 1.0])
    room = ctx.scene.rooms.get("Science")
    for poly, m in ((_bx(28.95, -8.58, 30.6, -6.9), carpet), (_bx(30.6, -8.58, 32.4, -6.85), wood)):
        g = poly.intersection(room).buffer(-0.005) if room is not None else poly
        for q in getattr(g, "geoms", [g]):
            if q.geom_type == "Polygon" and q.area > 0.05:
                parts.append(prism(q, 0.0, 0.006, m))
    parts += console_block(ctx, "sc_weather_pc", 29.05, -7.08, 29.72, -6.58, 0.95, rgb=(200, 205, 210), screens=1, facing="S",
                           seed=21, screen_rgbs=[(90, 140, 230)])
    paper = ctx.color("sc_paper", (232, 230, 222))
    for i, (px, py, a) in enumerate(((29.35, -7.75, 20), (29.5, -8.05, -35), (29.3, -8.3, 60), (29.65, -7.9, 5))):
        parts.append(obox((px, py, 0.012 + i * 0.002), (0.21, 0.28, 0.004), paper, yaw=a))
    stand = ctx.color("sc_temp_stand", (70, 74, 86))
    parts.append(cyl(31.34, -6.75, 0.06, 0.0, 0.62, stand, seg=12, outline=(20, 20, 24)))
    parts.append(cyl(31.34, -6.75, 0.2, 0.0, 0.04, stand, seg=20))
    parts += monitor(ctx, "sc_temp_mon", 31.34, -6.75, 0.62, 0.5, 0.36, yaw=0.0, screen_rgb=(120, 200, 230))
    parts += locker_row(ctx, "sc_locker", 28.02, -9.40, 30.12, -8.96, h=1.2, n=6, facing="S", rgb=(54, 102, 85), dark=(24, 48, 40))
    # Waschraum (Zeichnung): erste Kabine x 32,6..33,26 offen (Tuer liegt im Flur, Vent darin), zwei Kabinen mit
    # Tueren (Front -9,78), Rueckwand -8,6; Waschtisch x 34,52..35,38 (Front -9,35) mit Spiegel an der Nordwand
    parts += stalls(ctx, "sc_stall", 33.26, -9.78, 34.50, n=2, depth=1.18, h=1.15, rgb=(45, 123, 77))
    counter = ctx.color("sc_sink", (210, 215, 220))
    basin = ctx.color("sc_sink_basin", (150, 160, 170))
    mirror = ctx.glow("sc_mirror", (170, 200, 215), 0.6)
    parts.append(box(34.95, -9.0, 0.86, 0.7, 0.0, 0.72, counter, bevel=0.015, outline=(40, 44, 50)))
    for bx_ in (34.74, 35.16):
        parts.append(cyl(bx_, -9.12, 0.13, 0.72, 0.735, basin, seg=16))
        parts.append(tube([(bx_, -8.75, 0.72), (bx_, -8.75, 0.84), (bx_, -8.85, 0.84)], 0.015, basin, seg=6))
    b = box(34.95, -8.67, 0.8, 0.02, 0.95, 1.3, mirror)
    b["front"] = mirror
    parts.append(b)
    return parts
