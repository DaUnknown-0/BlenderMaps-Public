# bm_objects.py - Einzelobjekte einer Karte als 3D-Koerper (alles, was die Raumdateien nicht selbst bauen).
#
# Quelle sind die Einzelbilder des Spiels (world.json props, Bogen props0.png): jedes Objekt, das bm_base nicht zum
# Grundbild zaehlt, wird gebaut, ausser es liegt schon ein gebautes Teil darauf (Raumdatei) oder es ist Tuer/Huelle.
#   Bodenobjekt: Grundflaeche = passender geschlossener Collider, sonst Streifen an der Unterkante; Hoehe aus der
#                gezeichneten Hoehe ueber der Grundflaeche (Gegenstaende ~VFAC der echten Hoehe); Front = unterer
#                Teil des Bildes, Oberseite = Rest; durchsichtige Stellen zeigen den sauberen Boden dahinter.
#   Lueckenhaft gezeichnet (Gelaender, Ketten, Pflanzen): senkrechte Tafel mit Durchsicht an der Standlinie.
#   Wandobjekt: Unterkante liegt nicht auf dem Boden (im gezeichneten Wandband) -> duenne Platte an der Wand, Hoehe
#               ueber dem Boden = Abstand zur Wandunterkante / k.
#   Flach: Bodengitter, Kabel, Matten -> Platte knapp ueber dem Boden.
# Nichts ragt durch die Decke: jede Hoehe ist auf die Raumhoehe gedeckelt.
#
# Regeln aus den Nightfall-Meldungen (18.10., Skeld in der Ich-Sicht):
#   - Schon gebaut heisst auch: die Raumdatei deckt einen guten Teil der ganzen Bildflaeche ab, nicht nur den
#     Streifen an der Unterkante (Triebwerke, Kistenstapel und Reaktorsockel standen doppelt da, einmal gebaut und
#     einmal als Klotz mit aufgeklebtem Bild).
#   - Wo der Spieler laufen kann, steht nichts Festes: Tafel oder Klotz ohne Collider darunter wird flach (Scanner-
#     Feld, Rohre ueber dem Kopf), sonst stuende er mitten in einer Platte (O2-Luefter, Reaktor).
#   - Duenn Gezeichnetes (Rohre, Kabel am Boden) wird nie eine stehende Tafel, sondern liegt flach.
#   - Wandplatten nur vor echter Wand: noerdlich des Wandfusses muss Wandmasse liegen, nicht Boden (Tuer, Flur).

import math
import re

import numpy as np
from PIL import Image
from shapely.geometry import LineString, Point, Polygon, box as sbox
from shapely.ops import unary_union

import bm_tex as T
import bm_base
from bm_spec import box, prism, wall_face_panel
from bm_models import camera_dome, console_block, crate_stack, fan_unit, wall_console, vent_grate

VFAC = 0.8
SPARSE = 0.3          # Fuellgrad darunter: Rohre/Kabel/Fluegel, nie eine stehende Tafel
TAKEN_BOX = 0.25      # Anteil der Bildflaeche, ab dem ein Objekt als von der Raumdatei gebaut gilt
SKIP =re.compile(r"(Door|HullItems|hull|camoff|Shadow|shadow|Animation|Glow|glow|Ladder|ladder|wallnub|wirestop|electrical_wires|"
                  r"Background|Parallax|Overlay|Mask|Highlight|highlight|Light$|WeaponScreen|Fans$|middlewall|adminBottom|bathroomabove|"
                  # Polus-Ventilraeder baut die Raumdatei (Admin-Rad an der Fassade, Outside.py); bm_objects setzte
                  # zusaetzlich einen schwarzen Klotz in die gezeichnete Bildflaeche (Meldung #289)
                  r"waterwheel)", re.I)
FLAT = re.compile(r"(Vent|wires|cable|rug|mat$|carpet|decal|stain|crack|puddle|tape|ramp$|Ramp$)", re.I)


