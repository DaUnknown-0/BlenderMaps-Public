# Polus / Gelaende (alle begehbaren und sichtbaren Aussenflaechen ausserhalb der Gebaeude), am Kartenfoto gemessen.
#
# Boden: Zeichnung in Originalpalette (Boden (116,83,135), Schnee (205,223,236), Wege, Schatten), in 10er-Kacheln.

from bm_spec import art_floor, boulder, barrel, crate, crewmate_statue, cyl, box, lathe, prism, vent, sprite, flat_rgb

SKY = True
TILE = 10.0
VFAC = 0.8          # Gegenstaende zeichnet Among Us hoeher als Waende (k 0,5): Front ~0,8 der echten Hoehe


HOLE_SPRITES = ("RocksNBoxes/rock", "RocksNBoxes/bigRock", "RocksNBoxes/rockblock1", "blockrock", "Snowmen/snowman",
                "boxcluster", "boxclust2", "Storage/storagebox")


def sprite_poly(ctx, p, grow=0.03):
    """Umriss eines Sprites (Alphamaske) in Weltkoordinaten."""
    import cv2
    import numpy as np
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    a, b, w, h = p["rect"]
    al = (np.asarray(ctx.ref.sheet.crop((a, b, a + w, b + h)))[..., 3] > 60).astype(np.uint8)
    (x0, y0), (x1, y1) = p["min"], p["max"]
    cs, _ = cv2.findContours(al, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = [Polygon([(x0 + (q[0][0] + 0.5) / w * (x1 - x0), y1 - (q[0][1] + 0.5) / h * (y1 - y0)) for q in c])
             for c in cs if len(c) >= 3]
    return unary_union([q.buffer(0) for q in polys]).buffer(grow)


def floor(ctx, tname="Outside"):
    from shapely.geometry import box as _b
    if "_holes" not in ctx.__dict__:
        ctx._holes = [sprite_poly(ctx, p) for p in ctx.ref.world["props"]
                      if any(t in p["path"] for t in HOLE_SPRITES) or ("/panel_node_" in p["path"] and "shadow" not in p["path"])]
    bb = _b(*ctx.poly.bounds).buffer(0.3)
    return art_floor(ctx, f"floor_{tname}", holes=[h for h in ctx._holes if h.intersects(bb)])


def side_for(ctx, e):
    """Gebaeude-Aussenseiten (Ost/West) zeichnet Among Us nicht: Farbe der naechsten Fassade (Suedseite) desselben
    Gebaeudes, schlichteste Spalte; ohne Fassade in der Naehe die Wandkrone (60,74,74)."""
    import math
    from shapely.geometry import LineString, Point
    from bm_spec import side_from_column
    sc = ctx.scene
    cache = ctx.__dict__.setdefault("_side_cache", {})
    if "north" not in cache:
        cache["north"] = [n for n in sc.wall_edges() if n["room"] == "Outside" and n["kind"] == "north" and n["len"] > 0.5]
    mid = Point((e["a"][0] + e["b"][0]) / 2, (e["a"][1] + e["b"][1]) / 2)
    best, bd = None, 4.0
    for i, n in enumerate(cache["north"]):
        d = LineString([n["a"], n["b"]]).distance(mid)
        if d < bd:
            best, bd = i, d
    if best is None:
        return ctx.color("polus_wallcrown", (60, 74, 74))
    key = f"side_Outside_{best}"
    if key not in cache:
        n = cache["north"][best]
        x, y = sc.plain_column([n], ctx.k * ctx.H)
        cache[key] = side_from_column(ctx, key, x, y, spread=0.04)
    return cache[key]


# ---------------------------------------------------------------- Felsen
ROCK_LIGHT, ROCK_SHADE, SNOW = (115, 96, 126), (88, 74, 104), (206, 223, 236)
ROCK_LINE = (32, 23, 37)
ROCKS = ("RocksNBoxes/rock", "RocksNBoxes/bigRock", "RocksNBoxes/rockblock1", "blockrock")


def rock_lumps(ctx, p):
    """Brocken eines Fels-Sprites: jede Schneekappe ist die Kuppe eines Brockens. Breite = Kappenbreite * 1,7,
    Fuss = unterster Sprite-Pixel in der Spalte, Hoehe aus Kuppe - Fuss - Tiefenradius (Bildversatz k*h)."""
    import cv2
    import numpy as np
    a, b, w, h = p["rect"]
    im = np.asarray(ctx.ref.sheet.crop((a, b, a + w, b + h))).astype(int)
    (x0, y0), (x1, y1) = p["min"], p["max"]
    ppx, ppy = w / (x1 - x0), h / (y1 - y0)
    alpha = im[..., 3] > 128
    snow = alpha & (np.abs(im[..., :3] - np.array(SNOW)).sum(-1) < 40)
    n, lab, st, cen = cv2.connectedComponentsWithStats(snow.astype(np.uint8), connectivity=8)
    lumps = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 6:
            continue
        cxp = cen[i][0]
        top_r = st[i, cv2.CC_STAT_TOP]
        col = alpha[:, int(round(cxp))]
        bot_r = int(np.nonzero(col)[0].max()) if col.any() else h - 1
        wpx = st[i, cv2.CC_STAT_WIDTH]
        R = float(np.clip(wpx / ppx * 0.85, 0.14, 0.75))
        y_top = y1 - top_r / ppy
        y_bot = y1 - bot_r / ppy
        hh = max(0.18, (y_top - y_bot - 0.6 * R) / VFAC)
        lumps.append((x0 + cxp / ppx, y_bot + 0.6 * R, R, 0.75 * R, min(hh, 1.5 * R)))
    if not lumps:
        R = (x1 - x0) / 2
        lumps.append(((x0 + x1) / 2, y0 + 0.6 * R, R, 0.75 * R, max(0.2, (y1 - y0 - 0.6 * R) / VFAC)))
    return lumps


def rocks(ctx):
    mats = (ctx.color("polus_rock_light", ROCK_LIGHT), ctx.color("polus_rock_shade", ROCK_SHADE),
            ctx.color("polus_snow", SNOW))
    parts, seed = [], 0
    # keine Felsen in Innenraeumen (Fehlerrunde 19.10., #268/#270/#271: Brocken standen im Probenraum)
    from shapely.geometry import Point as _P
    from shapely.ops import unary_union as _uu
    inner = _uu([g for n, g in ctx.scene.rooms.items() if n != "Outside"]).buffer(0.15)
    for p in ctx.ref.world["props"]:
        if not any(t in p["path"] for t in ROCKS):
            continue
        for (cx, cy, rx, ry, h) in rock_lumps(ctx, p):
            seed += 1
            if inner.contains(_P(cx, cy)):
                continue
            parts.append(boulder(cx, cy, rx, ry, h, mats, seed=seed, cap=0.8, outline=ROCK_LINE))
    return parts


# ---------------------------------------------------------------- Kisten und Faesser am Dropship, Lagerkisten
# (Deckelmitte im Bild x, y, Kante, Drehung) -> Weltmitte: Deckel - VFAC * Kante (Wuerfel); Schnee = Kappe obenauf
CRATES = [(12.80, -7.27, 0.73, -25, False), (13.05, -6.35, 0.73, -25, False), (13.35, -6.85, 0.73, -25, False),
          (20.00, -6.40, 0.73, -25, False), (20.55, -6.95, 0.73, -25, True), (19.75, -7.45, 0.73, -25, True),
          (16.25, -10.30, 0.42, -20, False), (16.80, -10.40, 0.62, -20, False)]
# (Deckelmitte im Bild x, y, Radius, Hoehe)
BARRELS = [(12.60, -6.56, 0.22, 0.62), (13.75, -7.26, 0.25, 0.70)]
CRATE_LINE = (24, 36, 33)


def crates(ctx):
    parts = []
    snow = ctx.color("polus_snow", SNOW)
    for x, y, s, rot, cap in CRATES:
        cy = y - 0.62 * s                                                   # Deckel gestaucht gezeichnet
        from bm_models import au_crate
        parts += au_crate(ctx, "polus_crate", x, cy, s, rot, s)
        if cap:
            from shapely import affinity
            from shapely.geometry import box as _b
            sq = affinity.rotate(_b(x - s * 0.36, cy - s * 0.30, x + s * 0.50, cy + s * 0.52), rot, origin=(x, cy))
            parts.append(prism(sq, s, s + 0.06, snow, bevel=0.025, outline=(120, 140, 160)))
    for x, y, r, h in BARRELS:
        parts += barrel(ctx, x, y - 0.62 * h, r, h, prefix="polus_barrel")
    return parts


# ---------------------------------------------------------------- Eis-Crewmates, Wetterknoten
ICE = ((206, 223, 236), (140, 178, 206), (82, 113, 132))


def statues(ctx):
    mats = tuple(ctx.color(f"polus_ice_{i}", c) for i, c in enumerate(ICE))
    parts = []
    for p in ctx.ref.world["props"]:
        if "Snowmen/snowman" in p["path"] and not p["path"].endswith("ded.png"):
            (x0, y0), (x1, y1) = p["min"], p["max"]
            parts += crewmate_statue((x0 + x1) / 2, y0 + 0.16, mats, h=0.62, r=0.2, facing=180.0, outline=(60, 90, 110))
        elif p["path"].endswith("snowmanded.png"):
            (x0, y0), (x1, y1) = p["min"], p["max"]
            cx, cy = (x0 + x1) / 2, y0 + 0.15
            parts.append(lathe(cx, cy, [(0.0, 0.0), (0.2, 0.0), (0.21, 0.12), (0.17, 0.2), (0.0, 0.22)], mats[0], seg=24,
                               outline=(60, 90, 110)))
            parts.append(cyl(cx - 0.05, cy, 0.05, 0.2, 0.26, ctx.color("polus_bone", (231, 213, 168)), seg=12))
    return parts


def nodes(ctx):
    """Wetterknoten (panel_node_*): blauer Sockeltopf, Mast mit drei leuchtenden Ringen, Kugel obenauf."""
    pot = ctx.color("polus_node_pot", (82, 130, 181))
    potd = ctx.color("polus_node_pot_dark", (40, 52, 105))
    mast = ctx.color("polus_node_mast", (24, 28, 33))
    ring = ctx.glow("polus_node_ring", (173, 239, 255), 2.0)
    parts = []
    for p in ctx.ref.world["props"]:
        if "/panel_node_" not in p["path"] or "shadow" in p["path"]:
            continue
        (x0, y0), (x1, y1) = p["min"], p["max"]
        cx, cy = (x0 + x1) / 2, y0 + 0.12
        parts.append(lathe(cx, cy, [(0.0, 0.0), (0.13, 0.0), (0.16, 0.06), (0.16, 0.2), (0.12, 0.26), (0.0, 0.26)], pot,
                           seg=24, outline=(0, 0, 0)))
        parts.append(cyl(cx, cy, 0.1, 0.26, 0.29, potd, seg=20))
        parts.append(cyl(cx, cy, 0.022, 0.29, 0.74, mast, seg=10))
        for z in (0.40, 0.51, 0.62):
            parts.append(lathe(cx, cy, [(0.07, z), (0.13, z), (0.13, z + 0.025), (0.07, z + 0.025), (0.07, z)], ring, seg=24))
        parts.append(lathe(cx, cy, [(0.0, 0.72), (0.035, 0.735), (0.04, 0.76), (0.03, 0.785), (0.0, 0.79)], mast, seg=12))
    return parts


def lava_side(ctx):
    """Sprungbrett ueber der Lava (Sprite als Oberseite, Planke 0,08 dick, zwei Stuetzen am Ufer) und das
    Thermometer (panel_temphot) auf seinem Pfosten."""
    import bm_tex as T
    parts = []
    img, (x0, y0, x1, y1) = sprite(ctx, "Background/divingboard")
    W, H = img.size
    top_px = int(round(H * 0.72))                                            # untere 28 % = gezeichnete Kante
    import bm_style
    top = ctx.tex("polus_board_top", bm_style.floor_image("planks", (150, 160, 168), seed=4), uv="world", scale=[1.0, 1.0])
    edge = ctx.color("polus_board_edge", (132, 146, 156))
    # Planke als Koerper (#295): deckt die Gelaendezunge, die der Lavaschnitt unter dem Brett stehen laesst (x bis 32,87,
    # y -16,27..-15,60), liegt 0,03 darueber (vorher Oberseite genau auf z 0 -> Flimmern mit dem lila Gelaende), dazu
    # umlaufende Randleisten und ein Querholm am Ende
    bx0, bx1, by0, by1 = x0, 32.92, -16.31, -15.56
    parts.append(box((bx0 + bx1) / 2, (by0 + by1) / 2, bx1 - bx0, by1 - by0, -0.12, 0.03, edge, top=top, outline=(49, 60, 66)))
    lipm = ctx.color("polus_board_lip", (96, 108, 118))
    for yy in (by0 + 0.03, by1 - 0.03):
        parts.append(box((bx0 + bx1) / 2, yy, bx1 - bx0, 0.06, 0.03, 0.07, lipm, outline=(49, 60, 66)))
    parts.append(box(bx1 - 0.03, (by0 + by1) / 2, 0.06, by1 - by0, 0.03, 0.07, lipm, outline=(49, 60, 66)))
    for sx in (x0 + 0.12, x0 + 0.45):
        parts.append(box(sx, (by0 + by1) / 2, 0.08, (by1 - by0) * 0.8, -0.6, -0.12, edge, outline=(49, 60, 66)))
    img, (x0, y0, x1, y1) = sprite(ctx, "Outside/panel_temphot")
    W, H = img.size
    face = ctx.tex("polus_temphot_face", bm_style.ui_screen([((230, 90, 60), 0.6), ((240, 220, 200), 0.4)], seed=7, w=120, h=200, kind="gauge"), uv="part")
    body = ctx.color("polus_temphot_body", (90, 86, 80))
    cx = (x0 + x1) / 2
    parts.append(cyl(cx - 0.05, y0 + 0.12, 0.06, 0.0, 0.38, body, seg=12, outline=(20, 20, 20)))
    fr = box(cx, y0 + 0.12, x1 - x0, 0.14, 0.38, 0.38 + (y1 - y0) * 0.62 / VFAC, body, outline=(20, 20, 20))
    fr["front"] = face
    parts.append(fr)
    return parts


def bridges(ctx):
    """Stege: Plankenboden aus der Zeichnung (Laufsteg (150,158,173)), Unterzug, rote Gelaender (150,57,74) an beiden
    Stegseiten und rund um die Plattform (Sueden offen), Antennensaeule (Sprite SuppressorLeft: Koerper (132,147,148),
    dunkles Band (66,77,77), Glasstueck (104,192,176) leuchtend, blaue Fuesse (99,195,247))."""
    import math
    from shapely.geometry import Point
    from bm_spec import railing, tube
    sc = ctx.scene
    mm = sc.mapmod
    under = ctx.color("polus_bridge_under", (69, 67, 76))
    rail = ctx.color("polus_bridge_rail", (150, 57, 74))
    body = ctx.color("polus_pillar", (132, 147, 148))
    dark = ctx.color("polus_pillar_dark", (66, 77, 77))
    glass = ctx.glow("polus_pillar_glass", (104, 192, 176), 1.5)
    feet = ctx.glow("polus_pillar_feet", (99, 195, 247), 1.5)
    parts = []
    for i, b in enumerate(mm.BRIDGES):
        poly = mm.bridge_poly(b)
        x0, y0, x1, y1 = poly.bounds
        import bm_style
        top = ctx.tex(f"polus_bridge_top_{i}", bm_style.floor_image("plates", (124, 134, 140), seed=i), uv="world", scale=[1.0, 1.0])
        parts.append(prism(poly.simplify(0.01), -0.18, 0.0, under, top=top, outline=(30, 28, 36)))
        wx0, wy0, wx1, wy1 = b["walk"]
        cx, cy = b["c"]
        r = b["r"] - 0.04
        ys = cy - math.sqrt(max(0.0, r * r - ((wx1 - wx0) / 2) ** 2))
        for x in (wx0 + 0.03, wx1 - 0.03):
            parts += railing([(x, wy0 + 0.05), (x, ys)], 0.55, rail, r=0.03, post_step=0.5, post_r=0.025, outline=(60, 20, 30))
        a0 = math.degrees(math.atan2(ys - cy, wx1 - 0.03 - cx))
        a1 = math.degrees(math.atan2(ys - cy, wx0 + 0.03 - cx)) + 360
        arc = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in
               [a0 + (a1 - a0) * t / 28 for t in range(29)]]
        parts += railing(arc, 0.55, rail, r=0.03, post_step=0.45, post_r=0.025, outline=(60, 20, 30))
        # Stuetzen unter der Plattform
        for a in (30, 150, 270):
            sx, sy = cx + 0.55 * math.cos(math.radians(a)), cy + 0.55 * math.sin(math.radians(a))
            parts.append(tube([(sx, sy, -0.18), (cx + 0.15 * math.cos(math.radians(a)), cy + 0.15 * math.sin(math.radians(a)), -2.4)],
                              0.06, under, seg=8))
        # Antennensaeule
        px, py = b["pillar"]
        for a in (0, 120, 240):
            parts.append(lathe(px + 0.24 * math.cos(math.radians(a + 90)), py + 0.24 * math.sin(math.radians(a + 90)),
                               [(0.0, 0.0), (0.07, 0.02), (0.08, 0.07), (0.05, 0.12), (0.0, 0.13)], feet, seg=16))
        parts.append(lathe(px, py, [(0.0, 0.0), (0.27, 0.0), (0.27, 0.10), (0.24, 0.14), (0.24, 0.74), (0.0, 0.74)], body,
                           seg=32, outline=(24, 28, 33)))
        parts.append(cyl(px, py, 0.245, 0.74, 0.80, dark, seg=32))
        parts.append(cyl(px, py, 0.22, 0.80, 1.45, glass, seg=32, outline=(24, 28, 33)))
        parts.append(cyl(px, py, 0.245, 1.45, 1.52, dark, seg=32))
        parts.append(lathe(px, py, [(0.0, 1.52), (0.24, 1.52), (0.24, 2.30), (0.22, 2.42), (0.15, 2.52), (0.0, 2.56)], body,
                           seg=32, outline=(24, 28, 33)))
        parts.append(cyl(px, py, 0.245, 2.02, 2.08, dark, seg=32))
    return parts


