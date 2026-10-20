# Mira HQ / Storage - am Kartenfoto gemessen (k 0,53).
# Echte Koerper: hohes Regal auf seinem Collider (storageMid) mit Wangen, Boeden und Kleinkram, zweites Regal an der
# Nordwand, Kartonstapel, Among-Us-Kisten, Wischmopp mit Eimer, gruene Kiste.

from shapely.geometry import box as sbox

from bm_models import crate_stack, mop, shelf_unit
from bm_spec import art_floor, crate

CARD = ((186, 152, 108), (214, 186, 140))
K = 0.53


def floor(ctx):
    return art_floor(ctx, "floor_Storage", [sbox(19.0, 2.6, 21.1, 4.6), sbox(18.2, 4.5, 21.1, 5.7), sbox(20.4, 1.75, 21.1, 2.85)])


def props(ctx):
    k = K
    zs = (3.92 - 2.95) / k
    # Regal auf dem Collider storageMid (19,02..21,04 / 2,46..3,09), Front nach Sueden
    p = shelf_unit(ctx, "msto_shelf", 19.05, 2.48, 20.95, 3.07, h=zs, boards=5, rgb=(72, 76, 84), facing="S", seed=1)
    # Regal an der Nordwand (storage-top: Boeden mit Dosen, Kisten davor)
    p += shelf_unit(ctx, "msto_shelf_n", 19.7, 5.65, 21.0, 6.1, h=1.4, boards=4, rgb=(72, 76, 84), facing="S", seed=2)
    p += crate_stack(ctx, "msto_cardstack", 18.75, 5.05 - k * 0.6 + 0.3, 0.7, 0.6, n=2, seed=3)
    p += crate_stack(ctx, "msto_card2", 20.46, 3.38 + 0.35, 0.78, 0.7, n=1, seed=4)
    p.append(crate(ctx, "msto_card", 20.45, 4.20 - k * (zs + 0.35), 0.5, 8, 0.35, zs, *CARD, (60, 46, 30)))
    p.append(crate(ctx, "msto_card", 20.75, 2.30 - k * 0.5, 0.55, -6, 0.5, 0.0, *CARD, (60, 46, 30)))
    p.append(crate(ctx, "msto_green", 20.70, 5.25 - k * 0.55, 0.6, -10, 0.55, 0.0, (62, 97, 89), (90, 129, 111), (24, 36, 33)))
    p += mop(ctx, "msto_mop", 18.78, 2.75, h=1.25)
    return p
