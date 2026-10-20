# Fungle - kartenweite Teile: Ebenen, Berg als Hoehenfeld, Pilzwald, Meer, Nachthimmel.
#
# Vorlage: aus den Sprites zusammengesetztes Foto (bm_ref COMPOSITE, 52 px/E), weil die Aufnahme nur 19,3 px/E hat.
# Ebenen (Leiterbaender, Nightfall-Messung): Strand/Dschungel 0, Highland 4,5884 (BottomLeft/RightLadder),
#   Comms-Plateau 8,1244 (ueber Ledge 6,4746). Klippen sind im Bild etwa so lang gezeichnet, wie sie hoch sind
#   (Highland-Front 4,7 lang fuer 4,59) -> Berg als Hoehenfeld: zwischen zwei Ebenen linear ueber die Bildlage.
# Meer (243,187,84) auf -0,6, Nachthimmel (42,45,62), Leere (57,26,54).

import cv2
import math
import numpy as np
from shapely.geometry import Point, Polygon, box as sbox
from shapely.ops import unary_union

LEVELS = [("Highland", (14.0, 3.5), 4.5884), ("Plateau", (21.3, 13.5), 8.1244)]
MOUNTAIN_BOX = (-2.0, -6.8, 30.0, 24.8)
SEA = (243, 187, 84)
SEA_Z = -0.6
GRID = 0.2
SUMMIT_MAX = 12.5


# Leitern (Nightfall-Tabelle): x, y unten, y oben. Ihre Laufstreifen verbinden die Ebenen im Grundriss und werden
# deshalb vor der Ebenenteilung herausgeschnitten (die Leitern baut extra()).
LADDERS = [(11.38, -5.92, -1.11), (18.01, -5.92, -1.02), (19.23, 4.28, 6.52), (21.52, 7.74, 9.88)]
LADDER_W = 0.5


def ladder_cut():
    return unary_union([sbox(x - LADDER_W, y0 + 0.15, x + LADDER_W, y1 - 0.15) for x, y0, y1 in LADDERS])


def adjust(sc):
    cut = ladder_cut()
    for n in list(sc.rooms):
        sc.rooms[n] = sc.rooms[n].difference(cut).buffer(0)
    sc.floor = sc.floor.difference(cut).buffer(0)
    out = sc.rooms["Outside"]
    pieces = list(getattr(out, "geoms", [out]))
    sc.auto_z = {}
    sc.level_polys = {"Outside": []}
    for name, seed, z in LEVELS:
        sc.level_polys[name] = []
    keep = []
    for g in pieces:
        hit = None
        for name, seed, z in LEVELS:
            if g.buffer(0.05).contains(Point(seed)):
                hit = (name, z)
        if hit:
            sc.rooms[hit[0]] = unary_union([sc.rooms.get(hit[0], Polygon()), g]).buffer(0)
            sc.auto_z[hit[0]] = hit[1]
            sc.level_polys[hit[0]].append(g)
        else:
            keep.append(g)
    sc.rooms["Outside"] = unary_union(keep).buffer(0)
    # Zonenraeume, die selbst den Ebenen-Startpunkt enthalten (Comms-Plateau)
    for name, seed, z in LEVELS:
        for n, g in sc.rooms.items():
            if n != name and g.buffer(0.05).contains(Point(seed)):
                sc.auto_z[n] = z
                sc.level_polys[name].append(g)
    # Raeume (Zonen) auf den Hochebenen: Ebene der Flaeche, an die sie grenzen
    for n, g in list(sc.rooms.items()):
        if n in ("Outside",) or n in dict((a, 0) for a, _, _ in LEVELS):
            continue
        for name, seed, z in LEVELS:
            lp = unary_union(sc.level_polys[name]) if sc.level_polys[name] else None
            if lp is not None and lp.distance(g) < 0.3:
                sc.auto_z[n] = z
                sc.level_polys[name].append(g)
    # Pilzinseln im Dschungel sind Wandloecher, aber kein Bauwerk: Boden mit Pilzen (extra)
    others = unary_union([g for n, g in sc.rooms.items() if n != "Outside"]).buffer(0.8)
    sc.mushroom_areas = []
    walls = []
    for h in getattr(sc, "wall_holes", []):
        rest = h.difference(others)
        c = h.representative_point()
        if h.area > 1.0 and rest.area / h.area > 0.6 and c.y < -3.0:
            sc.mushroom_areas.append(h)
        else:
            walls.append(h)
    if sc.mushroom_areas:
        add = unary_union(sc.mushroom_areas)
        sc.rooms["Outside"] = unary_union([sc.rooms["Outside"], add]).buffer(0)
        sc.floor = unary_union([sc.floor, add]).buffer(0)
    sc.wall_holes = walls
    # Wildflaechen ausserhalb der Laufwege (Pilzsaum an der Kueste, Kristallfelder): Inselboden ohne Berg
    from bm_plan import RES
    sc._mmask = None
    mm = mountain_mask(sc)
    x0, y0, x1, y1 = MOUNTAIN_BOX
    ref, pl = sc.ref, sc.plan
    img = ref.img.astype(np.int16)
    island = ~sc.cfg["sky"](img)
    island = cv2.resize(island.astype(np.float32), (pl.gw, pl.gh), interpolation=cv2.INTER_AREA) > 0.5
    flo = sc._raster(sc.floor) > 0
    wild = island & ~flo
    # Bergmaske (GRID) auf das Planraster uebertragen und ausnehmen
    mmr = np.zeros_like(wild)
    rr, cc = np.nonzero(mm)
    px = ((x0 + cc * GRID - pl.ox) * RES).astype(int)
    py = ((pl.oy - (y1 - rr * GRID)) * RES).astype(int)
    k = int(GRID * RES)
    for dx in range(-k, k + 1):
        for dy in range(-k, k + 1):
            ok = (py + dy >= 0) & (py + dy < pl.gh) & (px + dx >= 0) & (px + dx < pl.gw)
            mmr[(py + dy)[ok], (px + dx)[ok]] = True
    wild &= ~mmr
    wall = sc._raster(unary_union(sc.wall_holes)) > 0 if sc.wall_holes else np.zeros_like(wild)
    wild &= ~wall
    sc._colfill = collider_fill(sc)
    wild &= ~(sc._colfill > 0)
    # geschlossene Collider-Koerper (Wrack, Felsen, Pilzhaufen, Lagerwaende) werden Wandmasse mit gezeichneter Krone
    bodies = []
    for w, pts in sc.ref.colliders(("Ship",)):
        if "PlayerBoundary" in w["path"] or "Door" in w["path"] or not w.get("closed") or len(pts) < 4:
            continue
        g = Polygon(pts).buffer(0)
        if g.area < 0.3:
            continue
        g = g.difference(sc.floor).buffer(0)
        if not g.is_empty and g.area > 0.2:
            bodies.append(g)
    sc.wall_holes = list(sc.wall_holes) + bodies
    n, lab, st, _ = cv2.connectedComponentsWithStats(wild.astype(np.uint8), connectivity=4)
    big = np.zeros(n, bool)
    big[1:] = st[1:, cv2.CC_STAT_AREA] > 2.0 * RES * RES
    add = pl._polys(big[lab].astype(np.uint8)).buffer(0.06)                # ueberlappen: keine Haarfugen zum Laufboden
    others = unary_union([g for n, g in sc.rooms.items() if n != "Outside"])
    add = add.difference(others).buffer(0)
    if not add.is_empty:
        sc.rooms["Outside"] = unary_union([sc.rooms["Outside"], add]).buffer(0)
        sc.floor = unary_union([sc.floor, add]).buffer(0)
        sc.mushroom_areas += [g for g in getattr(add, "geoms", [add])]
    sc._mmask = mm
    sc.floor_holes = furniture_holes(sc)