def sprite_part(ctx, suffix, ax0, ay0, ax1, ay1, name, scale=None):
    """Ausschnitt eines Sprites nach Bildkoordinaten (Weltlage der Zeichnung) als Textur."""
    import bm_tex as T
    img, (x0, y0, x1, y1) = sprite(ctx, suffix)
    W, H = img.size
    box_ = (int(round((ax0 - x0) / (x1 - x0) * W)), int(round((y1 - ay1) / (y1 - y0) * H)),
            int(round((ax1 - x0) / (x1 - x0) * W)), int(round((y1 - ay0) / (y1 - y0) * H)))
    crop = flat_rgb(img.crop(box_))
    import bm_style
    return ctx.color(name, bm_style.median_rgb(crop))                 # gemessene Farbe statt Bildausschnitt


def transformers(ctx):
    """Vier Transformatoren im Generatorhof (Sprite transformer0001, Collider ~1,05 x 0,8): gegliederter Koerper
    (bm_models.transformer: Kessel mit Kuehlrippen, Schaltschrank, Gitterkaefig, Isolatorstapel) statt nackter
    Kaesten (#255)."""
    from bm_models import transformer
    parts = []
    for i, p in enumerate(q for q in ctx.ref.world["props"] if "transformer0001" in q["path"]):
        dx, dy = p["min"][0] - 8.24, p["min"][1] - (-12.13)
        parts += transformer(ctx, "polus_trafo", 8.33 + dx, -12.0 + dy, 9.37 + dx, -11.2 + dy)
    # Schaltkasten mit Blitzschild an der Hofwand (panel_switches 9,49..9,95 / -11,33..-10,87)
    box_ = ctx.color("polus_switchbox", (120, 128, 132))
    sign = ctx.glow("polus_switchbox_sign", (240, 160, 50), 1.4)
    parts.append(box(9.72, -11.25, 0.46, 0.14, 0.55, 0.95, box_, bevel=0.01, outline=(30, 34, 36)))
    parts.append(box(9.72, -11.326, 0.2, 0.012, 0.66, 0.86, sign))
    parts.append(box(9.72, -11.22, 0.06, 0.06, 0.0, 0.55, box_))
    return parts


