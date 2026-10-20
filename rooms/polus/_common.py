# Polus - gemeinsame Bausteine der Raumdateien (Sprites als 3D-Teile).

import bm_tex as T
from bm_spec import box, sprite, flat_rgb

VFAC = 0.8          # Gegenstaende: gezeichnete Fronthoehe ~0,8 der echten Hoehe (Waende: k 0,5)


def sprite_tex(ctx, suffix, name, crop=None, bg=(0, 0, 0)):
    """Sprite (oder Ausschnitt in Bildkoordinaten x0, y0, x1, y1) als Textur in Originalpalette."""
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
    """Ausschnitt des Kartenfotos (Bildkoordinaten) als Textur in Originalpalette."""
    import bm_style
    if bm_style.on(ctx.scene):
        return ctx.color(name, bm_style.median_rgb(ctx.ref.crop_full(x0, y0, x1, y1)))
    return ctx.tex(name, T.label_upscale(ctx.ref.crop_full(x0, y0, x1, y1), T.TPPU / ctx.ref.ppu), uv="part")


def front_box(ctx, name, x0, x1, y_front, depth, h, side_rgb, front_art, top_rgb=None, top_art=None, z0=0.0,
              outline=(20, 20, 24), bevel=0.0):
    """Moebel vor einer Wand: Front = Bildausschnitt front_art (x0, y0, x1, y1), Fuss bei y_front (Welt)."""
    side = ctx.color(f"{name}_side", side_rgb)
    top = ctx.color(f"{name}_top", top_rgb) if top_rgb else None
    if top_art:
        top = art_tex(ctx, f"{name}_toptex", *top_art)
    b = box((x0 + x1) / 2, y_front + depth / 2, x1 - x0, depth, z0, z0 + h, side, top=top, outline=outline, bevel=bevel)
    if front_art:
        b["front"] = art_tex(ctx, f"{name}_front", *front_art)
    return b


POTS = [(16.07, -16.42), (23.64, -16.44), (16.06, -18.87), (18.21, -18.85), (21.31, -18.85), (25.19, -20.69),
        (19.89, -20.69)]   # Topffuss (Bild), gefunden ueber die Topffarben (123,36,123)/(168,77,148)


def potted_plant(ctx, x, y_bot):
    """Topfpflanze (Office/Admin): Topf (168,77,148)/(123,36,123) auf dem Boden, duenner Stamm, Kugelkrone (16,93,66).
    Der Topf steht VOR der Wand: liegt die Rueckseite (Mitte + 0,13 nach Norden) in einer Wandmasse, rueckt er nach Sueden
    (Fehlerrunde 19.10. abends, #290/#291: Topf steckte in der Wand, nur die Krone ragte als gruene Scherben heraus)."""
    from shapely.geometry import Point as _P
    from bm_spec import blob, lathe, cyl
    pot = ctx.color("plant_pot", (168, 77, 148))
    potd = ctx.color("plant_pot_dark", (123, 36, 123))
    trunk = ctx.color("plant_trunk", (70, 52, 40))
    leaf = (ctx.color("plant_leaf_light", (40, 130, 90)), ctx.color("plant_leaf", (16, 93, 66)))
    cy = y_bot + 0.1
    sc = ctx.scene
    holes = getattr(sc, "wall_holes", [])

    def blocked(yy):
        q = _P(x, yy + 0.13)
        return (not sc.floor.contains(q)) or any(h.contains(q) for h in holes)
    for _ in range(20):
        if not blocked(cy):
            break
        cy -= 0.02
    out = [lathe(x, cy, [(0.0, 0.0), (0.085, 0.0), (0.11, 0.2), (0.12, 0.24), (0.0, 0.24)], pot, seg=20, outline=(60, 10, 60))]
    out.append(lathe(x, cy, [(0.0, 0.0), (0.086, 0.0), (0.095, 0.08), (0.0, 0.08)], potd, seg=20))
    out.append(cyl(x, cy, 0.1, 0.22, 0.245, ctx.color("plant_soil", (60, 44, 36)), seg=16))
    out.append(cyl(x, cy, 0.022, 0.24, 0.46, trunk, seg=8))
    out.append(blob(x, cy, 0.60, 0.18, 0.18, 0.17, leaf, seed=int(x * 100), outline=(8, 50, 34)))
    return out
