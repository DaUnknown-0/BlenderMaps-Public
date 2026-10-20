# bm_spec.py - Bausteine fuer Raumspezifikationen (rooms/<karte>/<Raum>.py).
#
# Eine Raumdatei kann definieren (alles optional, sonst gilt die Vorgabe aus bm_scene):
#   floor(ctx)        -> Materialname des Bodens
#   north(ctx, e)     -> Materialname fuer eine Nordwandkante e (dict a, b, len, n) oder None = Zeichnung
#   side(ctx)         -> Materialname der Seitenwaende
#   props(ctx)        -> Liste von Bauteilen (siehe unten)
#   H                 -> eigene Raumhoehe
#
# Bauteile sind dicts, die blender/bm_build.py versteht:
#   prism(poly, z0, z1, mat, top=None, bevel=0)      Grundriss (Liste von (x, y) oder shapely-Polygon) senkrecht extrudiert
#   cyl(cx, cy, r, z0, z1, mat, top=None, seg=48, ry=None, bevel=0)   (Ellipse, wenn ry gesetzt)
#   box(cx, cy, sx, sy, z0, z1, mat, rot=0, top=None, bevel=0)
#   lathe(cx, cy, prof[(r, z)], mat, seg=48)
# "top" = eigenes Material fuer die Oberseite (z. B. Bildtextur, UV ueber das Rechteck der Oberseite).
#
# Lage aus der Zeichnung: Among Us zeigt einen Punkt in Hoehe z um k*z nach Norden versetzt; art_y(y, z) rechnet die
# gemessene Bildlage auf die Weltlage zurueck.

import math

from shapely.geometry import Polygon, box as sbox
from shapely import affinity


def _poly(p):
    if isinstance(p, Polygon):
        return [list(map(lambda v: round(v, 5), c)) for c in list(p.exterior.coords)[:-1]]
    return [list(c) for c in p]


def prism(poly, z0, z1, mat, top=None, bevel=0.0, holes=(), outline=None, front=None):
    d = {"type": "prism", "pts": _poly(poly), "z0": z0, "z1": z1, "mat": mat, "bevel": bevel}
    if front:
        d["front"] = front
    if outline:
        d["outline"] = list(outline)
    if isinstance(poly, Polygon) and poly.interiors:
        d["holes"] = [[list(c) for c in list(h.coords)[:-1]] for h in poly.interiors]
    if top:
        d["top"] = top
    return d


def ellipse(cx, cy, rx, ry, seg=64):
    return Polygon([(cx + rx * math.cos(2 * math.pi * i / seg), cy + ry * math.sin(2 * math.pi * i / seg)) for i in range(seg)])


def cyl(cx, cy, r, z0, z1, mat, top=None, seg=48, ry=None, bevel=0.0, outline=None):
    return prism(ellipse(cx, cy, r, ry if ry is not None else r, seg), z0, z1, mat, top, bevel, outline=outline)


def box(cx, cy, sx, sy, z0, z1, mat, rot=0.0, top=None, bevel=0.0, outline=None):
    b = affinity.rotate(sbox(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2), rot, origin=(cx, cy))
    return prism(b, z0, z1, mat, top, bevel, outline=outline)


def mesh(verts, faces, mat, outline=None, mats=None):
    """Freies Netz: verts [(x, y, z)], faces [(i, j, k, ...)] gegen den Uhrzeigersinn von aussen; mats je Flaeche optional."""
    d = {"type": "mesh", "verts": [list(v) for v in verts], "faces": [list(f) for f in faces], "mat": mat}
    if mats:
        d["mats"] = list(mats)
    if outline:
        d["outline"] = list(outline)
    return d


def wedge_box(x0, x1, y0, y1, z0, z1, ynose, znose, mat, outline=None):
    """Kasten x0..x1 / y0..y1 / z0..z1, dessen Suedseite als Schraege von (y0, z0..znose) nach (ynose, z1) laeuft."""
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),          # Boden 0-3
         (x0, y0, znose), (x1, y0, znose), (x0, ynose, z1), (x1, ynose, z1), (x1, y1, z1), (x0, y1, z1)]   # 4-9
    f = [(3, 2, 1, 0), (0, 1, 5, 4), (4, 5, 7, 6), (6, 7, 8, 9), (2, 3, 9, 8), (1, 2, 8, 7, 5), (0, 4, 6, 9, 3)]
    return mesh(v, f, mat, outline=outline)


def tube(pts, r, mat, seg=10, outline=None):
    """Rohr/Gelaender entlang einer Linie aus (x, y, z)-Punkten."""
    d = {"type": "tube", "pts": [list(p) for p in pts], "r": r, "mat": mat, "seg": seg}
    if outline:
        d["outline"] = list(outline)
    return d


def railing(path, z_top, mat, r=0.035, post_step=0.45, post_r=0.028, outline=None):
    """Gelaender: Handlauf auf z_top entlang path [(x, y)], Pfosten etwa alle post_step, Mittelholm auf halber Hoehe."""
    import math as _m
    parts = [tube([(x, y, z_top) for x, y in path], r, mat, outline=outline),
             tube([(x, y, z_top * 0.5) for x, y in path], r * 0.7, mat, outline=outline)]
    acc, posts = 0.0, [path[0]]
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        L = _m.hypot(x1 - x0, y1 - y0)
        t = post_step - acc
        while t < L:
            posts.append((x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L))
            t += post_step
        acc = (acc + L) % post_step
    posts.append(path[-1])
    for x, y in posts:
        parts.append(tube([(x, y, 0.0), (x, y, z_top)], post_r, mat, outline=outline))
    return parts


def lathe(cx, cy, prof, mat, seg=48, outline=None, tilt=None):
    """Drehkoerper um die senkrechte Achse durch (cx, cy); tilt = (Grad, Richtung Grad, Drehpunkt-z) neigt ihn."""
    d = {"type": "lathe", "c": [cx, cy], "prof": [list(p) for p in prof], "mat": mat, "seg": seg}
    if tilt:
        d["tilt"] = list(tilt)
    if outline:
        d["outline"] = list(outline)
    return d