def chainlink(ctx, x0, x1, y, h, mat, along="x", step=0.9):
    """Maschendrahtzaun als Koerper: Pfosten, oberer/unterer Holm, Drahtgitter aus duennen Staeben (keine Spieltextur).
    along "y": Zaun in Nord-Sued-Richtung, dann sind x0..x1 die y-Grenzen und y die feste x-Lage."""
    from bm_spec import tube
    out = []
    if along == "y":
        L = x1 - x0
        n = max(2, int(round(L / step)) + 1)
        for j in range(n):
            out.append(box(y, x0 + L * j / (n - 1), 0.05, 0.05, 0.0, h + 0.05, mat))
        for zz in (0.06, h):
            out.append(box(y, (x0 + x1) / 2, 0.03, L, zz - 0.015, zz + 0.015, mat))
        wire = ctx.color("polus_fence_wire", (70, 72, 84))
        yy = x0 + 0.12
        while yy < x1 - 0.05:
            out.append(tube([(y, yy, 0.08), (y, yy, h - 0.02)], 0.006, wire, seg=4))
            yy += 0.25
        zz = 0.3
        while zz < h - 0.05:
            out.append(tube([(y, x0, zz), (y, x1, zz)], 0.006, wire, seg=4))
            zz += 0.25
        return out
    L = x1 - x0
    n = max(2, int(round(L / step)) + 1)
    for j in range(n):
        px = x0 + L * j / (n - 1)
        out.append(box(px, y, 0.05, 0.05, 0.0, h + 0.05, mat))
    for zz in (0.06, h):
        out.append(box((x0 + x1) / 2, y, L, 0.03, zz - 0.015, zz + 0.015, mat))
    wire = ctx.color("polus_fence_wire", (70, 72, 84))
    k = 0
    xx = x0 + 0.12
    while xx < x1 - 0.05:
        out.append(tube([(xx, y, 0.08), (xx, y, h - 0.02)], 0.006, wire, seg=4))
        xx += 0.25
    zz = 0.3
    while zz < h - 0.05:
        out.append(tube([(x0, y, zz), (x1, y, zz)], 0.006, wire, seg=4))
        zz += 0.25
    return out