def _levels_raster(sc):
    """Hoehen der begehbaren Flaechen auf dem Gitter des Bergs (NaN = Berg/unbekannt)."""
    x0, y0, x1, y1 = MOUNTAIN_BOX
    nx, ny = int((x1 - x0) / GRID) + 1, int((y1 - y0) / GRID) + 1
    Z = np.full((ny, nx), np.nan, np.float32)
    def fill(poly, z):
        m = np.zeros((ny, nx), np.uint8)
        for g in getattr(poly, "geoms", [poly]):
            if g.is_empty:
                continue
            pts = np.array([((x - x0) / GRID, (y1 - y) / GRID) for x, y in g.exterior.coords], np.int32)
            cv2.fillPoly(m, [pts], 1)
            for h in g.interiors:
                pts = np.array([((x - x0) / GRID, (y1 - y) / GRID) for x, y in h.coords], np.int32)
                cv2.fillPoly(m, [pts], 0)
        Z[m > 0] = z
    for n, g in sc.rooms.items():
        fill(g, sc.auto_z.get(n, 0.0))
    return Z


def mountain_mask(sc):
    """Berg = nicht begehbar, im Bergrechteck, kein Meer/Himmel/Leere, keine Pilzinsel."""
    x0, y0, x1, y1 = MOUNTAIN_BOX
    nx, ny = int((x1 - x0) / GRID) + 1, int((y1 - y0) / GRID) + 1
    img = sc.ref.crop(x0, y0, x1, y1).resize((nx, ny))
    a = np.asarray(img).astype(int)
    open_ = sc.cfg["sky"](a)
    m = ~open_
    fl = np.zeros((ny, nx), np.uint8)
    for g in getattr(sc.floor, "geoms", [sc.floor]):
        pts = np.array([((x - x0) / GRID, (y1 - y) / GRID) for x, y in g.exterior.coords], np.int32)
        cv2.fillPoly(fl, [pts], 1)
    m &= fl == 0
    # nur das grosse zusammenhaengende Bergstueck
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=4)
    if n > 1:
        big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        m = lab == big
    return m


