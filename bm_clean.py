# bm_clean.py - gemalte Abbilder gebauter Moebel aus der Vorlage entfernen.
#
# Among Us zeichnet jedes Objekt schraeg von oben: ein Punkt (x, y, z) liegt im Bild bei (x, y + k*z). Steht ein
# Objekt in 3D, ist sein gemaltes Abbild auf Boden und Wandband (Vorlage fuer deren Texturen) falsch. drawn_region()
# liefert die Bildflaeche eines gebauten Teils, inpaint() fuellt diese Flaechen aus der Umgebung:
#   1. Versatzkopie: dieselbe Flaeche um (dx, dy) verschoben, wo sie frei ist und zur gleichen Zone gehoert (gleicher
#      Raumboden bzw. gleiches Wandband); Kandidaten zuerst waagerecht (Wandbaender, Fliesenreihen), dann senkrecht,
#      dann schraeg; bewertet am Rand der Luecke. So bleiben Fliesenmuster, Fugen und Wandleisten erhalten.
#   2. Was keine passende Quelle findet: Telea-Inpainting, auf die Palette der Umgebung zurueckgerechnet.

import math

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import unary_union


def drawn_region(q, k):
    """Bildflaeche eines Teils (Weltkoordinaten der Zeichnung) oder None."""
    t = q.get("type")
    try:
        if t == "prism" and len(q.get("pts", [])) >= 3:
            fp = Polygon(q["pts"]).buffer(0)
            z0, z1 = q["z0"], q["z1"]
            n = max(2, int(math.ceil(abs(z1 - z0) * k / 0.04)) + 1)
            return unary_union([affinity.translate(fp, 0, k * (z0 + (z1 - z0) * i / (n - 1))) for i in range(n)])
        if t == "lathe":
            cx, cy = q["c"]
            return unary_union([Point(cx, cy + k * z).buffer(max(r, 0.01)) for r, z in q["prof"]]).convex_hull
        if t == "tube":
            pts = [(p[0], p[1] + k * p[2]) for p in q["pts"]]
            return LineString(pts).buffer(q.get("r", 0.05)) if len(pts) > 1 else None
        if t == "mesh":
            vs = q["verts"]
            polys = []
            for f in q["faces"]:
                pp = [(vs[i][0], vs[i][1] + k * vs[i][2]) for i in f]
                hp = MultiPoint(pp).convex_hull
                if hp.area > 1e-6:
                    polys.append(hp)
            return unary_union(polys) if polys else None
    except Exception:
        return None
    return None


def holes_of(parts, k, max_area=15.0, max_z=4.0, pad=0.07):
    """Bildflaechen aller nennenswerten Teile (keine flachen Bodenauflagen, kein Gelaende)."""
    out = []
    for q in parts:
        t = q.get("type")
        if t == "prism":
            if q["z1"] - q["z0"] < 0.03:                                # Aufkleber, Bodenplatten
                continue
            if q["z1"] > max_z or Polygon(q["pts"]).area > max_area:
                continue
        g = drawn_region(q, k)
        if g is None or g.is_empty or g.area > max_area * 2.5:
            continue
        out.append(g.buffer(pad))
    return out


def _raster(ref, geoms, shape, value=1, out=None):
    m = np.zeros(shape, np.int32) if out is None else out
    for g in geoms:
        for pg in getattr(g, "geoms", [g]):
            if pg.is_empty or pg.geom_type != "Polygon":
                continue
            ext = np.array([ref.w2p(x, y) for x, y in pg.exterior.coords], np.float32).round().astype(np.int32)
            cv2.fillPoly(m, [ext], int(value))
            for h in pg.interiors:
                hi = np.array([ref.w2p(x, y) for x, y in h.coords], np.float32).round().astype(np.int32)
                cv2.fillPoly(m, [hi], 0)
    return m


def zones(sc, B):
    """Zonenbild: Raumboden = 1..n, Wandband ueber Nordkanten = 1001.., sonst 0."""
    ref = sc.ref
    shape = (ref.image.height, ref.image.width)
    lab = np.zeros(shape, np.int32)
    names = sorted(sc.rooms)
    for i, n in enumerate(names):
        _raster(ref, [sc.rooms[n]], shape, i + 1, lab)
    for e in sc.wall_edges():
        if e["kind"] != "north":
            continue
        (ax, ay), (bx, by) = e["a"], e["b"]
        quad = Polygon([(ax, ay), (bx, by), (bx, by + B), (ax, ay + B)])
        i = names.index(e["room"]) if e["room"] in names else 0
        _raster(ref, [quad], shape, 1001 + i, lab)
    for j, pd in enumerate(getattr(sc, "pits", [])):                   # Grubenboden: gezeichnet um k*d tiefer
        _raster(ref, [affinity.translate(pd["geom"], 0, -sc.cfg["k"] * float(pd.get("d", 0.4)))], shape, 3001 + j, lab)
    return lab


