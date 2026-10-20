# Mira HQ / Office - am Kartenfoto gemessen (k 0,53).
# Echte Koerper: drei Schreibtische mit Beinen, Monitore, Tastaturen, Rechnertower, Buerostuehle, Basketball, Stehlampe,
# Papierkorb, Ausgabesaeule, Vent als Gitter.

from shapely.geometry import box as sbox

from bm_models import floor_console, monitor, table, vent_grate
from bm_spec import art_floor, box, cyl, lathe, office_chair, sprite, tube

K = 0.53


def floor(ctx):
    return art_floor(ctx, "floor_Office", [sbox(12.8, 17.0, 14.55, 18.6), sbox(12.8, 18.8, 14.4, 19.85), sbox(16.05, 18.0, 16.65, 19.4)])


def props(ctx):
    k = K
    p = []
    wood, legs = (82, 65, 57), (50, 44, 40)
    keys = ctx.color("off_keys", (40, 42, 46))
    p += table(ctx, "off_deskb", 12.86, 17.05, 14.49, 18.16, h=(17.42 - 17.05) / k, top_rgb=wood, leg_rgb=legs)
    hb = (17.42 - 17.05) / k
    p += monitor(ctx, "off_monb", 13.55, 17.85, hb, 0.5, 0.36, yaw=0.0)
    p.append(box(13.55, 17.35, 0.4, 0.14, hb, hb + 0.015, keys, bevel=0.005))
    hm = (19.20 - 18.84) / k
    p += table(ctx, "off_deskm", 12.87, 18.84, 14.30, 19.42, h=hm, top_rgb=wood, leg_rgb=legs)
    p += monitor(ctx, "off_monm", 13.6, 19.25, hm, 0.46, 0.34, yaw=0.0)
    p.append(box(13.6, 18.98, 0.4, 0.14, hm, hm + 0.015, keys, bevel=0.005))
    hr = (18.40 - 18.06) / k
    p += table(ctx, "off_deskr", 16.13, 18.06, 16.57, 18.95, h=hr, top_rgb=wood, leg_rgb=legs)
    tower = ctx.color("off_tower", (60, 62, 68))
    p.append(box(16.47, 18.7, 0.16, 0.36, 0.0, 0.42, tower, bevel=0.01, outline=(20, 20, 24)))
    p += monitor(ctx, "off_monr", 16.35, 18.35, hr, 0.36, 0.3, yaw=90.0)
    # Stuhl 2 stand 0,2 im Laufbereich (Meldung 19.10. "Collider passt nicht"): an die Wand geschoben
    for (cx, cy, back) in ((13.30, 20.70, "S"), (15.30, 21.05, "S"), (13.20, 17.35, "S"), (13.45, 18.35, "N")):
        p += office_chair(ctx, "off_chair", cx, cy - k * 0.4, (42, 40, 40), (25, 24, 24), (0, 0, 0), back=back, w=0.40, back_top=0.78)
    ball = ctx.color("off_ball", (255, 109, 0))
    import math
    prof = [(0.0, 0.0)] + [(0.27 * math.sin(a / 12 * math.pi), 0.27 - 0.27 * math.cos(a / 12 * math.pi)) for a in range(1, 12)] + [(0.0, 0.54)]
    p.append(lathe(14.76, 17.68 - k * 0.27, prof, ball, seg=28, outline=(107, 52, 24)))
    grey = ctx.color("off_lamp", (139, 137, 134))
    p.append(tube([(12.85, 19.30, 0.0), (12.85, 19.30, 1.1), (13.05, 19.40, 1.25)], 0.03, grey, outline=(40, 40, 40)))
    p.append(cyl(12.85, 19.30, 0.18, 0.0, 0.03, grey, seg=20, outline=(40, 40, 40)))
    p.append(lathe(13.05, 19.40, [(0.0, 1.2), (0.12, 1.2), (0.16, 1.36), (0.0, 1.36)], ctx.glow("off_lampshade", (250, 240, 200), 1.0), seg=16))
    p.append(cyl(16.19, 19.85 - k * 0.5, 0.18, 0.0, 0.5, grey, seg=24, outline=(40, 40, 40)))
    p.append(cyl(16.19, 19.85 - k * 0.5, 0.16, 0.48, 0.5, ctx.color("off_bin_in", (30, 30, 34)), seg=24))
    p += floor_console(ctx, "off_stand", 16.19, 19.79, 0.56, 0.4, 1.25, body_rgb=(150, 160, 175), slope=False, screen_rgb=(120, 200, 220))
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "Office/OfficeVent")
    p += vent_grate(ctx, "off_vent", vx0, vy0, vx1, vy1)
    return p