def fences(ctx):
    """Maschendraht (Sprite fencebot, halbdurchsichtig): Suedzaun des Generatorhofs, Ostzaun gleich gebaut.
    Gezeichnet 0,85 hoch -> 0,85 / VFAC."""
    img, (x0, y0, x1, y1) = sprite(ctx, "Electrical/fencebot")
    post = ctx.color("polus_fence_post", (33, 32, 49))
    h = (y1 - y0) / VFAC
    yb = y0 + 0.08
    parts = chainlink(ctx, x0, x1, yb, h, post)
    ex = 11.36                                                                # Ostzaun (nur als Linie gezeichnet)
    from bm_spec import tube
    for yy in (-13.97, -12.8, -11.6, -10.45):
        parts.append(box(ex, yy, 0.05, 0.05, 0.0, h + 0.05, post))
    for zz in (0.06, h):
        parts.append(box(ex, (-13.97 + -10.45) / 2, 0.03, 3.52, zz - 0.015, zz + 0.015, post))
    wire = ctx.color("polus_fence_wire", (70, 72, 84))
    yy = -13.85
    while yy < -10.5:
        parts.append(tube([(ex, yy, 0.08), (ex, yy, h - 0.02)], 0.006, wire, seg=4))
        yy += 0.25
    zz = 0.3
    while zz < h - 0.05:
        parts.append(tube([(ex, -13.97, zz), (ex, -10.45, zz)], 0.006, wire, seg=4))
        zz += 0.25
    return parts