def art_decals(ctx, name, region, z, keep, thick=0.012, min_px=25, upscale=128, close=1, clean=None):
    """Flache Gegenstaende aus der Zeichnung: region = (x0, y0, x1, y1) in BILDkoordinaten, keep(rgb-Array, xx, yy)
    -> Maske der Gegenstandspixel. Jeder Fleck wird ein duennes Prisma auf Hoehe z (zurueckprojiziert um k*z),
    Oberseite = Zeichnung des Ausschnitts in Originalpalette, Umriss = vektorisierte Maske.
    Prozedurale Karten: entfaellt (nichts Aufgemaltes)."""
    if _proc(ctx):
        return []
    import cv2
    import numpy as np
    import bm_tex as T
    r = ctx.ref
    x0, y0, x1, y1 = region
    im = r.crop_full(x0, y0, x1, y1)
    if clean is not None:
        from PIL import Image as _Im
        im = _Im.fromarray(clean(np.asarray(im).copy()).astype(np.uint8))
    a = np.asarray(im).astype(int)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    wx, wy = x0 + (xx + 0.5) / r.ppu, y1 - (yy + 0.5) / r.ppu
    m = keep(a, wx, wy).astype(np.uint8)
    if close:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    sc = upscale / r.ppu
    tex = T.label_upscale(im, sc)
    dy = ctx.k * z
    tname = ctx.tex(name, tex, uv="bbox", bbox=[x0, y0 - dy, x1, y1 - dy])
    parts = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < min_px:
            continue
        blob = (lab == i).astype(np.uint8)
        big = cv2.resize(blob, (w * 4, h * 4), interpolation=cv2.INTER_LINEAR)
        cs, _ = cv2.findContours((big > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)
        pts = [(x0 + (p[0][0] + 0.5) / (4 * r.ppu), y1 - (p[0][1] + 0.5) / (4 * r.ppu) - dy) for p in c]
        pg = Polygon(pts).buffer(0).simplify(0.006)
        if pg.geom_type != "Polygon" or pg.area < 1e-4:
            continue
        parts.append(prism(pg, z, z + thick, tname, top=tname))
    return parts


def sprite(ctx, suffix):
    """Sprite aus dem Bogen des Spiels: (RGBA-Bild, Weltrechteck x0, y0, x1, y1 der Zeichnung)."""
    r = ctx.ref
    p = next(p for p in r.world["props"] if p["path"].endswith(suffix))
    a, b, w, h = p["rect"]
    return r.sheet.crop((a, b, a + w, b + h)), (*p["min"], *p["max"])


def flat_rgb(img, bg=(0, 0, 0)):
    """RGBA -> RGB, durchsichtige Pixel bekommen bg."""
    from PIL import Image as _Im
    base = _Im.new("RGB", img.size, bg)
    base.paste(img, (0, 0), img)
    return base


def _Image_NEAREST():
    from PIL import Image
    return Image.NEAREST


def vent(ctx, suffix, z=0.0, h=0.02, line=(20, 28, 30)):
    """Bodengitter als Koerper: Rahmen mit Fase, dunkle Oeffnung, Stege (User 18.10.: nichts aufgemalt)."""
    from bm_models import vent_grate
    _, (x0, y0, x1, y1) = sprite(ctx, suffix)
    return vent_grate(ctx, "vent_" + suffix.replace("/", "_"), x0, y0, x1, y1, z=z)


def _proc(ctx):
    import bm_style
    return bm_style.on(ctx.scene)


def art_floor(ctx, name, holes=(), radius=4, period_x=None, period_y=None):
    """Boden aus der Zeichnung (Originalpalette, hochskaliert); Stellen unter gebauten Objekten (holes: shapely-
    Geometrien in Bildkoordinaten) werden aus der Umgebung ergaenzt, damit unter Moebeln kein Abbild liegt.
    Prozedurale Karten (bm_style): Bodenkachel des Raums in gemessener Farbe."""
    if _proc(ctx):
        import bm_style
        return bm_style.style_for(ctx).floor
    import cv2
    import numpy as np
    from PIL import Image as _Im
    import bm_tex as T
    r = ctx.ref
    x0, y0, x1, y1 = ctx.poly.bounds
    x0 -= 0.3; y0 -= 0.3; x1 += 0.3; y1 += 0.3
    im = np.asarray(r.crop(x0, y0, x1, y1)).copy()
    h, w = im.shape[:2]
    m = np.zeros((h, w), np.uint8)
    for g in holes:
        for pg in getattr(g, "geoms", [g]):
            pts = np.array([((px - x0) * r.ppu, (y1 - py) * r.ppu) for px, py in pg.exterior.coords], np.int32)
            cv2.fillPoly(m, [pts], 1)
    if m.any() and (period_x or period_y):
        # Muster periodisch fortsetzen: Pixel aus derselben Reihe um Vielfache der Periode verschoben
        done = np.zeros_like(m)
        for axis, P in ((1, period_x), (0, period_y)):
            if not P:
                continue
            step = P * r.ppu
            for n in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5):
                todo = (m > 0) & (done == 0)
                if not todo.any():
                    break
                ys, xs = np.nonzero(todo)
                if axis == 1:
                    sx_ = np.round(xs + n * step).astype(int); sy_ = ys
                else:
                    sy_ = np.round(ys + n * step).astype(int); sx_ = xs
                ok = (sx_ >= 0) & (sx_ < w) & (sy_ >= 0) & (sy_ < h)
                ys, xs, sy_, sx_ = ys[ok], xs[ok], sy_[ok], sx_[ok]
                good = m[sy_, sx_] == 0
                im[ys[good], xs[good]] = im[sy_[good], sx_[good]]
                done[ys[good], xs[good]] = 1
        m = ((m > 0) & (done == 0)).astype(np.uint8)
    if m.any():
        pal = T.palette_of(_Im.fromarray(im))
        im = cv2.inpaint(im, m, radius, cv2.INPAINT_TELEA)
        # Ergaenztes zurueck auf die Palette (keine Zwischentoene erfinden)
        d = np.abs(im[:, :, None, :].astype(int) - pal[None, None, :, :]).sum(-1)
        im = np.where(m[:, :, None] > 0, pal[d.argmin(-1)], im).astype(np.uint8)
    up = T.label_upscale(_Im.fromarray(im), T.TPPU / r.ppu)
    return ctx.tex(name, up, uv="bbox", bbox=[x0, y0, x1, y1])


