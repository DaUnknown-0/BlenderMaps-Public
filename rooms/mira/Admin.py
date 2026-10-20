# Mira HQ / Admin - am Kartenfoto gemessen (k 0,53).
# Echte Koerper: Kartentisch mit Rand, leuchtender Kartenscheibe und Holo-Waenden, Tastenfeld am Westrand, Steuerpult
# davor mit Schraege und Bildschirm, Vent als Gitter.

from shapely.geometry import box as sbox

from bm_models import floor_console, map_table, vent_grate
from bm_spec import art_floor, box, sprite

K = 0.53


def floor(ctx):
    return art_floor(ctx, "floor_Admin", [sbox(19.7, 17.5, 22.15, 20.05)])


def props(ctx):
    p = map_table(ctx, "madm_map", 19.95, 18.15 - K * 0.75, 22.05, 19.95 - K * 0.75, h=0.75, rgb=(74, 105, 82), holo=(120, 230, 120))
    pad = ctx.color("madm_pad", (60, 70, 66))
    keys = ctx.glow("madm_keys", (120, 230, 140), 1.4)
    p.append(box(19.98, 18.9, 0.1, 0.3, 0.75, 0.79, pad, outline=(16, 30, 27)))
    for i in range(6):
        p.append(box(19.98 + (i % 2) * 0.04 - 0.02, 18.8 + (i // 2) * 0.08, 0.025, 0.05, 0.79, 0.8, keys))
    p += floor_console(ctx, "madm_console", 21.02, 17.77, 2.13, 0.4, (17.86 - 17.57) / K, body_rgb=(137, 153, 162), screen_rgb=(90, 170, 200))
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "Admin/AdminVent")
    p += vent_grate(ctx, "madm_vent", vx0, vy0, vx1, vy1)
    return p