def heightfield(sc):
    """Hoehe je Gitterpunkt: begehbar = Ebene, Berg = linear zwischen der naechsten Ebene im Sueden und im Norden
    derselben Spalte; ohne Ebene im Norden steigt der Gipfel mit Steigung 1 bis SUMMIT_MAX."""
    Z = _levels_raster(sc)
    M = mountain_mask(sc)
    ny, nx = Z.shape
    H = np.where(np.isnan(Z), 0.0, Z).astype(np.float32)
    for c in range(nx):
        col = Z[:, c]
        known = np.where(~np.isnan(col))[0]
        for r in np.where(M[:, c])[0]:
            south = known[known > r]                 # Zeile waechst nach Sueden
            north = known[known < r]
            if len(south) and len(north):
                rs, rn = south.min(), north.max()
                t = (rs - r) / max(1, rs - rn)
                H[r, c] = col[rs] + (col[rn] - col[rs]) * t
            elif len(south):
                rs = south.min()
                H[r, c] = min(SUMMIT_MAX, col[rs] + (rs - r) * GRID)
            elif len(north):
                rn = north.max()
                H[r, c] = max(0.0, col[rn] - (r - rn) * GRID)
    # Harmonisch glaetten: Ebenen fest, Bergfuss (Rand zu Meer/Strand ausserhalb der Laufflaechen) fest auf 0;
    # Mittel aus Spaltenverlauf (steile gezeichnete Klippen) und Glaettung (keine senkrechten Vorhaenge an den Flanken)
    known = ~np.isnan(Z)
    foot = (~M) & (~known)
    G = H.copy()
    G[foot] = 0.0
    for _ in range(600):
        P = np.pad(G, 1, mode="edge")
        avg = (P[:-2, 1:-1] + P[2:, 1:-1] + P[1:-1, :-2] + P[1:-1, 2:]) / 4.0
        G = np.where(M, avg, G)
    H = np.where(M, 0.5 * H + 0.5 * G, H)
    H = np.where(M, cv2.GaussianBlur(H, (0, 0), 1.0), H)
    return H, M


def collider_fill(sc):
    """Wandkoerper: geschlossene Ship-Collider gefuellt, offene als Linie (Planraster). PlayerBoundary ausgenommen."""
    pl = sc.plan
    m = np.zeros((pl.gh, pl.gw), np.uint8)
    for w, pts in sc.ref.colliders(("Ship",)):
        if "PlayerBoundary" in w["path"] or "Door" in w["path"]:
            continue
        px = pl._px(pts)
        if w.get("closed") and len(pts) >= 4:
            cv2.fillPoly(m, [px], 1)
        else:
            cv2.polylines(m, [px], False, 1, thickness=3)
    return m


def open_edge(sc, a, b, nx, ny):
    """Fungle: Wand nur, wo hinter der Kante ein Wandkoerper (Collider) liegt; Kueste, Berg, Sand sind offen."""
    cf = getattr(sc, "_colfill", None)
    if cf is not None:
        pl = sc.plan
        hits = 0
        for f in (0.25, 0.5, 0.75):
            x = a[0] + (b[0] - a[0]) * f - nx * 0.12
            y = a[1] + (b[1] - a[1]) * f - ny * 0.12
            c, r = pl._p((x, y))
            if 0 <= r < cf.shape[0] and 0 <= c < cf.shape[1] and cf[r, c]:
                hits += 1
        return hits < 2
    if getattr(sc, "_mmask", None) is None:
        sc._mmask = mountain_mask(sc)
    x0, y0, x1, y1 = MOUNTAIN_BOX
    mx, my = (a[0] + b[0]) / 2 - nx * 0.25, (a[1] + b[1]) / 2 - ny * 0.25
    c, r = int((mx - x0) / GRID), int((y1 - my) / GRID)
    if 0 <= r < sc._mmask.shape[0] and 0 <= c < sc._mmask.shape[1] and sc._mmask[r, c]:
        return True
    return None