def art_box(ctx, x0, y0a, x1, y1a, z0, z1, mat, top=None, bevel=0.0, outline=None):
    """Quader, dessen OBERSEITE im Bild bei y0a..y1a liegt (Bildkoordinaten): Weltlage = Bild - k*z1."""
    dy = ctx.k * z1
    return box((x0 + x1) / 2, (y0a + y1a) / 2 - dy, x1 - x0, y1a - y0a, z0, z1, mat, top=top, bevel=bevel, outline=outline)


def side_from_column(ctx, name, x, y_base, art_h=None, spread=0.06):
    """Seitenwand-Textur aus einer gemessenen Spalte des gezeichneten Wandbands (Bildkoordinaten: Wandfuss bei
    y_base, Oberkante art_h darueber), Median ueber +-spread, auf Raumhoehe gestreckt, Originalpalette."""
    import numpy as np
    from PIL import Image as _Im
    import bm_tex as T
    r = ctx.ref
    if _proc(ctx):
        import bm_style
        return bm_style.style_for(ctx).wall
    art_h = art_h or ctx.k * ctx.H
    n = int(round(ctx.H * T.TPPU))
    cols = []
    for dx in np.linspace(-spread, spread, 7):
        col = []
        for i in range(n):
            ya = y_base + art_h * (1 - (i + 0.5) / n)              # Zeile 0 = oben
            px, py = r.w2p(x + dx, ya)
            col.append(r.img_base[int(py), int(px)])
        cols.append(col)
    a = np.median(np.array(cols, np.float64), axis=0)
    strip = np.repeat(a[:, None, :], 4, axis=1).astype(np.uint8)
    pal = T.palette_of(_Im.fromarray(strip), min_px=3)
    d = np.abs(strip[:, :, None, :].astype(int) - pal[None, None, :, :]).sum(-1)
    strip = pal[d.argmin(-1)].astype(np.uint8)
    return ctx.tex(name, _Im.fromarray(strip), uv="world", scale=ctx.H)


def side_from_window(ctx, name, north, art_h=None, size=256):
    """Seitenwand-Textur aus dem schlichtesten Fenster des gezeichneten Nordbands (Breite = Raumhoehe H, damit die
    Kachel quadratisch entlang der Wand wiederholt): traegt Fussleiste, Oberkante und Paneelfugen der Zeichnung
    statt einer einzelnen gestreckten Spalte (Meldungen 18.10.: "einfarbige Waende"). None, wenn kein Nordband
    lang genug ist (dann side_from_column)."""
    import numpy as np
    from PIL import Image as _Im
    import bm_tex as T
    if _proc(ctx):
        import bm_style
        return bm_style.style_for(ctx).wall
    r = ctx.ref
    H = ctx.H
    art_h = art_h or ctx.k * H
    W = H
    best = None
    for e in north:
        if e["len"] < W + 0.1:
            continue
        (ax, ay), (bx, by) = e["a"], e["b"]
        if abs(by - ay) > 0.02 * abs(bx - ax):
            continue                                                   # nur waagerechte Fronten
        x_lo, x_hi = min(ax, bx) + W / 2, max(ax, bx) - W / 2
        n = max(2, int((x_hi - x_lo) / 0.1))
        for i in range(n + 1):
            xc = x_lo + (x_hi - x_lo) * i / n
            cols = []
            for dx in np.linspace(-W / 2, W / 2, 11):
                cols.append(np.array([r.img_base[int(r.w2p(xc + dx, ay + art_h * t)[1]), int(r.w2p(xc + dx, ay + art_h * t)[0])]
                                      for t in np.linspace(0.05, 0.9, 24)], float))
            d = np.mean([np.abs(cols[j] - cols[j + 1]).mean() for j in range(len(cols) - 1)])
            if best is None or d < best[0]:
                best = (d, xc, ay)
    if best is None:
        return None
    _, xc, y0 = best
    p0 = r.w2p(xc - W / 2, y0 + art_h)
    p1 = r.w2p(xc + W / 2, y0)
    im = _Im.fromarray(r.img_base).crop((int(round(p0[0])), int(round(p0[1])), int(round(p1[0])), int(round(p1[1]))))
    if im.width < 4 or im.height < 4:
        return None
    im = im.resize((size, size), _Im.LANCZOS)
    pal = T.palette_of(im, min_px=12)
    a = np.asarray(im).astype(int)
    d = np.abs(a[:, :, None, :] - pal[None, None, :, :]).sum(-1)
    im = _Im.fromarray(pal[d.argmin(-1)].astype(np.uint8))
    return ctx.tex(name, im, uv="world", scale=H)


