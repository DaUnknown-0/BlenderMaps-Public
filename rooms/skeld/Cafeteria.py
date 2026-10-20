# Skeld / Cafeteria - alle Werte am Kartenfoto gemessen (bm_analyze.py, Zoom-Bilder), siehe project_blender_maps.
#
# Boden: Rautengitter Abstand 0,2487, Phase (0,0516 | 0,0856); helle Rauten (176,178,162) auf (159,163,148),
#   Diagonale 0,444, Kachel 6x6 Plaetze (nur (i+j) ungerade), Muster per Autokorrelation verifiziert (584 Plaetze).
# Waende: Nordfronten = gezeichnetes Band (Fensterfront, Schraegen mit Postern); Seitenwaende im Stil der Schraegen:
#   Sockel (31,31,36), Altrosa (138,69,90), Petrol (84,133,146).
# Tische: Collider-Zehnecke 2,89 x 2,24 (oval, der Boden ist im Original unverzerrt). Hoehen aus dem Bildversatz
#   Platte/Bank: Sitz 0,25, Platte 0,41 (k * 0,16 = 0,095 gemessen). Platte rx 1,095 ry 0,76, Bankring aussen
#   1,455 x 1,065, Breite 0,28, Fugen oben/unten |x| < 0,135 bzw. 0,17, links/rechts |y| < 0,075.

import numpy as np
from PIL import Image
from shapely.geometry import box as sbox
from shapely.ops import unary_union

import bm_tex as T
from bm_spec import prism, cyl, box, ellipse, lathe, art_decals
PROCEDURAL = True      # zeichnet Boden/Waende selbst (keine Spieltextur), bleibt bei bm_style aktiv

S, X0, Y0 = 0.2487, 0.0516, 0.0856
SITES = {(0, 1): 1, (0, 3): 1, (0, 5): 0, (1, 0): 0, (1, 2): 0, (1, 4): 0, (2, 1): 1, (2, 3): 1, (2, 5): 0,
         (3, 0): 1, (3, 2): 0, (3, 4): 1, (4, 1): 0, (4, 3): 0, (4, 5): 0, (5, 0): 1, (5, 2): 0, (5, 4): 1}

TABLE_TOP = (66, 125, 162)
TABLE_SIDE = (74, 73, 49)
TABLE_LINE = (16, 36, 49)                                 # Konturfarbe der Tische und Baenke
Z_SEAT, Z_TOP = 0.25, 0.41

# Collider-Rechtecke der fuenf Tische (world.json, ShortObjects "Table ...")
TABLES = [(-4.83, 2.35, -1.93, 4.59), (0.10, 2.37, 2.99, 4.61), (-2.31, -0.28, 0.59, 1.96),
          (-4.85, -2.83, -1.96, -0.59), (0.14, -2.83, 3.03, -0.59)]


def floor(ctx):
    tile, P = T.diamond_tile(S, 0.222, (159, 163, 148), (176, 178, 162), SITES)
    return ctx.tex("floor_Cafeteria", tile, uv="world", scale=P, offset=[X0 - S / 2, Y0 - S / 2])


def side(ctx):
    H = ctx.H
    bands = [(0.0, 0.14, (31, 31, 36)), (0.14, 0.665, (138, 69, 90)), (0.665, 0.69, (121, 89, 109)),
             (0.69, 1.30, (84, 133, 146)), (1.30, 1.34, (79, 129, 143)), (1.34, 9.0, (38, 48, 46))]
    n = int(round(H * T.TPPU))
    img = np.zeros((n, 4, 3), np.uint8)
    for r in range(n):
        z = H - (r + 0.5) / T.TPPU
        img[r] = next(c for z0, z1, c in bands if z0 <= z < z1)
    return ctx.tex("side_Cafeteria", Image.fromarray(img), uv="world", scale=H)


