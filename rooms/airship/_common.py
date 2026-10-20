# Airship - gemeinsame Bausteine der Raumdateien.

import bm_tex as T
from bm_spec import box, cyl, sprite, flat_rgb, tube

VFAC = 0.8
LADDER = (196, 169, 71)
LADDER_DARK = (57, 35, 16)


def sprite_tex(ctx, suffix, name, crop=None, bg=(0, 0, 0)):
    img, (x0, y0, x1, y1) = sprite(ctx, suffix)
    if crop:
        W, H = img.size
        ax0, ay0, ax1, ay1 = crop
        img = img.crop((int(round((ax0 - x0) / (x1 - x0) * W)), int(round((y1 - ay1) / (y1 - y0) * H)),
                        int(round((ax1 - x0) / (x1 - x0) * W)), int(round((y1 - ay0) / (y1 - y0) * H))))
    import bm_style
    if bm_style.on(ctx.scene):
        # keine Spieltextur: Bildschirme als generische Anzeige, Flaechen in der gemessenen Farbe
        import re as _re
        cols = bm_style.sprite_colors(img)
        if _re.search(r"scr|mon|screen|display|tv|panel|radar|map", name, _re.I):
            asp = img.width / max(1, img.height)
            return ctx.tex(name, bm_style.ui_screen(cols, seed=len(name), w=160, h=max(40, int(160 / max(0.5, asp)))), uv="part")
        return ctx.color(name, cols[0][0])
    return ctx.tex(name, T.label_upscale(flat_rgb(img, bg), T.TPPU / ctx.ref.ppu), uv="part")


def art_tex(ctx, name, x0, y0, x1, y1):
    import bm_style
    if bm_style.on(ctx.scene):
        return ctx.color(name, bm_style.median_rgb(ctx.ref.crop_full(x0, y0, x1, y1)))
    return ctx.tex(name, T.label_upscale(ctx.ref.crop_full(x0, y0, x1, y1), T.TPPU / ctx.ref.ppu), uv="part")


def face(ctx, name, x0, x1, y, z0, z1, art=None, rgb=(73, 84, 97), depth=0.04):
    """Senkrechte Wandscheibe nach Sueden (Stegkante): Front = Bildausschnitt art (x0, y0, x1, y1)."""
    b = box((x0 + x1) / 2, y + depth / 2, x1 - x0, depth, z0, z1, ctx.color(f"{name}_side", rgb))
    if art:
        b["front"] = art_tex(ctx, f"{name}_art", *art)
    return b


def ladder(ctx, x, a, b, w=0.46, step=0.28):
    """Leiter von Punkt a nach b (je (y, z)) bei x: zwei Holme, Sprossen (196,169,71)."""
    import math
    wood = ctx.color("air_ladder", LADDER)
    (ya, za), (yb, zb) = a, b
    L = math.hypot(yb - ya, zb - za)
    out = [tube([(x - w / 2, ya, za), (x - w / 2, yb, zb)], 0.035, wood, seg=8, outline=LADDER_DARK),
           tube([(x + w / 2, ya, za), (x + w / 2, yb, zb)], 0.035, wood, seg=8, outline=LADDER_DARK)]
    n = max(2, int(L / step))
    for i in range(1, n):
        t = i / n
        y, z = ya + (yb - ya) * t, za + (zb - za) * t
        out.append(tube([(x - w / 2, y, z), (x + w / 2, y, z)], 0.025, wood, seg=6))
    return out


def sprite_block(ctx, suffix, name, h, side_rgb, line=(0, 0, 0), fk=None, bevel=0.02):
    """Gegenstand aus einem Sprite in AU-Schraegsicht: unten die Front (gezeichnet fk*h hoch), darueber die Oberseite
    in voller Tiefe. Grundriss = Spritebreite x (Spritehoehe - fk*h) ab der Unterkante."""
    import numpy as np
    from PIL import Image as _I
    fk = fk if fk is not None else ctx.k
    img, (x0, y0, x1, y1) = sprite(ctx, suffix)
    W, H = img.size
    ppm = H / (y1 - y0)
    fh = min(y1 - y0 - 0.1, fk * h)
    depth = max(0.1, (y1 - y0) - fh)
    cut = int(round(H - fh * ppm))
    flat = flat_rgb(img, side_rgb)
    side = ctx.color(f"{name}_side", side_rgb)
    top = ctx.tex(f"{name}_top", T.label_upscale(flat.crop((0, 0, W, max(1, cut))), T.TPPU / ctx.ref.ppu), uv="part")
    b = box((x0 + x1) / 2, y0 + depth / 2, x1 - x0, depth, 0.0, h, side, top=top, bevel=bevel, outline=line)
    b["front"] = ctx.tex(f"{name}_front", T.label_upscale(flat.crop((0, cut, W, H)), T.TPPU / ctx.ref.ppu), uv="part")
    return b