def art_region(ctx, seed, tol=26, box_=None, close=2, simplify=0.008):
    """Flaeche der Zeichnung um einen Saatpunkt (Bildkoordinaten), Flutfuellung bis Farbabstand tol (stoppt an den
    dunklen Konturen). box_ = (x0, y0, x1, y1) begrenzt die Suche. Rueckgabe: shapely-Polygon in Bildkoordinaten."""
    import cv2
    import numpy as np
    r = ctx.ref
    x0, y0, x1, y1 = box_ or (seed[0] - 2, seed[1] - 2, seed[0] + 2, seed[1] + 2)
    im = np.ascontiguousarray(np.asarray(r.crop_full(x0, y0, x1, y1)))
    h, w = im.shape[:2]
    sx, sy = int((seed[0] - x0) * r.ppu), int((y1 - seed[1]) * r.ppu)
    mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(im.copy(), mask, (sx, sy), (0, 0, 0), (tol,) * 3, (tol,) * 3,
                  cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8) | 4)
    m = (mask[1:-1, 1:-1] > 0).astype(np.uint8)
    if close:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close * 2 + 1,) * 2, np.uint8))
    big = cv2.resize(m, (w * 4, h * 4), interpolation=cv2.INTER_LINEAR)
    cs, _ = cv2.findContours((big > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cs, key=cv2.contourArea)
    pts = [(x0 + (p[0][0] + 0.5) / (4 * r.ppu), y1 - (p[0][1] + 0.5) / (4 * r.ppu)) for p in c]
    return Polygon(pts).buffer(0).simplify(simplify)


def art_container(ctx, name, x0, x1, y_base, y_top_front, y_top_back, side_rgb, z0=0.0, outline=None, bevel=0.0):
    """Quader, wie Among Us ihn zeichnet: Front im Bild von y_base (Fuss) bis y_top_front, Oberseite von dort bis
    y_top_back. Hoehe = Fronthoehe / k; Front und Oberseite tragen die Zeichnung, die Seiten side_rgb.
    z0 > 0: steht auf etwas (y_base ist dann die Bildlage der Unterkante)."""
    import bm_tex as T
    k = ctx.k
    h = (y_top_front - y_base) / k
    z1 = z0 + h
    yf = y_base - k * z0                                     # Weltlage der Frontflaeche
    depth = y_top_back - y_top_front
    from shapely.geometry import box as _b
    r = ctx.ref
    if _proc(ctx):
        import bm_style
        top = ctx.color(f"{name}_top", bm_style.median_rgb(r.crop_full(x0, y_top_front, x1, y_top_back)))
        fcol = bm_style.median_rgb(r.crop_full(x0, y_base, x1, y_top_front))
        fr = ctx.tex(f"{name}_front", bm_style.wall_image("panels", fcol, H=max(0.2, h), seed=len(name)), uv="part")
        side = ctx.color(f"{name}_side", side_rgb)
        return prism(_b(x0, yf, x1, yf + depth), z0, z1, side, top=top, bevel=bevel, outline=outline, front=fr), z1
    top = ctx.tex(f"{name}_top", T.label_upscale(r.crop_full(x0, y_top_front, x1, y_top_back), T.TPPU / r.ppu), uv="part")
    fr = ctx.tex(f"{name}_front", T.label_upscale(r.crop_full(x0, y_base, x1, y_top_front), T.TPPU / r.ppu), uv="part")
    side = ctx.color(f"{name}_side", side_rgb)
    return prism(_b(x0, yf, x1, yf + depth), z0, z1, side, top=top, bevel=bevel, outline=outline, front=fr), z1


def art_block(ctx, name, poly_art, z0, z1, side_rgb, outline=None, bevel=0.0, grow=0.0, tex=True):
    """Prisma, dessen Oberseite im Bild poly_art ist (Weltlage = Bild - k*z1), Oberseite = Zeichnung."""
    import bm_tex as T
    dy = ctx.k * z1
    pw = affinity.translate(poly_art.buffer(grow, join_style=2) if grow else poly_art, 0, -dy)
    side = ctx.color(f"{name}_side", side_rgb)
    top = None
    if tex and _proc(ctx):
        import bm_style
        bx0, by0, bx1, by1 = poly_art.bounds
        top = ctx.color(f"{name}_top", bm_style.median_rgb(ctx.ref.crop_full(bx0, by0, bx1, by1)))
    elif tex:
        bx0, by0, bx1, by1 = poly_art.bounds
        bx0 -= 0.05; by0 -= 0.05; bx1 += 0.05; by1 += 0.05
        img = ctx.ref.crop_full(bx0, by0, bx1, by1)
        top = ctx.tex(f"{name}_top", T.label_upscale(img, T.TPPU / ctx.ref.ppu), uv="bbox", bbox=[bx0, by0 - dy, bx1, by1 - dy])
    return prism(pw, z0, z1, side, top=top, bevel=bevel, outline=outline)


def art_box(ctx, name, poly, h, side_rgb, y_base=None, y_top=None, z0=0.0, outline=None, bevel=0.0, front=True):
    """Moebel mit fester Grundflaeche poly (= Collider, damit es nicht in den Laufbereich ragt; Meldungen 18.10.) und
    Hoehe h. Front (Suedseite) = Zeichnung von y_base (Fuss im Bild, Standard Suedkante) bis y_base + k*h, Oberseite =
    Zeichnung von dort bis y_top (Standard Nordkante + k*h), auf die Grundflaeche gestreckt."""
    import bm_tex as T
    k, r = ctx.k, ctx.ref
    x0, y0, x1, y1 = poly.bounds
    yb = y0 + k * z0 if y_base is None else y_base
    yf = yb + k * h
    yt = y1 + k * (z0 + h) if y_top is None else y_top
    up = T.TPPU / r.ppu
    if _proc(ctx):
        import bm_style
        top = ctx.color(f"{name}_top", bm_style.median_rgb(r.crop_full(x0, yf, x1, max(yf + 0.02, yt))))
        fr = None
        if front:
            fcol = bm_style.median_rgb(r.crop_full(x0, yb, x1, yf))
            fr = ctx.tex(f"{name}_front", bm_style.wall_image("panels", fcol, H=max(0.2, h), seed=len(name)), uv="part")
        return prism(poly, z0, z0 + h, ctx.color(f"{name}_side", side_rgb), top=top, bevel=bevel, outline=outline, front=fr)
    top = ctx.tex(f"{name}_top", T.label_upscale(r.crop_full(x0, yf, x1, max(yf + 0.02, yt)), up), uv="bbox",
                  bbox=[x0, y0, x1, y1])
    fr = ctx.tex(f"{name}_front", T.label_upscale(r.crop_full(x0, yb, x1, yf), up), uv="part") if front else None
    return prism(poly, z0, z0 + h, ctx.color(f"{name}_side", side_rgb), top=top, bevel=bevel, outline=outline, front=fr)


def wall_face_panel(ctx, name, a, b, z0, z1, off=0.02, depth=0.03, ppu=128):
    """Duenne Platte vor der Wand a -> b (Raum links der Richtung a -> b), Front = Foto (mit allen Objekten) der
    Wandflaeche, entzerrt: Punkt (s, z) der Wand liegt im Bild bei Weltlage + k*z nach Norden. Fuer Gezeichnetes an
    schraegen Waenden, das sonst verloren ginge (Security-Serverschrank, Meldungen 18.10.). Die Front muss nach Sueden
    zeigen (Wand mit Raum auf der Suedseite), sonst greift die Frontzuordnung in bm_build nicht."""
    import cv2
    import numpy as np
    from PIL import Image as _Im
    r, k = ctx.ref, ctx.k
    (ax, ay), (bx, by) = a, b
    L = math.hypot(bx - ax, by - ay)
    dx, dy = (bx - ax) / L, (by - ay) / L
    nx, ny = -dy, dx                                                   # zum Raum (links)
    W, H = max(8, int(L * ppu)), max(8, int((z1 - z0) * ppu))
    s = (np.arange(W) + 0.5) / W * L
    z = z1 - (np.arange(H) + 0.5) / H * (z1 - z0)
    S, Z = np.meshgrid(s, z)
    X = ax + S * dx
    Y = ay + S * dy + k * Z
    img = np.asarray(r.full_image)
    px = ((X - r.mn[0]) * r.ppu).astype(np.float32)
    py = ((r.mx[1] - Y) * r.ppu).astype(np.float32)
    face = cv2.remap(img, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if _proc(ctx):
        # Platte in der gemessenen Farbe mit Paneelmuster (kein Foto)
        import bm_style
        col = tuple(int(v) for v in np.median(face.reshape(-1, 3), axis=0))
        o1, o2 = off, off + depth
        pts = [(ax + nx * o1, ay + ny * o1), (bx + nx * o1, by + ny * o1), (bx + nx * o2, by + ny * o2), (ax + nx * o2, ay + ny * o2)]
        m = ctx.tex(name + "_face", bm_style.wall_image("panels", col, H=max(0.3, z1 - z0), seed=len(name)), uv="world",
                    scale=[max(0.3, z1 - z0), max(0.3, z1 - z0)])
        return prism(Polygon(pts), z0, z1, m)
    # Welche Seitenbelegung bm_build fuer die Raumseite (Kante b -> a) waehlt, und wo dort u = 0 liegt
    fx_, fy_ = -dx, -dy
    if fx_ > 0.7:
        key, flip = "front", bx < ax                                   # u steigt mit x
    elif fy_ > 0.7:
        key, flip = "face_e", by < ay                                  # u steigt mit y
    elif fy_ < -0.7:
        key, flip = "face_w", by > ay                                  # u faellt mit y
    else:
        key, flip = "face_n", bx > ax                                  # u faellt mit x
    if flip:
        face = np.ascontiguousarray(face[:, ::-1])
    t = ctx.tex(name + "_face", _Im.fromarray(face), uv="part")
    o1, o2 = off, off + depth
    pts = [(ax + nx * o1, ay + ny * o1), (bx + nx * o1, by + ny * o1), (bx + nx * o2, by + ny * o2), (ax + nx * o2, ay + ny * o2)]
    side = ctx.color(name + "_side", tuple(int(v) for v in np.median(face.reshape(-1, 3), axis=0)))
    p = prism(Polygon(pts), z0, z1, side)
    p[key] = t
    return p


def screen_tex(ctx, name, frame_rgb, screen_rgb, line=(0, 0, 0), aspect=1.0, inset=(0.12, 0.30, 0.12, 0.10)):
    """Bild einer Geraeteseite mit Bildschirm (Rahmen, Schirm mit Zeilen, Kontur): fuer Seiten, die Among Us nie zeigt
    (Bildschirme zur Raummitte). inset = Rand links, oben, rechts, unten in Anteilen der Seite."""
    from PIL import Image as _Im, ImageDraw as _Dr
    if name in ctx.scene.mats:
        return name
    w = 128
    h = max(16, int(round(w / max(0.1, aspect))))
    im = _Im.new("RGB", (w, h), tuple(frame_rgb))
    d = _Dr.Draw(im)
    l, t, r, b = inset
    x0, y0, x1, y1 = int(w * l), int(h * t), int(w * (1 - r)), int(h * (1 - b))
    d.rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], fill=tuple(line))
    d.rectangle([x0, y0, x1, y1], fill=tuple(screen_rgb))
    dark = tuple(int(v * 0.8) for v in screen_rgb)
    for yy in range(y0 + 3, y1, 6):
        d.line([(x0 + 2, yy), (x1 - 2, yy)], fill=dark, width=1)
    d.rectangle([0, 0, w - 1, h - 1], outline=tuple(line), width=3)
    return ctx.tex(name, im, uv="part")


