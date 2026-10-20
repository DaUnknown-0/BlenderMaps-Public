# Polus / Admin - am Kartenfoto gemessen.
#
# Boden: violetter Teppich (Zeichnung). Fernseher an der Nordwand (Sprite dvdscreen) bleibt Wandzeichnung.
# Kartentisch (Sprite mapTable 23,02..24,77 / -22,17..-21,04): Gehaeuse, Oberseite = Sprite, Karte (map_admin)
#   leuchtet. Zwei Buecherregale (Front = Zeichnung), Topfpflanzen (_common).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _common import POTS, VFAC, front_box, potted_plant, sprite_tex               # noqa: E402
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, cyl, sprite, vent                             # noqa: E402

Z_MAP = 0.6


def floor(ctx):
    return art_floor(ctx, "floor_Admin", holes=[sbox(22.98, -22.2, 24.8, -21.0), sbox(21.5, -22.5, 21.9, -21.3),
                                               sbox(22.2, -24.7, 23.0, -23.8)]
                     + [sbox(x - 0.14, y - 0.02, x + 0.14, y + 0.6) for x, y in POTS if y < -19.5])


def admin_table(ctx):
    """Kartentisch in Zeichnungsmass (Fehlerrunde 19.10. abends, #292: war ein riesiger grauer Kasten, 0,4 zu weit
    suedlich im Laufweg): Grundflaeche = Collider ShortObjects mapTable (22,97..24,75 / -22,05..-21,08), schmaler Sockel,
    helle Tischplatte mit Rahmen, leuchtende Karte (Raster, Raumbloecke), links und rechts je ein Bedienpult mit Knoepfen."""
    from bm_spec import prism
    from shapely.geometry import box as _b
    x0, y0, x1, y1 = 22.99, -22.03, 24.73, -21.10
    base = ctx.color("ad_map_body", (92, 100, 108))
    frame = ctx.color("ad_map_rim", (176, 184, 190))
    dark = ctx.color("ad_map_dark", (60, 66, 72))
    glow = ctx.glow("ad_map_holo", (110, 220, 120), 1.6)
    line = ctx.glow("ad_map_hololine", (40, 120, 60), 1.2)
    btn = ctx.glow("ad_map_button", (90, 230, 120), 2.0)
    z_top = 0.52
    parts = [box((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 0.36, y1 - y0 - 0.3, 0.0, z_top - 0.08, base, bevel=0.02,
                 outline=(30, 34, 38))]
    parts.append(box((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, z_top - 0.08, z_top, frame, bevel=0.015,
                     outline=(30, 34, 38)))
    # Kartenfeld (eingelassen) mit Rasterlinien und Raumbloecken
    mx0, mx1, my0, my1 = 23.30, 24.42, -21.92, -21.22
    parts.append(box((mx0 + mx1) / 2, (my0 + my1) / 2, mx1 - mx0, my1 - my0, z_top - 0.004, z_top + 0.004, glow))
    for i in range(1, 6):
        xx = mx0 + (mx1 - mx0) * i / 6
        parts.append(box(xx, (my0 + my1) / 2, 0.012, my1 - my0 - 0.04, z_top + 0.004, z_top + 0.008, line))
    for i in range(1, 4):
        yy = my0 + (my1 - my0) * i / 4
        parts.append(box((mx0 + mx1) / 2, yy, mx1 - mx0 - 0.04, 0.012, z_top + 0.004, z_top + 0.008, line))
    for bx, by, bw, bd in ((23.45, -21.40, 0.22, 0.14), (23.85, -21.75, 0.30, 0.12), (24.20, -21.45, 0.16, 0.20),
                           (23.70, -21.36, 0.12, 0.10), (24.05, -21.80, 0.14, 0.10)):
        parts.append(prism(_b(bx - bw / 2, by - bd / 2, bx + bw / 2, by + bd / 2).difference(
            _b(bx - bw / 2 + 0.012, by - bd / 2 + 0.012, bx + bw / 2 - 0.012, by + bd / 2 - 0.012)), z_top + 0.004, z_top + 0.02, line))
    # Bedienpulte links/rechts (graue Kaesten mit gruenen Knoepfen, Zeichnung)
    for px in (23.13, 24.59):
        parts.append(box(px, (y0 + y1) / 2, 0.24, y1 - y0 - 0.12, z_top, z_top + 0.09, dark, bevel=0.01, outline=(30, 34, 38)))
        for by in (-21.75, -21.55, -21.35):
            parts.append(cyl(px, by, 0.035, z_top + 0.09, z_top + 0.105, btn, seg=12))
    return parts


def props(ctx):
    parts = []
    k = ctx.k
    from bm_models import map_table, shelf_unit
    parts += admin_table(ctx)
    # Buecherregale (#273..#275): Regal 1 steht an der Ostseite der Trennwand (x 21,62..21,92, Front Osten), Regal 2
    # vor der zweiten Trennwand (x 21,65..22,5, Front Sueden); dichte Buecherreihen statt grosser Kloetze
    from bm_models import bookcase
    parts += bookcase(ctx, "ad_shelf1", 21.62, -22.45, 21.94, -21.25, 1.3, facing="E", rgb=(70, 50, 40), shelves=4, seed=1)
    parts += bookcase(ctx, "ad_shelf2", 21.66, -24.88, 22.52, -24.52, 1.05, facing="S", rgb=(70, 50, 40), shelves=3, seed=2)
    for x, y in POTS:
        if y < -19.5:
            parts += potted_plant(ctx, x, y)
    parts += vent(ctx, "Admin/AdminVent")
    return parts