def _flat_rgb(spr, bg):
    """Sprite (RGBA) auf Hintergrundfarbe gelegt -> RGB (Schirminhalt einer Konsole)."""
    base = Image.new("RGBA", spr.size, tuple(int(v) for v in bg) + (255,))
    base.alpha_composite(spr)
    return base.convert("RGB")


def _parts_footprint(parts):
    shapes = []
    for q in parts:
        try:
            t = q.get("type")
            if t == "prism" and len(q.get("pts", [])) >= 3:
                if q.get("z1", 1) - q.get("z0", 0) < 0.03 and q.get("z0", 0) < 0.05:
                    continue                                                 # flache Bodenflicken zaehlen nicht
                shapes.append(Polygon(q["pts"]).buffer(0))
            elif t == "lathe":
                shapes.append(Point(q["c"]).buffer(max(p[0] for p in q["prof"])))
            elif t == "mesh":
                xs = [v[0] for v in q["verts"]]; ys = [v[1] for v in q["verts"]]
                shapes.append(sbox(min(xs), min(ys), max(xs), max(ys)))
            elif t == "tube":
                for a, b in zip(q["pts"], q["pts"][1:]):
                    shapes.append(LineString([a[:2], b[:2]]).buffer(q.get("r", 0.05)))
        except Exception:
            pass
    return unary_union(shapes) if shapes else Polygon()