def office_chair(ctx, name, cx, cy, rgb, dark, line, back="S", w=0.52, seat_z=0.36, back_top=0.80):
    """Buerostuhl (Among-Us-Stil): Fuss mit Saeule, Sitz, Lehne auf der Seite back ('S' = zum Betrachter)."""
    body = ctx.color(f"{name}_body", rgb)
    shade = ctx.color(f"{name}_dark", dark)
    parts = [cyl(cx, cy, 0.20, 0.0, 0.04, shade, seg=20, outline=line),
             cyl(cx, cy, 0.045, 0.04, seat_z - 0.06, shade, seg=12),
             box(cx, cy, w, w * 0.85, seat_z - 0.06, seat_z, body, bevel=0.03, outline=line)]
    off = {"S": (0, -w * 0.36), "N": (0, w * 0.36), "W": (-w * 0.36, 0), "E": (w * 0.36, 0)}[back]
    bw, bd = (w, 0.11) if back in "NS" else (0.11, w)
    parts.append(box(cx + off[0], cy + off[1], bw, bd, seat_z, back_top, body, bevel=0.045, outline=line))
    return parts


def crate(ctx, name, cx, cy, s, rot, h, z0=0.0, side_rgb=(63, 97, 90), top_rgb=(90, 130, 112), line=(24, 36, 33)):
    """Among-Us-Kiste: Wuerfel mit Deckel, Seiten mit gezeichneter Griffmulde; cx, cy = WELTmitte."""
    from PIL import Image as _Im, ImageDraw as _Dr
    n = 128
    tname = f"{name}_side"
    if tname not in ctx.scene.mats:
        im = _Im.new("RGB", (n, n), tuple(side_rgb))
        d = _Dr.Draw(im)
        pts = [(0.08, 0.34), (0.36, 0.34), (0.40, 0.54), (0.60, 0.54), (0.64, 0.34), (0.92, 0.34)]
        d.line([(x * n, y * n) for x, y in pts], fill=tuple(line), width=5, joint="curve")
        ctx.tex(tname, im, uv="face")
    top = ctx.color(f"{name}_top", top_rgb)
    sq = affinity.rotate(sbox(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), rot, origin=(cx, cy))
    d = prism(sq, z0, z0 + h, tname, top=top, bevel=0.02, outline=line)
    d["side_uv"] = "face"
    return d


