# Polus - Dekontaminationsschleusen (Fehlerrunde 19.10., #266/#267: "Tueren fehlen, Pfosten nackt"): Tuerrahmen mit
# Warnstreifen um beide Schleusentueren, Duesenleisten an der Decke und Duesen an den Seitenwaenden, Bodenrost in der
# Mitte. Die Tuerblaetter selbst zeichnet Nightfall (bewegliche Tueren).

import math

from bm_spec import box, cyl, lathe

FRAME = (150, 160, 168)
STRIPE = (230, 190, 40)
NOZZLE = (90, 100, 108)


def door_frame(ctx, name, a, b, H, depth=0.22):
    """Rahmen um eine Tuer von a nach b (Tuerlinie): zwei Pfosten mit Warnstreifen, Sturz."""
    fr = ctx.color("decon_frame", FRAME)
    st = ctx.color("decon_stripe", STRIPE)
    (ax, ay), (bx, by) = a, b
    along_x = abs(bx - ax) > abs(by - ay)
    parts = []
    for px, py in (a, b):
        sx, sy = (0.1, depth) if along_x else (depth, 0.1)
        parts.append(box(px, py, sx, sy, 0.0, H, fr, bevel=0.01, outline=(30, 34, 38)))
        for k in range(4):
            z = 0.15 + 0.22 * k
            parts.append(box(px, py, sx + 0.01, sy + 0.01, z, z + 0.08, st))
    mx, my = (ax + bx) / 2, (ay + by) / 2
    L = math.hypot(bx - ax, by - ay)
    parts.append(box(mx, my, L + 0.1 if along_x else depth, depth if along_x else L + 0.1, H - 0.14, H, fr, outline=(30, 34, 38)))
    return parts


def nozzles(ctx, name, x0, y0, x1, y1, H):
    """Duesenleisten an der Decke (zwei Reihen) und Duesen an beiden Laengswaenden."""
    nz = ctx.color("decon_nozzle", NOZZLE)
    jet = ctx.glow("decon_jet", (170, 230, 255), 0.8)
    parts = []
    along_x = (x1 - x0) >= (y1 - y0)
    n = 4
    for r in (0.3, 0.7):
        if along_x:
            yy = y0 + (y1 - y0) * r
            parts.append(box((x0 + x1) / 2, yy, x1 - x0 - 0.3, 0.06, H - 0.06, H - 0.02, nz))
            pts = [(x0 + 0.3 + (x1 - x0 - 0.6) * i / (n - 1), yy) for i in range(n)]
        else:
            xx = x0 + (x1 - x0) * r
            parts.append(box(xx, (y0 + y1) / 2, 0.06, y1 - y0 - 0.3, H - 0.06, H - 0.02, nz))
            pts = [(xx, y0 + 0.3 + (y1 - y0 - 0.6) * i / (n - 1)) for i in range(n)]
        for px, py in pts:
            parts.append(lathe(px, py, [(0.0, H - 0.06), (0.04, H - 0.06), (0.025, H - 0.13), (0.0, H - 0.13)], nz, seg=10))
            parts.append(cyl(px, py, 0.018, H - 0.135, H - 0.13, jet, seg=8))
    return parts