def extra(sc, ctx):
    import bm_tex as T
    from bm_scene import tri
    out = []
    # Berg: Dreiecksnetz ueber das Gitter, Textur = Zeichnung in Bildlage
    H, M = heightfield(sc)
    x0, y0, x1, y1 = MOUNTAIN_BOX
    ny, nx = H.shape
    import bm_style
    tex = ctx.tex("fungle_mountain", bm_style.floor_image("ground", (58, 96, 62), (92, 70, 54), seed=2), uv="world", scale=[2.0, 2.0])
    verts, faces = [], []
    idx = -np.ones((ny, nx), np.int64)
    use = cv2.dilate(M.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    for r in range(ny):
        for c in range(nx):
            if use[r, c]:
                idx[r, c] = len(verts)
                verts.append((x0 + c * GRID, y1 - r * GRID, float(H[r, c])))
    for r in range(ny - 1):
        for c in range(nx - 1):
            if M[r, c] or M[r + 1, c] or M[r, c + 1] or M[r + 1, c + 1]:
                a, b, d, e = idx[r, c], idx[r, c + 1], idx[r + 1, c], idx[r + 1, c + 1]
                if min(a, b, d, e) >= 0:
                    faces.append((int(d), int(e), int(b), int(a)))
    out.append({"name": "mountain", "coll": "Terrain", "kind": "terrain", "mat": tex, "verts": verts, "faces": faces,
                "bbox": [x0, y0, x1, y1]})
    out += mushrooms(sc, ctx)
    out += props_extra(sc, ctx)
    out += furniture(sc, ctx)
    # Meer und Himmel
    sea = ctx.color("fungle_sea", SEA)
    R = 120.0
    out.append({"name": "sea", "coll": "Terrain", "mat": sea, "kind": "floor", "z": SEA_Z,
                "tris": [[[-R, -R], [R, -R], [R, R]], [[-R, -R], [R, R], [-R, R]]]})
    return out


CAP, RING, STEM = (102, 35, 74), (198, 151, 186), (181, 92, 148)
WHITE, WHITE2 = (255, 230, 239), (250, 202, 225)
POD = (159, 130, 13)
MUSH_PAL = [CAP, RING, STEM, WHITE, WHITE2, (82, 25, 66), (148, 65, 132), (99, 32, 74)]


def mushrooms(sc, ctx):
    """Pilzwald: auf einem geruettelten Raster (0,9) in den Pilzflaechen, nur wo die Zeichnung Pilzfarben zeigt
    (Rot/Blau deutlich ueber Gruen). Grosse Pilze: Hut (102,35,74) mit hellem Ring (198,151,186), Stiel (181,92,148);
    kleine weisse Pilze (255,230,239)/(250,202,225); vereinzelt gelbe Samenkapseln (159,130,13)."""
    import random
    from bm_spec import lathe, cyl
    rnd = random.Random(11)
    cap, ring, stem = (ctx.color("fu_cap", CAP), ctx.color("fu_ring", RING), ctx.color("fu_stem", STEM))
    white, white2 = ctx.color("fu_white", WHITE), ctx.color("fu_white2", WHITE2)
    pod = ctx.color("fu_pod", POD)
    parts = []
    area = unary_union(getattr(sc, "mushroom_areas", []))
    if area.is_empty:
        return []
    x0, y0, x1, y1 = area.bounds
    ref = sc.ref
    step = 0.9
    a_ = ref.img.astype(np.int16)
    mm_ = np.zeros(a_.shape[:2], np.float32)
    for q in MUSH_PAL:
        mm_ = np.maximum(mm_, (np.abs(a_ - np.array(q, np.int16)).sum(-1) <= 45).astype(np.float32))
    dens = cv2.blur(mm_, (int(ref.ppu * 1.2), int(ref.ppu * 1.2)))
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            px, py = x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3)
            x += step
            if not area.contains(Point(px, py)):
                continue
            ix, iy = ref.w2p(px, py)
            if not (0 <= int(ix) < ref.W and 0 <= int(iy) < ref.H):
                continue
            c = ref.img[int(iy), int(ix)].astype(int)
            if py > -2.0 or min(np.abs(c - np.array(q)).sum() for q in MUSH_PAL) > 45:
                continue
            if dens is not None and dens[min(dens.shape[0] - 1, int(iy)), min(dens.shape[1] - 1, int(ix))] < 0.45:
                continue                                               # nur im dichten Pilzwald
            kind = rnd.random()
            if kind < 0.55:
                r = rnd.uniform(0.45, 0.8)
                h = rnd.uniform(0.6, 1.4)
                parts.append(cyl(px, py, r * 0.22, 0.0, h, stem, seg=12, outline=(60, 15, 45)))
                prof = [(0.0, h + 0.32 * r), (r * 0.55, h + 0.28 * r), (r * 0.95, h + 0.12 * r), (r, h), (r * 0.8, h - 0.05),
                        (0.0, h - 0.02)]
                parts.append(lathe(px, py, prof, cap, seg=20, outline=(40, 10, 30)))
                parts.append(lathe(px, py, [(r * 0.62, h + 0.235 * r), (r * 0.78, h + 0.19 * r), (r * 0.78, h + 0.205 * r),
                                            (r * 0.62, h + 0.25 * r)], ring, seg=20))
            elif kind < 0.92:
                r = rnd.uniform(0.2, 0.34)
                h = rnd.uniform(0.25, 0.55)
                parts.append(cyl(px, py, r * 0.3, 0.0, h, white2, seg=10))
                parts.append(lathe(px, py, [(0.0, h + 0.4 * r), (r * 0.7, h + 0.3 * r), (r, h), (r * 0.6, h - 0.04), (0.0, h)],
                                   white, seg=14, outline=(120, 60, 100)))
            else:
                parts.append(lathe(px, py, [(0.0, 0.0), (0.16, 0.05), (0.2, 0.25), (0.12, 0.45), (0.0, 0.55)], pod, seg=10,
                                   outline=(60, 50, 5)))
        y += step
    return [{"name": "mushrooms", "coll": "Terrain", "kind": "parts", "parts": parts}]


def level_at(sc, x, y):
    """Bodenhoehe am Punkt: Ebene des naechsten Raums (Hochebenen), sonst 0."""
    n = sc._room_at((x, y))
    return getattr(sc, "auto_z", {}).get(n, 0.0)


HANDLED = ("Ladders/", "Bonfire", "Zipline", "anim_antenna", "JungleObstacles/", "GlowingMushroom", "Vents/", "Mushrooms/",
           "HighlandsObstacles/Obstacle", "Rooms/Dock/Dock", "ConchEmergencyButton")