def barrel(ctx, bx, by, r, h, z0=0.0, prefix="au_barrel"):
    """Among-Us-Fass (Polus/Skeld-Lager): Koerper (71,108,126), Ring (107,158,173), Deckel (66,78,87), rote Banderole."""
    body = ctx.color(f"{prefix}", (71, 108, 126))
    lid = ctx.color(f"{prefix}_lid", (66, 78, 87))
    ring = ctx.color(f"{prefix}_ring", (107, 158, 173))
    label = ctx.color(f"{prefix}_label", (115, 28, 49))
    return [cyl(bx, by, r, z0, z0 + h - 0.06, body, seg=40, outline=(8, 12, 16)),
            cyl(bx, by, r * 0.97, z0 + h - 0.06, z0 + h - 0.02, ring, seg=40),
            cyl(bx, by, r * 0.93, z0 + h - 0.02, z0 + h, lid, seg=40),
            cyl(bx, by, r * 1.01, z0 + h * 0.45, z0 + h * 0.58, label, seg=40),
            # Fassreifen, Deckelrand und Spundloch (Fehlerrunde 19.10.: "glatte Faesser")
            cyl(bx, by, r * 1.035, z0 + h * 0.18, z0 + h * 0.18 + 0.025, ring, seg=40),
            cyl(bx, by, r * 1.035, z0 + h * 0.82, z0 + h * 0.82 + 0.025, ring, seg=40),
            lathe(bx, by, [(r * 0.9, z0 + h - 0.03), (r * 1.02, z0 + h - 0.03), (r * 1.02, z0 + h + 0.012), (r * 0.9, z0 + h + 0.012),
                           (r * 0.9, z0 + h - 0.03)], ring, seg=40),
            cyl(bx + r * 0.5, by + r * 0.2, r * 0.12, z0 + h, z0 + h + 0.02, lid, seg=12)]


def boulder(cx, cy, rx, ry, h, mats, seed=0, seg=14, rings=6, cap=0.70, outline=None):
    """Felsbrocken: gedrueckte Kuppel mit fester Zufallsdelle je Ecke. mats = (hell, schattig, schnee|None): Flaechen
    nach oben ueber cap*h bekommen Schnee, nach Westen/oben geneigte die helle, der Rest die schattige Farbe."""
    import random
    rnd = random.Random(seed)
    light, shade, snow = mats
    verts, faces, fm = [], [], []
    jit = [[1.0 + rnd.uniform(-0.16, 0.16) for _ in range(seg)] for _ in range(rings)]
    for i in range(rings):
        t = i / rings
        z = h * math.sin(t * math.pi / 2) ** 0.85
        rr = math.cos(t * math.pi / 2) ** 0.7
        for j in range(seg):
            a = 2 * math.pi * j / seg
            f = jit[i][j] if i else 0.5 * (1 + jit[i][j])
            verts.append((cx + rx * rr * f * math.cos(a), cy + ry * rr * f * math.sin(a), z * (1 + 0.08 * (jit[i][j] - 1))))
    top = len(verts)
    verts.append((cx + rnd.uniform(-0.1, 0.1) * rx, cy + rnd.uniform(-0.1, 0.1) * ry, h))
    bot = len(verts)
    verts.append((cx, cy, 0.0))

    def mat_of(ids):
        ps = [verts[q] for q in ids]
        ax, ay, az = ps[1][0] - ps[0][0], ps[1][1] - ps[0][1], ps[1][2] - ps[0][2]
        bx_, by_, bz = ps[2][0] - ps[0][0], ps[2][1] - ps[0][1], ps[2][2] - ps[0][2]
        nx, ny, nz = ay * bz - az * by_, az * bx_ - ax * bz, ax * by_ - ay * bx_
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / L, ny / L, nz / L
        zc = sum(p[2] for p in ps) / len(ps)
        if snow and zc > cap * h and nz > 0.35:
            return snow
        return light if (nz > 0.55 or nx < -0.25) else shade
    for i in range(rings - 1):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            c, d = (i + 1) * seg + (j + 1) % seg, (i + 1) * seg + j
            faces.append((a, b, c, d))
            fm.append(mat_of((a, b, c)))
    for j in range(seg):
        a, b = (rings - 1) * seg + j, (rings - 1) * seg + (j + 1) % seg
        faces.append((a, b, top))
        fm.append(mat_of((a, b, top)))
        faces.append((bot, (j + 1) % seg, j))
        fm.append(shade)
    return mesh(verts, faces, light, outline=outline, mats=fm)


