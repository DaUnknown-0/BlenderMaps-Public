# Mira HQ / Umkleide (Locker) - am Kartenfoto gemessen (k 0,53).
# Echte Koerper: Spindreihen an der West- und Ostwand (je Spind Tuer, Griff, Lueftungsschlitze; die rechte Reihe
# duenn an der Ostwand x 10,87..11,17, weil der Spieler dort laeuft, Meldung 18.10.), drei Latten-Baenke, Vent.

from shapely.geometry import box as sbox

from bm_models import bench, locker_row, vent_grate
from bm_spec import art_floor, sprite

K = 0.53


def floor(ctx):
    return art_floor(ctx, "floor_Locker", [sbox(8.35, 2.15, 8.85, 5.2), sbox(10.7, 0.2, 11.15, 3.3), sbox(9.55, 4.2, 10.55, 4.8)])


def props(ctx):
    dy = K * 1.2
    p = locker_row(ctx, "lock_left", 8.38, 3.13 - dy, 8.75, 5.14 - dy, h=1.2, n=5, facing="E", rgb=(150, 120, 92), dark=(70, 56, 44))
    p += locker_row(ctx, "lock_right", 10.87, 1.25 - dy, 11.17, 3.25 - dy, h=1.2, n=5, facing="W", rgb=(150, 120, 92), dark=(70, 56, 44))
    for name, (x0, x1, yb, yf, yt) in {"lock_bench": (9.61, 10.52, 4.24, 4.38, 4.74), "lock_bench_l": (8.38, 8.75, 2.20, 2.34, 3.27),
                                       "lock_bench_r": (10.74, 11.11, 0.23, 0.37, 1.30)}.items():
        h = (yf - yb) / K
        p += bench(ctx, name, x0, yb, x1, yb + (yt - yf), h=h, rgb=(82, 89, 132), leg_rgb=(40, 44, 70), slats=3)
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "Locker/LockerVent")
    p += vent_grate(ctx, "lock_vent", vx0, vy0, vx1, vy1)
    return p