def props_extra(sc, ctx):
    """Leitern, Lagerfeuer, Seilrutsche, Antenne, Kristalle, Leuchtpilze; uebrige Konsolen/Hindernisse mit Collider
    als Kaesten mit ihrem Sprite als Front, auf der Ebene ihres Raums."""
    import math
    import bm_tex as T
    from bm_spec import box, cyl, lathe, tube, sprite, flat_rgb, mesh
    parts = []
    ref = sc.ref
    wood = ctx.color("fu_ladder", (41, 12, 41))
    # Leitern: vom Fuss (untere Ebene) schraeg zur Kante der oberen Ebene, Holme + Sprossen
    for x, ya, yb in LADDERS:
        za, zb = level_at(sc, x, ya - 0.3), level_at(sc, x, yb + 0.3)
        if zb <= za:
            zb = za + (yb - ya)
        for dx in (-0.2, 0.2):
            parts.append(tube([(x + dx, ya, za + 0.05), (x + dx, yb, zb + 0.05)], 0.03, wood, seg=8))
        n = int(math.hypot(yb - ya, zb - za) / 0.3)
        for i in range(1, n):
            t = i / n
            parts.append(tube([(x - 0.2, ya + (yb - ya) * t, za + (zb - za) * t + 0.05),
                               (x + 0.2, ya + (yb - ya) * t, za + (zb - za) * t + 0.05)], 0.022, wood, seg=6))
    # Lagerfeuer: Steinring, Scheite, Flamme (leuchtend)
    _, (fx0, fy0, fx1, fy1) = sprite(ctx, "Bonfire/Fire")
    fx, fy = (fx0 + fx1) / 2, fy0 + 0.25
    stone = ctx.color("fu_stone", (195, 139, 79))
    log = ctx.color("fu_log", (178, 114, 21))
    for i in range(10):
        a = 2 * math.pi * i / 10
        parts.append(lathe(fx + 0.55 * math.cos(a), fy + 0.42 * math.sin(a), [(0.0, 0.0), (0.12, 0.0), (0.13, 0.08),
                                                                              (0.08, 0.15), (0.0, 0.16)], stone, seg=10))
    for a in (20, 140, 260):
        r = math.radians(a)
        parts.append(tube([(fx + 0.4 * math.cos(r), fy + 0.3 * math.sin(r), 0.05), (fx, fy, 0.35)], 0.06, log, seg=8))
    fire = ctx.glow("fu_fire", (247, 207, 66), 3.0)
    core = ctx.glow("fu_fire_core", (231, 121, 16), 3.0)
    parts.append(lathe(fx, fy, [(0.0, 0.1), (0.22, 0.15), (0.16, 0.45), (0.06, 0.8), (0.0, 0.95)], core, seg=12))
    parts.append(lathe(fx, fy, [(0.0, 0.12), (0.14, 0.18), (0.1, 0.4), (0.04, 0.65), (0.0, 0.72)], fire, seg=12))
    # Seilrutsche: zwei Pfosten, Seil
    post = ctx.color("fu_zip_post", (244, 230, 192))
    _, (b0, b1, b2, b3) = sprite(ctx, "Zipline/ZiplineBottomPost")
    _, (t0, t1, t2, t3) = sprite(ctx, "Zipline/ZiplineTopPost")
    bx, by = (b0 + b2) / 2, b1 + 0.25
    tx, ty = (t0 + t2) / 2, t1 + 0.25
    bz, tz = level_at(sc, bx, by), level_at(sc, tx, ty)
    parts.append(cyl(bx, by, 0.09, bz, bz + 1.8, post, seg=10, outline=(90, 109, 107)))
    parts.append(cyl(tx, ty, 0.09, tz, tz + 2.4, post, seg=10, outline=(90, 109, 107)))
    parts.append(tube([(bx, by, bz + 1.7), (tx, ty, tz + 2.3)], 0.02, ctx.color("fu_cable", (60, 60, 60)), seg=6))
    # Antenne auf dem Comms-Plateau
    grey = ctx.color("fu_antenna", (156, 154, 143))
    light = ctx.color("fu_antenna_light", (186, 186, 176))
    _, (a0, a1, a2, a3) = sprite(ctx, "anim_antenna0001/AntennaBase")
    ax, ay = (a0 + a2) / 2, a1 + 0.2
    az = level_at(sc, ax, ay)
    parts.append(cyl(ax, ay, 0.22, az, az + 0.25, grey, seg=16, outline=(41, 44, 41)))
    parts.append(cyl(ax, ay, 0.06, az + 0.25, az + 1.6, grey, seg=10))
    parts.append(lathe(ax, ay, [(0.0, az + 1.55), (0.15, az + 1.56), (0.45, az + 1.66), (0.65, az + 1.82), (0.0, az + 1.7)],
                       light, seg=32, outline=(41, 44, 41), tilt=(40.0, 0.0, az + 1.6)))
    # Kristalle (rot/violett), je Sprite drei schraege Saeulen
    crys = (ctx.color("fu_crystal", (162, 32, 54)), ctx.color("fu_crystal_dark", (140, 23, 60)))
    for p in ref.world["props"]:
        if "Crystal" in p["path"] or "HighlandsObstacles/Obstacle" in p["path"]:
            (x0, y0), (x1, y1) = p["min"], p["max"]
            cx, cy = (x0 + x1) / 2, y0 + 0.3
            z0 = level_at(sc, cx, cy)
            w = (x1 - x0) / 2
            for k, (dx, ang, h) in enumerate(((-w * 0.4, 15, 0.9), (0.0, -5, 1.3), (w * 0.45, -20, 0.8))):
                parts.append(lathe(cx + dx, cy, [(0.0, z0), (0.16, z0), (0.16, z0 + h * 0.8), (0.0, z0 + h)],
                                   crys[k % 2], seg=6, outline=(66, 16, 66), tilt=(abs(ang), 0.0 if ang > 0 else 180.0, z0)))
    # Leuchtpilze
    glow = ctx.glow("fu_glowshroom", (82, 231, 225), 2.0)
    for p in ref.world["props"]:
        if p["path"].endswith("/Mush"):
            (x0, y0), (x1, y1) = p["min"], p["max"]
            cx, cy = (x0 + x1) / 2, y0 + 0.1
            z0 = level_at(sc, cx, cy)
            parts.append(cyl(cx, cy, 0.04, z0, z0 + 0.25, ctx.color("fu_glowstem", (189, 251, 239)), seg=8))
            parts.append(lathe(cx, cy, [(0.0, z0 + 0.38), (0.12, z0 + 0.3), (0.16, z0 + 0.24), (0.0, z0 + 0.25)], glow, seg=14))
    # uebrige Konsolen/Hindernisse
    for p in ref.world["props"]:
        if not p.get("collider") or any(h in p["path"] for h in HANDLED):
            continue
        (x0, y0), (x1, y1) = p["min"], p["max"]
        if (x1 - x0) * (y1 - y0) > 3.0 or (x1 - x0) < 0.15:
            continue
        a, b, w, h = p["rect"]
        img = ref.sheet.crop((a, b, a + w, b + h))
        arr = np.asarray(img)
        if (arr[..., 3] > 128).mean() < 0.15:
            continue
        cx = (x0 + x1) / 2
        avg = arr[arr[..., 3] > 128][:, :3].mean(0).astype(int)
        side = ctx.color(f"fu_box_{int(avg[0])}_{int(avg[1])}_{int(avg[2])}", tuple(int(v) for v in avg))
        nm = "fu_spr_" + "".join(ch if ch.isalnum() else "_" for ch in p["path"][-40:])
        tex = ctx.color(nm + "_c", tuple(int(v * 1.1) for v in avg))
        flat = (y1 - y0) < 0.8 * (x1 - x0) or any(t in p["path"] for t in ("Plate", "Shell", "Debris", "Sandcastle"))
        if flat:                                                             # liegt am Boden: Sprite als Oberseite
            z0 = level_at(sc, cx, (y0 + y1) / 2)
            parts.append(box(cx, (y0 + y1) / 2, x1 - x0, (y1 - y0) * 0.9, z0, z0 + 0.08, side, top=tex,
                             outline=(30, 20, 30)))
            continue
        depth = min(0.6, max(0.2, (y1 - y0) * 0.4))
        hh = max(0.2, (y1 - y0 - depth * 0.5) / 0.8)
        z0 = level_at(sc, cx, y0 + depth / 2)
        # Front = unterer Teil des Sprites (gezeichnet 0,8*hh hoch), Oberseite = Rest
        top = ctx.color(nm + "_t", tuple(int(v * 1.12) for v in avg))
        parts.append(box(cx, y0 + depth / 2, x1 - x0, depth, z0, z0 + hh, side, top=top, bevel=0.01, outline=(30, 20, 30)))
    return [{"name": "fungle_props", "coll": "Props", "kind": "parts", "parts": parts}]