def blob(cx, cy, cz, rx, ry, rz, mats, seed=0, seg=14, rings=8, outline=None):
    """Klumpiges Ellipsoid (Baumkrone, Moos): mats = (hell, schattig); Flaechen nach oben/Westen hell."""
    import random
    rnd = random.Random(seed)
    light, shade = mats
    verts, faces, fm = [], [], []
    for i in range(1, rings):
        t = math.pi * i / rings
        for j in range(seg):
            a = 2 * math.pi * j / seg
            f = 1.0 + rnd.uniform(-0.18, 0.18)
            verts.append((cx + rx * f * math.sin(t) * math.cos(a), cy + ry * f * math.sin(t) * math.sin(a),
                          cz + rz * f * math.cos(t)))
    top = len(verts)
    verts.append((cx, cy, cz + rz))
    bot = len(verts)
    verts.append((cx, cy, cz - rz))
    # Ringe laufen von oben (i=1) nach unten
    for i in range(rings - 2):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            c, d = (i + 1) * seg + (j + 1) % seg, (i + 1) * seg + j
            faces.append((a, d, c, b))
            fm.append(light if i < (rings - 2) * 0.45 else shade)
    for j in range(seg):
        faces.append((top, j, (j + 1) % seg))
        fm.append(light)
        a, b = (rings - 2) * seg + j, (rings - 2) * seg + (j + 1) % seg
        faces.append((bot, b, a))
        fm.append(shade)
    return mesh(verts, faces, light, outline=outline, mats=fm)


def crewmate_statue(cx, cy, mats, h=0.62, r=0.21, facing=-90.0, outline=None):
    """Eingefrorener Crewmate (Polus-Schneemann): Koerper als Drehkoerper, Visier, Rucksack; mats = (hell, mittel, dunkel)."""
    light, mid, dark = mats
    prof = [(0.0, 0.0), (r * 0.95, 0.0), (r, 0.05), (r, h * 0.62), (r * 0.92, h * 0.82), (r * 0.62, h * 0.96), (0.0, h)]
    parts = [lathe(cx, cy, prof, light, seg=32, outline=outline)]
    a = math.radians(facing)
    fx, fy = math.cos(a), math.sin(a)
    vx, vy = cx + fx * r * 0.78, cy + fy * r * 0.78
    parts.append(box(vx, vy, r * 1.15, r * 0.5, h * 0.52, h * 0.78, mid, rot=facing + 90, bevel=0.03, outline=outline))
    bx_, by_ = cx - fx * r * 0.95, cy - fy * r * 0.95
    parts.append(box(bx_, by_, r * 1.2, r * 0.45, h * 0.18, h * 0.62, mid, rot=facing + 90, bevel=0.04, outline=outline))
    for s_ in (-1, 1):                                                       # Beine
        lx, ly = cx + (-fy) * s_ * r * 0.45, cy + fx * s_ * r * 0.45
        parts.append(cyl(lx, ly, r * 0.36, 0.0, h * 0.2, dark, seg=16))
    return parts


class Ctx:
    """Wird jeder Raumdatei uebergeben: Zugriff auf Vorlage, Szene und Materialablage."""

    def __init__(self, scene, room):
        self.scene = scene
        self.ref = scene.ref
        self.room = room
        self.k = scene.cfg["k"]
        self.H = scene.H
        self.poly = scene.rooms.get(room)

    def art_y(self, y_art, z):
        return y_art - self.k * z

    def tex(self, name, img, **uv):
        f = self.scene.out / "tex" / f"{name}.png"
        img.save(f)
        self.scene.mats[name] = dict({"image": f.name}, **uv)
        return name

    def color(self, name, rgb):
        return self.scene.solid(name, rgb)

    def glow(self, name, rgb, strength=3.0):
        """Leuchtendes Material (Roehren, Bildschirme): Farbe exakt, Emission fuer EEVEE/Nightfall."""
        n = self.scene.solid(name, rgb)
        self.scene.mats[n]["emit"] = strength
        return n


def pit_rails(ctx, mat, z_top=0.45, inset=0.05, outline=None, min_len=0.25):
    """Gelaender entlang aller Kanten zwischen Plattform (Boden des Raums) und seinen Gruben (Raumdatei PITS)."""
    from shapely.ops import linemerge
    sc = ctx.scene
    pits = [pd["geom"] for pd in getattr(sc, "pits", []) if pd["room"] == ctx.room]
    if not pits:
        return []
    from shapely.ops import unary_union as _uu
    pu = _uu(pits)
    plat = sc.rooms[ctx.room].difference(pu).buffer(0)
    shared = pu.boundary.intersection(plat.buffer(0.02))
    shared = shared.difference(sc.floor.boundary.buffer(0.06))           # nicht an Aussenwaenden
    if shared.is_empty:
        return []
    lines = linemerge([g for g in getattr(shared, "geoms", [shared]) if g.geom_type == "LineString"]) \
        if shared.geom_type != "LineString" else shared
    parts = []
    for ln in getattr(lines, "geoms", [lines]):
        if ln.length < min_len:
            continue
        # leicht auf die Plattform versetzt
        off = ln.parallel_offset(inset, "left")
        if off.is_empty or not plat.buffer(0.01).contains(off.interpolate(0.5, normalized=True)):
            off = ln.parallel_offset(inset, "right")
        if off.is_empty or off.geom_type != "LineString":
            off = ln
        pts = [tuple(c) for c in off.simplify(0.02).coords]
        if len(pts) >= 2:
            parts += railing(pts, z_top, mat, r=0.022, post_r=0.018, post_step=0.4, outline=outline)
    return parts


