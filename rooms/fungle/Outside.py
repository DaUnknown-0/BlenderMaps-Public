# Fungle / Strand und Dschungel (Ebene 0) - Boden aus der zusammengesetzten Zeichnung, in 10er-Kacheln.

from bm_spec import art_floor

SKY = True
TILE = 10.0


def floor(ctx, tname="Outside"):
    from shapely.geometry import box as _b
    bb = _b(*ctx.poly.bounds).buffer(0.3)
    return art_floor(ctx, f"floor_{tname}", holes=[h for h in getattr(ctx.scene, "floor_holes", []) if h.intersects(bb)])