# ------------------------------------------------------------------ Moebel aus den Collidern
# Fungle-Moebel (Tische, Bank, Pflanzkuebel, Felsen am Treffpunkt) sind in die Raumbilder gemalt und haben nur einen
# geschlossenen Ship-Collider. Daraus: Koerper mit der Collider-Grundflaeche, Hoehe je Art, Oberseite = Zeichnung um
# k*h nach Norden versetzt, Front = gezeichneter Streifen darunter. Im Boden wird die Zeichnung dort ausgespart.
FURN_SKIP = ("Crystal", "Cristal", "Obstacle", "GlowingMush", "mushroomjungle", "Bonfire/Tubes", "PlayerBoundary",
             "Zipline", "Ladder")
FURN_H = [("Table", 0.5), ("Rocks", 0.9), ("Chairs", 0.42), ("Bonfire", 0.35), ("Greenhouse", 0.6), ("MetalPlate", 0.06),
          ("ObjectWalls", 0.7), ("Laboratory", 0.75), ("RecRoom", 0.5), ("Cafeteria", 0.5)]


def furniture_list(sc):
    out = []
    for w, pts in sc.ref.colliders(("Ship",)):
        path = w["path"]
        if not w.get("closed") or any(s in path for s in FURN_SKIP):
            continue
        P = Polygon(pts).buffer(0)
        if not (0.15 < P.area < 12):
            continue
        if not any(g.buffer(0.02).contains(P.buffer(-0.03)) for g in sc.rooms.values()):
            continue
        h = next((hh for key, hh in FURN_H if key in path), 0.6)
        out.append((path, P, h))
    return out


def furniture_holes(sc):
    k = sc.cfg["k"]
    from shapely.affinity import translate
    return [unary_union([P, translate(P, 0, k * h)]).buffer(0.04) for _, P, h in furniture_list(sc)]