def slab(poly, y, t, mat, face=None, outline=None, bbox=None, rot=0.0, cx=None):
    """Senkrechte Scheibe: Umriss poly in (x, z) (shapely, mit Loechern), Dicke t quer (y-t/2 .. y+t/2). Vorder- und
    Rueckseite zeigen face (Bild ueber bbox (x0, z0, x1, z1) des Umrisses), Raender in mat."""
    from shapely.geometry.polygon import orient
    import shapely as _sh
    verts, faces, mats, uvs = [], [], [], []
    bx0, bz0, bx1, bz1 = bbox or poly.bounds
    y0, y1 = y - t / 2, y + t / 2

    def uv(x, z):
        return ((x - bx0) / max(1e-6, bx1 - bx0), (z - bz0) / max(1e-6, bz1 - bz0))
    for g in getattr(poly, "geoms", [poly]):
        if g.is_empty or g.area < 1e-5:
            continue
        g = orient(g, 1.0)
        tris = _sh.constrained_delaunay_triangles(g)
        for tr in getattr(tris, "geoms", [tris]):
            cs = list(tr.exterior.coords)[:3]
            (ax, az), (bx, bz), (cx_, cz) = cs
            if (bx - ax) * (cz - az) - (cx_ - ax) * (bz - az) < 0:
                cs = [cs[0], cs[2], cs[1]]
            i = len(verts)
            verts += [(x, y0, z) for x, z in cs]                     # Vorderseite (Normale -y): CCW
            faces.append((i, i + 1, i + 2)); mats.append(face or mat); uvs.append([uv(x, z) for x, z in cs])
            i = len(verts)
            verts += [(x, y1, z) for x, z in cs[::-1]]               # Rueckseite (Normale +y)
            faces.append((i, i + 1, i + 2)); mats.append(face or mat); uvs.append([uv(x, z) for x, z in cs[::-1]])
        for ring in [g.exterior] + list(g.interiors):
            pts = list(ring.coords)
            for (ax, az), (bx, bz) in zip(pts, pts[1:]):
                i = len(verts)
                verts += [(ax, y0, az), (ax, y1, az), (bx, y1, bz), (bx, y0, bz)]
                faces.append((i, i + 1, i + 2, i + 3)); mats.append(mat); uvs.append([(0, 0), (0, 1), (1, 1), (1, 0)])
    if rot:                                                              # um die senkrechte Achse durch (cx, y)
        import math as _m
        c0 = (bx0 + bx1) / 2 if cx is None else cx
        ca, sa = _m.cos(_m.radians(rot)), _m.sin(_m.radians(rot))
        verts = [(c0 + (vx - c0) * ca - (vy - y) * sa, y + (vx - c0) * sa + (vy - y) * ca, vz) for vx, vy, vz in verts]
    d = {"type": "mesh", "verts": [list(v) for v in verts], "faces": [list(f) for f in faces], "mat": mat, "mats": mats,
         "uvs": uvs}
    if outline:
        d["outline"] = list(outline)
    return d


def sprite_outline(spr, x0, y_top, ppm, to_z, min_px=30, tol=0.012):
    """Umriss eines Sprites (Alpha > 128) als shapely-Flaeche mit Loechern in (x, z): Pixel (px, py) -> Welt
    x = x0 + px/ppm, Bild-y = y_top - py/ppm, z = to_z(Bild-y)."""
    import cv2
    import numpy as np
    from shapely.geometry import Polygon as _P
    from shapely.ops import unary_union as _uu
    a = (np.asarray(spr)[..., 3] > 128).astype(np.uint8)
    cs, hier = cv2.findContours(a, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return _P()
    hier = hier[0]

    def conv(c):
        return [(x0 + (px + 0.5) / ppm, to_z(y_top - (py + 0.5) / ppm)) for px, py in c[:, 0, :]]
    polys = []
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or cv2.contourArea(c) < min_px or len(c) < 3:
            continue
        holes = []
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) >= min_px * 0.5 and len(cs[j]) >= 3:
                holes.append(conv(cs[j]))
            j = hier[j][0]
        pg = _P(conv(c), holes).buffer(0)
        if not pg.is_empty:
            polys.append(pg.simplify(tol))
    return _uu(polys).buffer(0) if polys else _P()


def rot3(v, yaw, pitch, roll=0.0):
    """Punkt um die x-Achse kippen (roll, Grad: positiv = Hinterkante +y hoch), um die y-Achse neigen (pitch) und um
    z drehen (yaw); Reihenfolge roll, pitch, yaw."""
    x, y, z = v
    if roll:
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        y, z = y * cr - z * sr, y * sr + z * cr
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    x, z = x * cp - z * sp, x * sp + z * cp
    cy_, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return (x * cy_ - y * sy_, x * sy_ + y * cy_, z)


def obox(c, size, mat, yaw=0.0, pitch=0.0, outline=None, roll=0.0):
    """Frei gedrehter Kasten (Mitte c, Kanten size) als Netz; roll kippt um die lokale x-Achse (Schraegen)."""
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    corners = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
               (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    verts = []
    for v in corners:
        rx, ry, rz = rot3(v, yaw, pitch, roll)
        verts.append((c[0] + rx, c[1] + ry, c[2] + rz))
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return mesh(verts, faces, mat, outline=outline)


def tooth(c, w, h, mat, up=True):
    """Zahn: Pyramide mit Grundflaeche w x w bei c, Spitze h darueber (up) oder darunter."""
    x, y, z = c
    s_ = w / 2
    base = [(x - s_, y - s_, z), (x + s_, y - s_, z), (x + s_, y + s_, z), (x - s_, y + s_, z)]
    apex = (x, y, z + h if up else z - h)
    verts = base + [apex]
    if up:
        faces = [(3, 2, 1, 0), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    else:
        faces = [(0, 1, 2, 3), (1, 0, 4), (2, 1, 4), (3, 2, 4), (0, 3, 4)]
    return mesh(verts, faces, mat)