def _free_side(walk, x0, y0, x1, y1, reach=0.35):
    """Seite eines Geraets, vor der der Spieler stehen kann (Anzeigen dorthin): bevorzugt Sueden (so zeichnet es
    Among Us), bei schmalen, langen Geraeten an einer Ost-/Westwand die freie Laengsseite; sonst die freie Seite mit
    dem meisten Platz. 'S', wenn nichts frei ist (Meldung 19.10.: Konsolen an Seitenwaenden zeigten zur Wand)."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    probes = {"S": (cx, y0 - reach), "N": (cx, y1 + reach), "E": (x1 + reach, cy), "W": (x0 - reach, cy)}
    free = {}
    for side, p in probes.items():
        pt = Point(p)
        if walk.contains(pt):
            free[side] = walk.boundary.distance(pt)
    if not free:
        return "S"
    tall = (y1 - y0) > 1.3 * (x1 - x0)
    if tall and (("E" in free) or ("W" in free)):
        return max((s for s in ("E", "W") if s in free), key=lambda s: free[s])
    if "S" in free:
        return "S"
    return max(free, key=lambda s: free[s])


def _colliders(ref):
    out = []
    for w in ref.world["walls"]:
        if not w.get("closed"):
            continue
        for p in w["paths"]:
            if len(p) >= 3:
                g = Polygon(p).buffer(0)
                if 0.03 < g.area < 30:
                    out.append(g)
    return out


def _wall_segment(floor, cx, wall_y, x0, x1):
    """Bodenkante (Wand) unter einem Wandobjekt: Randsegment, das die Senkrechte x = cx bei wall_y schneidet, auf den
    x-Bereich des Objekts begrenzt und so ausgerichtet, dass der Raum links liegt (wall_face_panel). None, wenn die
    Kante fast senkrecht verlaeuft (Ost-/Westwand, zeichnet Among Us nicht)."""
    best = None
    for g in getattr(floor, "geoms", [floor]):
        for ring in [g.exterior] + list(g.interiors):
            cs = list(ring.coords)
            for p, q in zip(cs, cs[1:]):
                if min(p[0], q[0]) - 1e-6 <= cx <= max(p[0], q[0]) + 1e-6 and abs(q[0] - p[0]) > 0.05:
                    t = (cx - p[0]) / (q[0] - p[0])
                    y = p[1] + t * (q[1] - p[1])
                    d = abs(y - wall_y)
                    if d < 0.03 and (best is None or d < best[0]):
                        best = (d, p, q)
    if best is None:
        return None
    _, p, q = best
    if p[0] > q[0]:
        p, q = q, p
    sl = (q[1] - p[1]) / (q[0] - p[0])
    if abs(sl) > 3.0:
        return None
    xa, xb = max(x0, p[0]), min(x1, q[0])
    if xb - xa < 0.05:
        return None
    a, b = (xa, p[1] + sl * (xa - p[0])), (xb, p[1] + sl * (xb - p[0]))
    L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
    nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L                     # links von a -> b
    mid = ((a[0] + b[0]) / 2 + nx * 0.06, (a[1] + b[1]) / 2 + ny * 0.06)
    return (a, b) if floor.contains(Point(mid)) else (b, a)


def _clip(spr, thr=150):
    a = np.asarray(spr).copy()
    a[..., 3] = np.where(a[..., 3] >= thr, 255, 0)
    return Image.fromarray(a)


def build(sc, ctx, built_parts):
    """Meshes fuer alle noch nicht gebauten Einzelobjekte (je Raum eins). built_parts: Teile der Raumdateien."""
    ref = sc.ref
    k = sc.cfg["k"]
    taken = _parts_footprint(built_parts).buffer(0.05)
    import bm_style
    proc = bm_style.on(sc)
    cols = _colliders(ref)
    floor = sc.floor
    walk = sc.walk_real()                                                # wo der Spieler laufen kann
    by_room = {}
    stats = {"floor": 0, "card": 0, "wall": 0, "flat": 0, "skipped": 0}
    log = []
    up = T.TPPU / ref.ppu

    def room_of(pt):
        n = min(sc.rooms, key=lambda r: sc.rooms[r].distance(pt))
        return n

    def cap_h(room):
        return sc.room_h.get(room, sc.H) - 0.04

    pits = getattr(sc, "pits", [])

    def pit_at(x, y):
        """Grube unter einem gezeichneten Fusspunkt (tiefer gezeichnet um k*d) -> Tiefe d, sonst 0."""
        for pd in pits:
            d = float(pd.get("d", 0.4))
            if pd["geom"].contains(Point(x, y + k * d)):
                return d
        return 0.0

    for i, p in enumerate(ref.world["props"]):
        path = p["path"]
        if bm_base.classify(sc.key, path) != "object" or SKIP.search(bm_base._strip(path)):
            continue
        if any(t in path.rsplit("/", 1)[-1].lower() for t in ("rail", "fence")):   # Gelaender/Zaeune bauen die Raumdateien als Rohre
            continue
        (x0, y0), (x1, y1) = p["min"], p["max"]
        w, hgt = x1 - x0, y1 - y0
        if w < 0.08 or hgt < 0.08 or w * hgt > 60:
            continue
        a, b, pw, ph = p["rect"]
        spr = _clip(ref.sheet.crop((a, b, a + pw, b + ph)))
        bb = spr.getbbox()
        if bb is None:
            continue
        ppx, ppy = pw / w, ph / hgt
        vx0, vx1 = x0 + bb[0] / ppx, x0 + bb[2] / ppx
        vy1, vy0 = y1 - bb[1] / ppy, y1 - bb[3] / ppy
        spr = spr.crop(bb)
        sw, sh = spr.size
        al = np.asarray(spr)[..., 3] > 100
        fill = al.mean()
        if fill < 0.02:
            continue
        foot = sbox(vx0, vy0, vx1, vy0 + min(0.4, 0.3 * (vy1 - vy0)))
        whole = sbox(vx0, vy0, vx1, vy1)
        if taken.intersection(foot).area > 0.3 * foot.area or taken.intersection(whole).area > TAKEN_BOX * whole.area:
            stats["skipped"] += 1
            log.append((i, path, "gebaut"))
            continue
        name = f"obj_{sc.key}_{i}"
        rgb = np.asarray(spr)[..., :3][al]
        avg = tuple(int(v) for v in np.median(rgb, axis=0))
        side = ctx.color(name + "_side", tuple(int(v * 0.82) for v in avg))
        cx = (vx0 + vx1) / 2
        on_floor = floor.buffer(0.05).contains(Point(cx, vy0 + 0.04))
        room = room_of(Point(cx, vy0 + 0.1))
        out = by_room.setdefault(room, [])

        def tex_over_base(tag, crop_box, world_box):
            """Bildausschnitt; durchsichtige Stellen zeigen die saubere Vorlage an derselben Stelle.
            Prozedurale Karten: gemessene Mittelfarbe des Ausschnitts (keine Spieltextur)."""
            sub = spr.crop(crop_box)
            if proc:
                a_ = np.asarray(sub)
                vis = a_[..., :3][a_[..., 3] > 100]
                col = tuple(int(v) for v in np.median(vis, axis=0)) if len(vis) else avg
                return ctx.color(name + tag, col)
            bx0, by0, bx1, by1 = world_box
            bg = ref.crop(bx0, by0, bx1, by1).convert("RGBA").resize(sub.size)
            bg.alpha_composite(sub)
            return ctx.tex(name + tag, T.label_upscale(bg.convert("RGB"), up), uv="part")

        def alpha_tex(tag, img):
            t = ctx.tex(name + tag, img.resize((max(2, int(img.width * up)), max(2, int(img.height * up))), Image.NEAREST),
                        uv="part")
            ctx.scene.mats[t]["alpha"] = True
            return t

        def make_flat(why):
            if proc:
                # Aufgemaltes (Kabel, Flecken, Matten) entfaellt; Luftschaechte baut vent_grate als Koerper
                if re.search(r"vent", path, re.I):
                    out.extend(vent_grate(ctx, name, vx0, vy0, vx1, vy1, z=0.0, rgb=tuple(int(v) for v in avg)))
                    stats["flat"] += 1
                log.append((i, path, why + " (entfaellt)"))
                return
            t = tex_over_base("_flat", (0, 0, sw, sh), (vx0, vy0, vx1, vy1))
            out.append(box(cx, (vy0 + vy1) / 2, vx1 - vx0, vy1 - vy0, 0.0, 0.012, side, top=t))
            stats["flat"] += 1
            log.append((i, path, why))

        fm = FLAT.search(path)
        if fm and not on_floor and fm.group(0).lower() in ("wires", "cable"):
            fm = None                                                  # Kabeltafel im Wandband (Skeld Electrical)
        if fm or (vy1 - vy0) < 0.12:
            make_flat("flach")
            continue
        def wall_panel(reach=0.02):
            """Wandobjekt: Wandfuss = noerdlichste Bodenkante unter der Objektmitte (bis reach ueber dem Fusspunkt).
            Gibt den Protokollgrund zurueck, "wand" bei Erfolg."""
            ray = LineString([(cx, vy0 - 6.0), (cx, vy0 + reach)]).intersection(floor)
            if ray.is_empty:
                return "kein Boden"
            wall_y = max(c[1] for g in getattr(ray, "geoms", [ray]) for c in g.coords)
            if floor.contains(Point(cx, wall_y + 0.12)):
                return "keine Wand"                                      # Tuer/Flur statt Wand: Platte schwebte
            # Flach auf der Wand, in deren Richtung (schraege Waende: die achsparallele Platte stand im 45-Grad-Winkel
            # als schwarze Leiste heraus, Cafeteria, Meldungen 18.10.); Bild entzerrt aus dem Foto
            seg = _wall_segment(floor, cx, wall_y, vx0, vx1)
            if seg is None:
                return "keine Wandkante"
            a_, b_ = seg
            zl = [(vy0 - e[1]) / k for e in seg]
            zh = [(vy1 - e[1]) / k for e in seg]
            z0, z1 = max(0.0, min(zl)), min(cap_h(room), max(zh))
            if z1 - z0 < 0.05:
                return "zu niedrig"
            if re.search(r"camera", path, re.I):
                # Ueberwachungskamera: Dome auf Wandarm, Blick in den Raum (Wandnormale)
                L_ = ((b_[0] - a_[0]) ** 2 + (b_[1] - a_[1]) ** 2) ** 0.5 or 1.0
                nx_, ny_ = -(b_[1] - a_[1]) / L_, (b_[0] - a_[0]) / L_
                import math as _m
                # camera_dome: Linse bei yaw 0 auf -y (Blickwinkel = yaw - 90) -> yaw = Winkel(n) + 90
                out.extend(camera_dome(ctx, name, cx + nx_ * 0.08, wall_y + ny_ * 0.08, min(cap_h(room) - 0.12, z1),
                                       yaw=_m.degrees(_m.atan2(ny_, nx_)) + 90.0))
                stats["wall"] += 1
                return "kamera"
            # Wandkonsole als Koerper: Kasten mit Tiefe, Rahmen, eingelassener Schirm (Sprite = Schirminhalt), Ablage
            body_rgb = tuple(int(v * 0.9) for v in avg)
            scr = _flat_rgb(spr, body_rgb) if fill > 0.5 else None
            out.extend(wall_console(ctx, name, a_, b_, z0, z1, body_rgb=body_rgb, screen=scr, depth=min(0.12, 0.25 * (z1 - z0) + 0.04),
                                    ledge=(z1 - z0) > 0.25))
            stats["wall"] += 1
            return "wand"

        if re.search(r"camera", path, re.I):
            # Kamera: an der Wand als Dome; am Boden gezeichnete (Polus camera_off) auf einem Mast, Blick nach Sueden
            why = wall_panel(reach=0.45)
            if why != "kamera":
                import math as _m
                out.extend(camera_dome(ctx, name, cx, vy0 + 0.05, min(cap_h(room) - 0.12, 1.25), yaw=0.0))
                mast = ctx.color(name + "_mast", (60, 64, 70))
                out.append(box(cx, vy0 + 0.05, 0.04, 0.04, 0.0, min(cap_h(room) - 0.2, 1.15), mast))
                why = "kamera (Mast)"
            stats["wall"] += 1
            log.append((i, path, why))
            continue
        if not on_floor:
            why = wall_panel()
            if why != "wand":
                stats["skipped"] += 1
            log.append((i, path, why))
            continue
        # Bodenobjekt: Grundflaeche
        low_box = False
        probe = sbox(vx0 + 0.02, vy0 - 0.05, vx1 - 0.02, vy0 + 0.3)
        cand = [c for c in cols if c.intersects(probe) and abs(c.bounds[1] - vy0) < 0.35
                and c.bounds[0] > vx0 - 0.4 and c.bounds[2] < vx1 + 0.4]
        fp = max(cand, key=lambda c: c.intersection(probe).area) if cand else None
        solid = fp is not None and fp.area >= 0.02
        if not solid:
            depth = max(0.15, min(1.2, 0.35 * (vx1 - vx0), 0.45 * (vy1 - vy0)))
            fp = sbox(vx0, vy0, vx1, vy0 + depth)
            if walk.intersection(fp).area > 0.5 * fp.area:
                # Rohre/Leuchtstreifen am Boden liegen flach. Dichtes im Laufweg: Konsolen am Wandfuss werden
                # Wandplatten (Polus Specimen, Mira Storage), kleine Pulte ohne Collider (Airship Cockpit) niedrige
                # Kloetze unter Augenhoehe (die Kamera steht nie in ihnen); Grosses entfaellt (Rohre ueber dem Kopf)
                if fill < SPARSE:
                    make_flat("begehbar, flach")
                    continue
                if floor.boundary.distance(Point(cx, vy0)) < 0.4 and wall_panel(reach=0.45) == "wand":
                    log.append((i, path, "wand (Laufweg)"))
                    continue
                if (vx1 - vx0) * (vy1 - vy0) < 1.2:
                    low_box = True
                else:
                    stats["skipped"] += 1
                    log.append((i, path, "begehbar, entfaellt"))
                    continue
        dz = pit_at(cx, vy0 + 0.05)
        if dz:                                                          # Objekt steht im Grubenboden
            from shapely import affinity as _af
            fp = _af.translate(fp, 0, k * dz)
        fx0, fy0, fx1, fy1 = fp.bounds
        fence = re.search(r"(fence|Fence|gate|Gate|chain|Chain)", path) is not None
        if fill < SPARSE and not fence:
            make_flat("duenn")
            continue
        if fill < 0.45 or fence:
            # lueckenhaft gezeichnet: senkrechte Tafel mit Durchsicht (beidseitig), unten auf der Standlinie
            z1 = min(cap_h(room), (vy1 - vy0) / VFAC - dz)
            if proc:
                yc = (fy0 + fy1) / 2
                if fence:
                    # Zaun/Kette als Koerper: Pfosten alle 0,6 m, zwei Holme
                    pm = ctx.color(name + "_post", tuple(int(v) for v in avg))
                    npost = max(2, int(round((vx1 - vx0) / 0.6)) + 1)
                    for j in range(npost):
                        px_ = vx0 + (vx1 - vx0) * j / (npost - 1)
                        out.append(box(px_, yc, 0.05, 0.05, -dz, z1, pm))
                    for zz in (z1 - 0.05, z1 * 0.55):
                        out.append(box(cx, yc, vx1 - vx0, 0.035, zz - 0.02, zz + 0.02, pm))
                else:
                    # Silhouette als Scheibe in der gemessenen Farbe (Form aus dem Sprite als Referenz)
                    from bm_spec import slab, sprite_outline
                    outl = sprite_outline(spr, vx0, vy1, ppx, lambda yd: max(0.0, (yd - vy0) / VFAC - dz), min_px=20, tol=0.012)
                    if not outl.is_empty:
                        out.append(slab(outl, yc, max(0.04, min(0.3, (fy1 - fy0) * 0.6)), side, outline=(16, 20, 24)))
                stats["card"] += 1
                log.append((i, path, "tafel (Koerper)"))
                continue
            c = box(cx, (fy0 + fy1) / 2, vx1 - vx0, 0.02, -dz, z1, side)
            c["front"] = alpha_tex("_card", spr)
            c["front_both"] = True
            out.append(c)
            stats["card"] += 1
            log.append((i, path, "tafel"))
            continue
        h = min(cap_h(room) + dz, max(0.1, (vy1 - fy1 + k * dz) / VFAC))
        if low_box:
            h = min(h, 0.5)
        cut = int(round(sh * (1 - min(0.98, (VFAC * h) / max(1e-3, vy1 - vy0)))))  # Zeile Oberseite/Front im Bild
        cut = max(0, min(sh - 1, cut))
        front = top = None
        if sh - cut > 2:
            front = tex_over_base("_front", (0, cut, sw, sh), (vx0, vy0, vx1, vy0 + (sh - cut) / ppy))
        if cut > 2:
            top = tex_over_base("_top", (0, 0, sw, cut), (vx0, vy1 - cut / ppy, vx1, vy1))
        if re.search(r"box|crate|carton", path, re.I) and fp.area < 1.5:
            # Kiste/Karton als Koerper mit Fase, Deckelfuge und Klebeband
            out.extend(crate_stack(ctx, name, (fx0 + fx1) / 2, (fy0 + fy1) / 2, min(fx1 - fx0, fy1 - fy0), h - dz, n=1,
                                   rgb=tuple(int(v) for v in avg), dark=tuple(int(v * 0.7) for v in avg), seed=i))
        elif re.search(r"fan", path, re.I) and fp.area < 0.5:
            out.extend(fan_unit(ctx, name, cx, fy0 + 0.05, min(cap_h(room) - 0.2, 0.55), r=min(0.3, (fx1 - fx0) * 0.45), yaw=-90.0))
            out.append(box(cx, fy0 + 0.05, 0.05, 0.05, 0.0, 0.3, ctx.color(name + "_foot", (60, 64, 70))))
        elif fp.area < 2.0 and (fx1 - fx0) < 2.2 and (fy1 - fy0) < 2.2:
            # kleines Geraet/Schrank: gebauter Korpus mit Anzeigen und Leuchten statt Kasten mit aufgeklebtem Bild
            fac = _free_side(walk, fx0, fy0, fx1, fy1)
            nscr = 1 if ((fx1 - fx0) if fac in ("S", "N") else (fy1 - fy0)) < 0.7 else 2
            out.extend(console_block(ctx, name, fx0, fy0, fx1, fy1, h - dz, rgb=tuple(int(v * 0.9) for v in avg), screens=nscr,
                                     lights=(h - dz) > 0.35, seed=i, facing=fac))
        else:
            out.append(prism(fp.simplify(0.01), -dz, h - dz, side, bevel=0.02, outline=(16, 20, 24)))
        stats["floor"] += 1
        log.append((i, path, "klotz" if solid else ("klotz niedrig" if low_box else "klotz ohne Collider")))
    # Konsolen-Garantie (19.10., User: "Collider und platzierte Sachen muessen uebereinstimmen"): jede Aufgabenkonsole
    # hat einen geschlossenen Collider mit ihrem Namen. Liegt auf ihm kein KLEINES Teil (grosse Koerper wie Spindreihen,
    # Dropship-Rumpf oder Theken zaehlen nicht, sie verdecken die Konsole nur), wird dort ein Koerper gebaut: Wandgeraet
    # auf der naechsten Bodenkante (beliebige Richtung, Anzeige zum Boden), sonst ein Standpult mit Anzeige zur freien
    # Seite. Vorher gingen Konsolen verloren, die eine Raumdatei "abdeckte" (Mira Locker O2, Reactor Handscanner).
    own = [q for ps in by_room.values() for q in ps]
    small, devs = [], []
    for q in list(built_parts) + own:
        try:
            fpq = _parts_footprint([q])
        except Exception:
            continue
        if fpq.is_empty or fpq.area >= 2.5:
            continue
        small.append(fpq)
        # geraeteartig: klein (< 1 m2) und bis ueber 0,6 hoch (Bullaugen, Rohre, Stuehle zaehlen nicht als Konsole)
        try:
            if q.get("type") == "prism":
                z1 = q["z1"]
            elif q.get("type") == "mesh":
                z1 = max(v[2] for v in q["verts"])
            else:
                z1 = 0.0
        except Exception:
            z1 = 0.0
        if 0.015 < fpq.area < 1.0 and z1 >= 0.6:
            devs.append(fpq)
    small_u = unary_union(small).buffer(0) if small else Polygon()
    devs_u = unary_union(devs).buffer(0) if devs else Polygon()
    CONS = re.compile(r"(Console|panel_|task_|Task_|taks_|DivertRecieve|RubyTask)", re.I)
    NOT = re.compile(r"(Vent|Camera|Shadow|Text|ladder|Ladder|Door|EmergencyConsole|MapConsole|TaskAddConsole|dummy)", re.I)
    edges = []
    for g_ in getattr(floor, "geoms", [floor]):
        for ring in [g_.exterior] + list(g_.interiors):
            cs = list(ring.coords)
            for a_, b_ in zip(cs, cs[1:]):
                if math.hypot(b_[0] - a_[0], b_[1] - a_[1]) > 0.08:
                    edges.append((a_, b_))
    todo = []
    seen_names = set()
    for w in ref.world["walls"]:
        pth = w["path"]
        if not w.get("closed") or w["layer"] not in ("ShortObjects", "Objects") or not CONS.search(pth) or NOT.search(pth):
            continue
        for ppath in w["paths"]:
            if len(ppath) >= 3:
                todo.append((pth, Polygon(ppath).buffer(0), False, pth.split("/")[1] if "/" in pth else ""))
                seen_names.add(pth.rsplit("/", 1)[-1])
    # Konsolen ohne geschlossenen Collider (Airship fast alle, Mira Handscanner, Polus panel_*): Lage aus der
    # Konsolenliste, Grundflaeche 0,5 x 0,5
    for c in ref.world.get("consoles", []):
        nm = c.get("name", "")
        if "pos" not in c or nm in seen_names or NOT.search(nm) or not CONS.search(nm):
            continue
        x, y = c["pos"]
        todo.append((f"{c.get('room', '')}/{nm}", sbox(x - 0.25, y - 0.25, x + 0.25, y + 0.25), True, c.get("room", "")))
    for pth, g, by_pos, croom in todo:
        if True:
            if g.is_empty or g.area < 0.02 or g.area > 4.0:
                continue
            # Konsolenlage liegt 0,3..0,5 vor der Wand: ein Wandgeraet dort gilt bis 0,55 Abstand als vorhanden
            if by_pos and devs_u.distance(g.centroid) < 0.55:
                continue
            if small_u.intersection(g).area > 0.2 * g.area or small_u.distance(g.centroid) < 0.08:
                continue
            gx0, gy0, gx1, gy1 = g.bounds
            ccx, ccy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
            room = room_of(Point(ccx, ccy))
            name = "con_" + re.sub(r"[^A-Za-z0-9]+", "_", pth.rsplit("/", 2)[-1])[-40:] + f"_{len(log)}"
            rgb = (96, 104, 112)
            out = by_room.setdefault(room, [])
            # naechste Bodenkante (Wand) zum Collider
            best = None
            cr = (croom or "").lower()
            for a_, b_ in edges:
                ln = LineString([a_, b_])
                d_ = ln.distance(Point(ccx, ccy))
                if d_ >= 0.9:
                    continue
                # Kanten des eigenen Raums bevorzugen: die Konsole liegt in der Wandmasse, die naechste Kante kann zum
                # Nachbarraum gehoeren (Mira Handscanner landeten an der Decontam-Wand)
                er = (room_of(ln.interpolate(0.5, normalized=True)) or "").lower()
                score = d_ + (0.0 if (cr and (cr in er or er in cr)) else 0.6)
                if best is None or score < best[0]:
                    best = (score, a_, b_, ln)
            if best is not None:
                d_, a_, b_, ln = best
                L_ = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
                ux, uy = (b_[0] - a_[0]) / L_, (b_[1] - a_[1]) / L_
                nx_, ny_ = -uy, ux                                           # links von a -> b
                mid = ((a_[0] + b_[0]) / 2 + nx_ * 0.06, (a_[1] + b_[1]) / 2 + ny_ * 0.06)
                if not floor.contains(Point(mid)):                          # Boden muss links liegen
                    a_, b_ = b_, a_
                    ux, uy = -ux, -uy
                # Spannweite = Projektion des Colliders auf die Kante, mindestens 0,45
                ts = [((x - a_[0]) * ux + (y - a_[1]) * uy) for x, y in g.exterior.coords]
                t0, t1 = max(0.0, min(ts)), min(L_, max(ts))
                if t1 - t0 < 0.45:
                    tm = (t0 + t1) / 2
                    t0, t1 = max(0.0, tm - 0.225), min(L_, tm + 0.225)
                pa = (a_[0] + ux * t0, a_[1] + uy * t0)
                pb = (a_[0] + ux * t1, a_[1] + uy * t1)
                out.extend(wall_console(ctx, name, pa, pb, 0.85, 1.45, body_rgb=rgb, screen=None, depth=0.12, ledge=True))
                log.append((-1, pth, "konsole (Wand, Garantie)"))
            else:
                fac = _free_side(walk, gx0, gy0, gx1, gy1)
                h = 1.0 if walk.intersection(g).area < 0.3 * g.area else 0.5
                out.extend(console_block(ctx, name, gx0, gy0, gx1, gy1, h, rgb=rgb, screens=1, lights=True, seed=len(log), facing=fac))
                log.append((-1, pth, "konsole (Pult, Garantie)"))
            stats["floor"] += 1
    meshes = [{"name": f"objects_{r}", "coll": r, "kind": "parts", "parts": ps} for r, ps in sorted(by_room.items()) if ps]
    try:
        import json as _json
        (sc.out / "objects_log.json").write_text(_json.dumps(log, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception:
        pass
    return meshes, stats