def table(ctx, bb, top, side_, i):
    x0, y0, x1, y1 = bb
    cx = (x0 + x1) / 2
    cy_art = (y0 + 0.08 + y1 - 0.03) / 2                 # Bankring im Bild (ohne Frontband unten)
    cy = ctx.art_y(cy_art, Z_SEAT)                        # gemeinsamer Fusspunkt
    parts = []
    # Rund: Among Us zeichnet Oberseiten gestaucht (Platte 1,095 x 0,76 = Faktor 0,69), der Tisch selbst ist rund
    ring = ellipse(cx, cy, 1.455, 1.455).difference(ellipse(cx, cy, 1.175, 1.175))
    gaps = unary_union([sbox(cx - 0.135, cy, cx + 0.135, cy + 2), sbox(cx - 0.17 + 0.03, cy - 2, cx + 0.17 + 0.03, cy),
                        sbox(cx - 2, cy - 0.075, cx + 2, cy + 0.075)])
    for seg in getattr(ring.difference(gaps), "geoms", []):
        parts.append(prism(seg.simplify(0.002), 0.0, Z_SEAT, side_, top=top, bevel=0.025, outline=TABLE_LINE))
    parts.append(cyl(cx, cy, 0.22, 0.0, 0.31, side_, seg=32, outline=TABLE_LINE))                       # Saeule
    parts.append(cyl(cx, cy, 0.42, 0.0, 0.04, side_, seg=40, outline=TABLE_LINE))                        # Fuss
    parts.append(cyl(cx, cy, 1.095, Z_TOP - 0.10, Z_TOP, side_, top=top, seg=72, bevel=0.03, outline=TABLE_LINE))
    return parts


def props(ctx):
    top = ctx.color("caf_table_top", TABLE_TOP)
    side_ = ctx.color("caf_table_side", TABLE_SIDE)
    parts = []
    for i, bb in enumerate(TABLES):
        parts += table(ctx, bb, top, side_, i)
        # Kleinzeug auf der Platte (Papiere, Becher, Tablett, Laptop) als exakte Aufkleber der Zeichnung
        cx = (bb[0] + bb[2]) / 2
        cya = (bb[1] + 0.08 + bb[3] - 0.03) / 2 + 0.095     # Plattenmitte im Bild

        def keep(a, wx, wy, cx=cx, cya=cya, center=(i == 2)):
            e = ((wx - cx) / 1.03) ** 2 + ((wy - cya) / 0.70) ** 2 <= 1
            tab = np.abs(a - np.array(TABLE_TOP)).sum(-1) <= 18
            if center:                                     # Notfallknopf wird gebaut, nur der Aufdruck ist Aufkleber
                e &= ~((np.abs(wx - (-0.865)) < 0.33) & (np.abs(wy - 1.07) < 0.25))
            return e & ~tab

        def clean(a):
            white = (a == 255).all(-1) | ((a >= 240).all(-1))
            a[white] = TABLE_TOP                           # Hervorhebungsrand benutzbarer Dinge gehoert nicht dazu
            return a
        parts += art_decals(ctx, f"caf_items_{i}", (cx - 1.05, cya - 0.72, cx + 1.05, cya + 0.72), Z_TOP, keep, clean=clean)
    # Notfallknopf auf dem mittleren Tisch: Sockel mit Gefahrenrahmen (Sprite als Oberseite), Glas, Kuppel
    r = ctx.ref
    sp = next(p for p in r.world["props"] if p["path"].endswith("Cafeteria/Ground/EmergencyConsole"))
    a, b, w, h = sp["rect"]
    from PIL import Image as _Im, ImageDraw as _Dr
    _im = _Im.new("RGB", (160, 160), (70, 74, 78))
    _d = _Dr.Draw(_im)
    for _i in range(0, 320, 24):                                      # Gefahrenstreifen gelb/schwarz
        _d.polygon([(_i, 0), (_i + 12, 0), (_i + 12 - 160, 160), (_i - 160, 160)], fill=(230, 190, 40))
    _d.ellipse([28, 28, 132, 132], fill=(60, 60, 64), outline=(20, 20, 24), width=4)
    _d.ellipse([40, 40, 120, 120], fill=(200, 40, 40), outline=(120, 20, 20), width=3)
    etop = ctx.tex("caf_emergency_top", _im, uv="part")
    (sx0, sy0), (sx1, sy1) = sp["min"], sp["max"]
    ecx = (sx0 + sx1) / 2
    ecy = ctx.art_y((sy0 + sy1) / 2, Z_TOP + 0.08)
    frame = ctx.color("caf_emergency_frame", (60, 62, 70))
    parts.append(box(ecx, ecy, sx1 - sx0 - 0.06, (sy1 - sy0) * 0.8, Z_TOP, Z_TOP + 0.08, frame, top=etop, bevel=0.01,
                     outline=(20, 20, 24)))
    dome = ctx.color("caf_emergency_dome", (232, 120, 150))
    parts.append(lathe(ecx, ecy + 0.02, [(0.0, Z_TOP + 0.08), (0.11, Z_TOP + 0.08), (0.105, Z_TOP + 0.12), (0.07, Z_TOP + 0.16),
                                         (0.0, Z_TOP + 0.175)], dome, seg=32, outline=(20, 20, 24)))
    return parts
