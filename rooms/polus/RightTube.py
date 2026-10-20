# Polus / RightTube (untere Roehre LowerDecon - Specimen) - Fehlerrunde 19.10. abends (#306: "Gang mit lila Boden und
# nackten Waenden"). Die Roehrenwaende haben im Original Fenster: dort, wo die Shadow-Collider Luecken haben (Licht faellt
# durch), Nordwand x 28,55..29,95 und 30,72..32,14, Suedwand x 29,62..31,13 und 31,80..33,25. Fenster als Koerper:
# heller Rahmen, dunkelblaue Scheibe mit zwei hellen Schlieren, auf beiden Seiten der Wand.

from shapely.geometry import Point

from bm_spec import box

GLASS = (52, 66, 140)
FRAME = (150, 160, 168)
STREAK = (120, 140, 210)
Z0, Z1 = 0.45, 0.95
# (x0, x1, Wand-Mittellinie y, Richtung zur Roehre (+1 = Roehre suedlich der Wand -> Innenflaeche Richtung -y))
WINDOWS = [(28.55, 29.95, -20.38, -1), (30.72, 32.14, -20.37, -1),
           (29.62, 31.13, -21.16, +1), (31.80, 33.25, -21.16, +1)]


def _face(fl, x, y_mid, step):
    """Erste Stelle ab der Wandmitte (in Schrittrichtung), an der Boden beginnt: dort liegt die Wandflaeche."""
    y = y_mid
    for _ in range(60):
        y += step
        if fl.contains(Point(x, y)):
            return y - step / 2
    return None


def props(ctx):
    fl = ctx.scene.floor
    frame = ctx.color("rt_window_frame", FRAME)
    glass = ctx.glow("rt_window_glass", GLASS, 0.4)
    streak = ctx.glow("rt_window_streak", STREAK, 0.6)
    parts = []
    for x0, x1, ym, d in WINDOWS:
        cx, w = (x0 + x1) / 2, x1 - x0
        for step in (0.01 * d, -0.01 * d):
            yf = _face(fl, cx, ym, step)
            if yf is None:
                continue
            s = 1 if step > 0 else -1                                          # Seite, auf der der Boden liegt
            y = yf + s * 0.008
            parts.append(box(cx, y, w + 0.08, 0.016, Z0 - 0.04, Z1 + 0.04, frame))
            parts.append(box(cx, y + s * 0.006, w, 0.006, Z0, Z1, glass))
            for f in (0.3, 0.62):
                parts.append(box(x0 + w * f, y + s * 0.01, 0.05, 0.003, Z0 + 0.08, Z1 - 0.08, streak))
    return parts