def furniture(sc, ctx):
    """Collider-Moebel als echte Koerper (19.10.): Lagerfeuer, Campingstuehle, Kiste, liegendes Fass, Felsen, Sofa,
    Sandhuegel mit Notfallknopf und Laptop, Laborkonsole, Cafeteria-Tisch; Rest (unbekannt) wie vorher als Prisma mit
    Fotoflaechen. Dazu die Dorm-Einrichtung (Betten, Fernseher, Schrank, Faesser), die in keinem eigenen Collider liegt."""
    import random
    import bm_tex as T
    from bm_spec import prism, boulder, lathe, cyl, box
    from bm_models import (bench, bed, camp_chair, campfire, chair_simple, console_block, crate_stack, lab_pedestal, laptop,
                           lift, sand_mound, table, tv_unit)
    k = sc.cfg["k"]
    SAND = (222, 170, 110)
    parts = []
    for i, (path, P, h) in enumerate(furniture_list(sc)):
        z0 = level_at(sc, P.centroid.x, P.centroid.y)
        x0, y0, x1, y1 = P.bounds
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        w, d = x1 - x0, y1 - y0
        nm = f"fu_furn{i}"
        ps = []
        if "RocksLeftOfMeetingRoom" in path:
            mats = (ctx.color(nm + "_rock", SAND), ctx.color(nm + "_rock_dark", (190, 140, 90)), None)
            rnd = random.Random(i)
            for j in range(4):
                rx, ry = w * rnd.uniform(0.18, 0.3), d * rnd.uniform(0.18, 0.3)
                px, py = x0 + rx + rnd.random() * (w - 2 * rx), y0 + ry + rnd.random() * (d - 2 * ry)
                ps.append(boulder(px, py, rx, ry, rnd.uniform(0.4, 0.9), mats, seed=i * 7 + j, outline=(120, 90, 60)))
        elif "Bonfire/Chairs" in path:
            for j, (px, py) in enumerate(((x0 + 0.3, y1 - 0.35), (cx, cy), (x1 - 0.3, y0 + 0.35))):
                ps += camp_chair(ctx, f"{nm}_c{j}", px, py, yaw=-35.0)
        elif "Bonfire" in path and w > 1.4:
            ps += campfire(ctx, nm, cx, cy, r=min(w, d) * 0.45, seed=i)
        elif "Bonfire" in path and w > d * 1.45:
            # liegendes blaues Fass (Drehkoerper, um 90 Grad gekippt, schraeg NW-SO)
            steel = ctx.color(nm + "_barrel", (90, 120, 150))
            band = ctx.color(nm + "_band", (60, 80, 100))
            L, r = min(w, 0.95), min(d, 0.6) * 0.5
            prof = [(0.0, 0.3 - L / 2), (r * 0.9, 0.3 - L / 2), (r, 0.3 - L / 2 + 0.06), (r, 0.3 + L / 2 - 0.06), (r * 0.9, 0.3 + L / 2),
                    (0.0, 0.3 + L / 2)]
            ps.append(lathe(cx, cy, prof, steel, seg=20, outline=(30, 40, 50), tilt=(90.0, 35.0, 0.3)))
            for zz in (0.3 - L * 0.25, 0.3 + L * 0.25):
                ps.append(lathe(cx, cy, [(r * 0.98, zz - 0.02), (r * 1.03, zz - 0.02), (r * 1.03, zz + 0.02), (r * 0.98, zz + 0.02)], band,
                                seg=20, tilt=(90.0, 35.0, 0.3)))
            ps.append(box(cx, cy, 0.1, 0.1, 0.0, 0.001, steel))                 # Standmarke (Collider-Mitte)
        elif "Bonfire" in path:
            ps += crate_stack(ctx, nm, cx, cy, min(w, d) * 0.8, 0.5, n=1, rgb=(76, 110, 90), dark=(50, 80, 65), tape=(230, 200, 60), seed=i)
        elif "RecRoom/Walls/ObjectWalls" in path:
            ps += sand_mound(ctx, nm, cx, cy, w / 2, d / 2, 0.45, seed=i)
            ps += crate_stack(ctx, nm + "_box", x0 + 0.25, y0 + 0.2, 0.26, 0.26, n=1, rgb=(70, 160, 150), dark=(40, 110, 100), seed=i)
        elif "RecRoom/Walls" in path:
            ps += bench(ctx, nm, x0, y0, x1, y1, h=0.36, rgb=(84, 82, 140), leg_rgb=(50, 50, 90))
            ps.append(box(cx, y1 - 0.06, w, 0.12, 0.36, 0.6, ctx.color(nm + "_back", (84, 82, 140)), bevel=0.02, outline=(30, 30, 50)))
        elif "MeetingRoom/Walls/Table" in path:
            ps += sand_mound(ctx, nm, cx, cy, w / 2, d / 2, 0.55, seed=i)
            ps.append(cyl(cx - 0.1, cy + 0.1, 0.22, 0.5, 0.56, ctx.color(nm + "_btn_base", (235, 225, 230)), seg=20, outline=(120, 90, 110)))
            ps.append(lathe(cx - 0.1, cy + 0.1, [(0.0, 0.56), (0.16, 0.56), (0.18, 0.66), (0.12, 0.74), (0.0, 0.78)],
                            ctx.glow(nm + "_btn", (240, 120, 170), 1.6), seg=16, outline=(150, 60, 100)))
            ps += laptop(ctx, nm + "_laptop", x1 - 0.45, cy - 0.25, 0.4, yaw=-20.0, w=0.3)
        elif "Laboratory/Walls" in path:
            ps += lab_pedestal(ctx, nm, cx, cy, r=min(w, d) / 2 - 0.03, h=0.75)
        elif "Cafeteria/Walls" in path:
            ps += table(ctx, nm, x0, y0, x1, y1, h=0.5, top_rgb=(70, 110, 150), leg_rgb=(120, 80, 50), round_=True, thick=0.07)
            rnd = random.Random(i)
            cush = ((200, 60, 60), (70, 90, 160), (90, 90, 100), (230, 200, 90))
            for j in range(7):
                a = 2 * math.pi * j / 7 + 0.2
                px, py = cx + (w / 2 + 0.3) * math.cos(a), cy + (d / 2 + 0.3) * math.sin(a)
                ps.append(box(px, py, 0.42, 0.36, 0.0, 0.16, ctx.color(f"{nm}_cush{j}", cush[j % 4]), bevel=0.03, rot=rnd.uniform(-25, 25),
                              outline=(40, 30, 30)))
            for j in range(3):
                px, py = x0 + w * (0.25 + 0.25 * j), cy + rnd.uniform(-0.25, 0.25)
                ps.append(lathe(px, py, [(0.0, 0.5), (0.04, 0.5), (0.04, 0.62), (0.015, 0.66), (0.015, 0.72), (0.0, 0.72)],
                                ctx.color(f"{nm}_bottle{j}", (200, 60, 50) if j != 1 else (230, 200, 80)), seg=10))
            ps.append(box(cx + 0.3, cy + 0.1, 0.3, 0.22, 0.5, 0.508, ctx.color(nm + "_paper", (235, 238, 240)), rot=12.0))
        if ps:
            parts += lift(ps, z0)
            continue
        # Rueckfall wie vorher: Prisma mit Fotoflaechen
        top_box = (x0, y0 + k * h, x1, y1 + k * h)
        a = np.asarray(ctx.ref.crop_full(x0, y0, x1, y0 + max(0.05, k * h))).reshape(-1, 3)
        med = tuple(int(v) for v in np.median(a, axis=0))
        side = ctx.color(f"fu_furn_side_{i}", med)
        top = ctx.color(f"fu_furn_top_{i}", tuple(int(v * 1.12) for v in med))
        parts.append(prism(P.simplify(0.02), z0, z0 + h, side, top=top, outline=(30, 20, 30)))
    # Dorm (aus dem Foto gemessen, 19.10.): drei Feldbetten, Fernseher auf Holzschrank an der Ostwand, gruener Schrank,
    # drei Faesser, Schlafsack; alles unter Augenhoehe, weil kein Collider darunter liegt
    BLUE, FRAME = (62, 160, 200), (40, 100, 130)
    parts += bed(ctx, "fu_dorm_bed1", -0.1, -1.2, 0.95, -0.55, head="W", frame_rgb=FRAME, mattress_rgb=BLUE, h_frame=0.16, h_mattress=0.12)
    parts += bed(ctx, "fu_dorm_bed2", 1.8, -1.18, 2.85, -0.5, head="N", frame_rgb=FRAME, mattress_rgb=BLUE, h_frame=0.16, h_mattress=0.12)
    parts += bed(ctx, "fu_dorm_bed3", 0.15, -2.9, 1.33, -2.45, head="W", frame_rgb=FRAME, mattress_rgb=BLUE, h_frame=0.16, h_mattress=0.12)
    parts += tv_unit(ctx, "fu_dorm_tv", 3.3, -0.9, 0.7, 0.5, z_cab=0.3, facing="W", rgb=(120, 80, 50), screen_rgb=(170, 220, 190), depth=0.45)
    parts += console_block(ctx, "fu_dorm_cab", 2.95, -2.85, 3.75, -2.1, 0.55, rgb=(60, 90, 70), screens=1, facing="W", lights=False, seed=3)
    for j, (px, py) in enumerate(((2.55, -2.15), (2.5, -2.55), (2.8, -2.75))):
        parts.append(cyl(px, py, 0.14, 0.0, 0.45, ctx.color(f"fu_dorm_drum{j}", (90, 120, 130)), seg=16, outline=(30, 40, 50)))
        parts.append(cyl(px, py, 0.1, 0.45, 0.47, ctx.color(f"fu_dorm_drum{j}_lid", (50, 70, 80)), seg=16))
    from bm_spec import blob
    parts.append(blob(1.75, -2.55, 0.0, 0.38, 0.28, 0.2, (ctx.color("fu_dorm_bag", (60, 90, 60)), ctx.color("fu_dorm_bag_d", (40, 65, 45))),
                      seed=5, outline=(30, 40, 30)))
    return [{"name": "fungle_furniture", "coll": "Props", "kind": "parts", "parts": parts}]