def lab_yard(ctx):
    """Hof vor dem Labor: Bohrer (Sprite Science/drill, Koerper (102,121,126), drei Beine, oranger Bohrkopf), rote
    Werkzeugkiste (175,90,72), Maschendrahtzaun im Norden. Dazu das Ventilrad vor der Admin-Fassade."""
    import math
    from bm_spec import tube
    parts = []
    body = ctx.color("polus_drill", (102, 121, 126))
    dark = ctx.color("polus_drill_dark", (60, 70, 74))
    bit = ctx.color("polus_drill_bit", (220, 140, 60))
    _, (x0, y0, x1, y1) = sprite(ctx, "Science/drill")
    cx, cy = (x0 + x1) / 2 + 0.05, y0 + 0.3
    parts.append(lathe(cx, cy, [(0.0, 0.0), (0.06, 0.05), (0.16, 0.38), (0.0, 0.38)], bit, seg=16, outline=(60, 30, 10)))
    parts.append(lathe(cx, cy, [(0.0, 0.38), (0.27, 0.38), (0.30, 0.5), (0.30, 1.9), (0.22, 2.25), (0.08, 2.45), (0.0, 2.5)],
                       body, seg=28, outline=(30, 34, 36)))
    parts.append(cyl(cx, cy, 0.305, 1.1, 1.2, dark, seg=28))
    for a in (90, 210, 330):
        ex, ey = cx + 0.6 * math.cos(math.radians(a)), cy + 0.6 * math.sin(math.radians(a))
        parts.append(tube([(cx + 0.2 * math.cos(math.radians(a)), cy + 0.2 * math.sin(math.radians(a)), 0.9), (ex, ey, 0.0)],
                          0.035, dark, seg=6))
    # Werkbank mit Werkzeug (Zeichnung 24,98..26,05 / -6,52..-6,9) statt flacher Platte (#260)
    from bm_models import ground_hole, workbench
    parts += workbench(ctx, "polus_bench", 25.0, -6.92, 26.05, -6.5, h=0.58, rgb=(175, 90, 72), top_rgb=(140, 76, 60), seed=3)
    # Bohrloch (Collider Science/Hole) als dunkle Grube mit Geroellrand
    from shapely.geometry import Polygon as _Poly
    for w in ctx.ref.world["walls"]:
        if w["path"].endswith("Science/Hole"):
            parts += ground_hole(ctx, "polus_hole", _Poly(w["paths"][0]).buffer(0), seed=7)
    post = ctx.color("polus_fence_post", (33, 32, 49))
    parts += chainlink(ctx, 24.6, 27.4, -6.45, 1.05, post)
    # Westzaun des Hofs (Collider Science/Walls x 24,77 von -8,3 bis -6,6; im Foto der Zaun von der Kante gesehen):
    # vorher zog collider_walls dort eine raumhohe weisse Wand (#298/#299)
    parts += chainlink(ctx, -8.28, -6.47, 24.77, 1.05, post, along="y")
    # Ventilrad an der Admin-Fassade (Sprite panel_waterwheel, Aufgabe Wasserrad): senkrecht an der Wand, Blick nach
    # Sueden, auf einem kurzen Rohrstutzen. Vorher lag das Rad waagerecht auf einem Pfosten vor der Fassade und sah im
    # Schnee wie ein Stehtisch aus (Meldung #289).
    _, (wx0, wy0, wx1, wy1) = sprite(ctx, "Admin/panel_waterwheel")
    wcx = (wx0 + wx1) / 2
    wall_y, wy, wz, wr = -24.05, -24.17, 0.52, 0.30
    rim = ctx.color("polus_wheel", (165, 142, 132))
    pipe = ctx.color("polus_wheel_pipe", (71, 55, 54))
    parts.append(tube([(wcx, wall_y + 0.04, wz), (wcx, wy + 0.03, wz)], 0.07, pipe, seg=14, outline=(0, 0, 0)))
    parts.append(cyl(wcx, wall_y - 0.01, 0.13, wz - 0.13, wz + 0.13, pipe, seg=16))
    n = 28
    ring = [(wcx + wr * math.cos(2 * math.pi * i / n), wy, wz + wr * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    parts.append(tube(ring, 0.028, rim, seg=8, outline=(0, 0, 0)))
    for i in range(6):
        a_ = math.radians(i * 60 + 30)
        parts.append(tube([(wcx, wy, wz), (wcx + (wr + 0.06) * math.cos(a_), wy, wz + (wr + 0.06) * math.sin(a_))], 0.02, rim,
                          seg=6))
        parts.append(cyl(wcx + (wr + 0.07) * math.cos(a_), wy, 0.025, wz + (wr + 0.07) * math.sin(a_) - 0.035,
                         wz + (wr + 0.07) * math.sin(a_) + 0.035, rim, seg=8))
    parts.append(tube([(wcx, wy + 0.04, wz), (wcx, wy - 0.04, wz)], 0.06, rim, seg=14, outline=(0, 0, 0)))
    return parts


VENTS = ["Outside/ScienceBuildingVent", "Outside/ElectricBuildingVent", "Outside/SouthVent", "LifeSupport/ElecFenceVent"]


def props(ctx):
    parts = []
    parts += rocks(ctx)
    parts += crates(ctx)
    parts += statues(ctx)
    parts += nodes(ctx)
    parts += lava_side(ctx)
    parts += bridges(ctx)
    parts += transformers(ctx)
    parts += fences(ctx)
    parts += lab_yard(ctx)
    for v in VENTS:
        parts += vent(ctx, v)
    return parts
