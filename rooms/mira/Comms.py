# Mira HQ / Comms - Pult an der Nordwand mit zwei Monitoren, Tastatur und Stuhl; Seitenschrank mit Anzeigen an der
# Ostwand (Front nach Westen). Alles gebaut, kein Bild.
from shapely.geometry import box as sbox

from bm_models import console_block, monitor, table
from bm_spec import art_floor, box, office_chair

K = 0.53


def floor(ctx):
    return art_floor(ctx, "floor_Comms", [sbox(14.2, 4.75, 16.95, 5.75), sbox(16.6, 2.4, 17.1, 4.65)])


def props(ctx):
    h = (5.10 - 4.80) / K
    p = table(ctx, "mcom_desk", 14.24, 4.80, 16.92, 5.42, h=h, top_rgb=(82, 65, 57), leg_rgb=(50, 44, 40))
    p += monitor(ctx, "mcom_mon_l", 14.92, 5.2, h, 0.5, 0.36, yaw=0.0)
    p += monitor(ctx, "mcom_mon_r", 16.2, 5.2, h, 0.6, 0.42, yaw=0.0)
    keys = ctx.color("mcom_keys", (40, 42, 46))
    p.append(box(15.55, 4.95, 0.42, 0.14, h, h + 0.015, keys, bevel=0.005))
    p += office_chair(ctx, "mcom_chair", 15.55, 4.45, (63, 134, 135), (46, 94, 107), (0, 0, 0), back="S", w=0.44, back_top=0.8)
    p += console_block(ctx, "mcom_side", 16.64, 2.45 - K * 0.62, 17.08, 4.59 - K * 0.62, 0.62, rgb=(82, 65, 57), screens=3, facing="W", seed=5)
    return p