def _pieces(comp, stats, n, tile=200, big=300):
    """Flecken als (lokale Maske, x0, y0); grosse Flecken in Kacheln geteilt (Suche bleibt klein)."""
    for ci in range(1, n):
        x, y, w, h, area = stats[ci]
        if area < 4:
            continue
        if w <= big and h <= big:
            yield comp[y:y + h, x:x + w] == ci, x, y
            continue
        for ty in range(y, y + h, tile):
            for tx in range(x, x + w, tile):
                sub = comp[ty:min(y + h, ty + tile), tx:min(x + w, tx + tile)] == ci
                if sub.sum() >= 4:
                    yield sub, tx, ty


def inpaint(img, mask, lab, max_shift=None, log=None):
    """img HxWx3 uint8, mask HxW bool (zu fuellen), lab HxW int (Zone je Pixel). Rueckgabe gefuelltes Bild.
    Gearbeitet wird je Fleck in seinem Ausschnitt (grosse Flecken kachelweise), nie auf dem ganzen Bild."""
    img = img.copy()
    H, W = mask.shape
    n, comp, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    filled_total, telea_px, npieces = 0, 0, 0
    todo_all = mask.copy()
    ms = max_shift or 3
    for cm_local, ox, oy in _pieces(comp, stats, n):
        npieces += 1
        h, w = cm_local.shape
        ly0, lx0 = np.nonzero(cm_local)
        ys, xs = ly0 + oy, lx0 + ox
        # Rand: 3 px um den Fleck, ausserhalb jeder Luecke
        pad = 4
        y0, y1, x0, x1 = max(0, oy - pad), min(H, oy + h + pad), max(0, ox - pad), min(W, ox + w + pad)
        win = np.zeros((y1 - y0, x1 - x0), np.uint8)
        win[ys - y0, xs - x0] = 1
        ring = cv2.dilate(win, np.ones((7, 7), np.uint8)).astype(bool) & ~mask[y0:y1, x0:x1]
        rys, rxs = np.nonzero(ring)
        if len(rys) == 0:
            continue
        rys = rys + y0
        rxs = rxs + x0
        if len(rys) > 4000:                                          # Rand ausduennen
            sel = np.linspace(0, len(rys) - 1, 4000).astype(int)
            rys, rxs = rys[sel], rxs[sel]
        cands = []
        sw = max(2, w // 40)
        sh_ = max(2, h // 40)
        for s in range(0, int(ms * w) + 1, sw):                     # waagerecht
            cands += [(w + s, 0), (-(w + s), 0)]
        for s in range(0, int(ms * h) + 1, sh_):                    # senkrecht
            cands += [(0, h + s), (0, -(h + s))]
        st = max(4, int(max(w, h) / 6))
        for dx in range(-2 * w - st, 2 * w + st + 1, st):           # schraeg (grob)
            for dy in range(-2 * h - st, 2 * h + st + 1, st):
                if abs(dx) > w * 0.6 or abs(dy) > h * 0.6:
                    cands.append((dx, dy))
        scored = []
        rl = lab[rys, rxs]
        rc = img[rys, rxs].astype(np.int16)
        for dx, dy in cands:
            sy, sx = rys + dy, rxs + dx
            ok = (sy >= 0) & (sy < H) & (sx >= 0) & (sx < W)
            if ok.mean() < 0.6:
                continue
            sy_, sx_ = sy[ok], sx[ok]
            ok2 = (~mask[sy_, sx_]) & (lab[sy_, sx_] == rl[ok])
            if ok2.sum() < 0.5 * len(rys):
                continue
            d = np.abs(img[sy_[ok2], sx_[ok2]].astype(np.int16) - rc[ok][ok2]).mean()
            scored.append((d + 0.002 * (abs(dx) + abs(dy)), dx, dy))
        scored.sort()
        left = np.ones(len(ys), bool)
        for d, dx, dy in scored[:12]:
            if not left.any():
                break
            ly, lx = ys[left], xs[left]
            sy, sx = ly + dy, lx + dx
            ok = (sy >= 0) & (sy < H) & (sx >= 0) & (sx < W)
            good = np.zeros(len(ly), bool)
            good[ok] = (~mask[sy[ok], sx[ok]]) & ((lab[sy[ok], sx[ok]] == lab[ly[ok], lx[ok]]) | (lab[ly[ok], lx[ok]] == 0))
            img[ly[good], lx[good]] = img[sy[good], sx[good]]
            idx = np.nonzero(left)[0][good]
            left[idx] = False
            filled_total += int(good.sum())
        done = ~left
        todo_all[ys[done], xs[done]] = False
    if todo_all.any():
        telea_px = int(todo_all.sum())
        img = cv2.inpaint(img, todo_all.astype(np.uint8), 5, cv2.INPAINT_TELEA)
    if log is not None:
        log.update({"components": n - 1, "pieces": npieces, "copied": filled_total, "telea": telea_px})
    return img
