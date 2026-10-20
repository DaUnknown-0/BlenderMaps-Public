# Airship / Storage (Frachtraum) - am Kartenfoto gemessen.
#
# Boden grau mit Pfeilmuster (Zeichnung). Frachtstapel mit Netzen (storage_cargo1top, storage_cargo1, storage_cargo2top,
#   storage_cargo3top): Kistenblock (145,112,77)/(132,94,66) mit gelbem Rohrnetz (211,181,71) (3D, 19.10.).
# Pappkartons im Norden (219,196,145)/(195,167,129) als Kartonstapel, Tresor (task_safe (214,161,55)/(195,108,41))
#   mit Tuer, Drehgriff und Scharnieren.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, sprite, vent                                  # noqa: E402
from bm_models import cargo_net, crate_stack, safe_box                              # noqa: E402

CARGO = [("Storage/storage_cargo1top", 1.6), ("Storage/storage_cargo1", 0.95), ("Storage/storage_cargo2top", 0.85),
         ("Storage/storage_cargo3top", 0.55)]
BOXES = [(37.10, 37.95, 2.00, 2.85, 0.70), (38.00, 39.40, 2.05, 3.25, 0.90)]


def floor(ctx):
    holes = []
    for suf, h in CARGO + [("Storage/task_safe", 0.9)]:
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        holes.append(sbox(x0, y0, x1, y1))
    holes += [sbox(x0, y0, x1, y1 + 0.3) for x0, x1, y0, y1, h in BOXES]
    return art_floor(ctx, "floor_Storage", holes=holes)


def props(ctx):
    parts = []
    k = ctx.k
    # Grundrisse auf den nicht begehbaren Bereich beschneiden (Collider des Spiels): die Netze aus der Zeichnung ragten
    # bis 5 m2 in den Laufweg (Collider-Abgleich 19.10.)
    walk = ctx.scene.walk_real().buffer(0.03)

    def clip(x0, y0, x1, y1):
        """Groesstes achsparalleles Rechteck im nicht begehbaren Teil des Sprite-Rechtecks (Rastersuche 0,1 m)."""
        import numpy as np
        g = sbox(x0, y0, x1, y1).difference(walk)
        if g.is_empty or g.area < 0.25:
            return x0, y0, x1, y1
        from shapely.geometry import Point as _P
        st = 0.1
        xs = np.arange(x0 + st / 2, x1, st)
        ys = np.arange(y0 + st / 2, y1, st)
        ok = np.array([[g.contains(_P(x, y)) for x in xs] for y in ys])
        best = (0.0, (x0, y0, x1, y1))
        H, W = ok.shape
        hist = np.zeros(W, int)
        for r in range(H):
            hist = np.where(ok[r], hist + 1, 0)
            for c0 in range(W):
                if hist[c0] == 0:
                    continue
                hmin = hist[c0]
                for c1 in range(c0, W):
                    hmin = min(hmin, hist[c1])
                    if hmin == 0:
                        break
                    area = (c1 - c0 + 1) * hmin
                    if area > best[0]:
                        best = (area, (xs[c0] - st / 2, ys[r] - (hmin - 1) * st - st / 2, xs[c1] + st / 2, ys[r] + st / 2))
        return best[1]
    for i, (suf, h) in enumerate(CARGO):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        cx0, cy0, cx1, cy1 = clip(x0, y0, x1, y1)                         # Grundriss aus den Collidern
        if (cx1 - cx0) * (cy1 - cy0) < 0.4:
            continue
        h = max(0.6, min(2.4, (y1 - cy1) / k))                              # gezeichnete Front ueber dem Grundriss
        parts += cargo_net(ctx, f"as_cargo{i}", cx0, cy0, cx1, cy1, h, seed=i,
                           cells=(max(2, int((cx1 - cx0) / 0.8)), max(2, int((cy1 - cy0) / 0.8))))
    for j, (x0, x1, y0, y1, h) in enumerate(BOXES):
        cy = (y0 + y1) / 2 - k * h
        if x1 - x0 > 1.1:
            for q, cx in enumerate((x0 + 0.37, x1 - 0.37)):
                parts += crate_stack(ctx, f"as_box{j}_{q}", cx, cy, 0.68, h, n=2, rgb=(219, 196, 145), dark=(195, 167, 129), seed=j * 2 + q)
        else:
            parts += crate_stack(ctx, f"as_box{j}", (x0 + x1) / 2, cy, min(x1 - x0, 0.85), h, n=1, rgb=(219, 196, 145),
                                 dark=(195, 167, 129), seed=j)
    _, (x0, y0, x1, y1) = sprite(ctx, "Storage/task_safe")
    sx0, sy0, sx1, sy1 = clip(x0, y0, x1, y0 + 0.56)
    parts += safe_box(ctx, "as_safe", (sx0 + sx1) / 2, (sy0 + sy1) / 2, sx1 - sx0, sy1 - sy0, 0.9, facing="S")
    parts += vent(ctx, "Storage/StorageVent")
    return parts
