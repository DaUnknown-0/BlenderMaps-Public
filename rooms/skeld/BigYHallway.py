# Skeld / BigY-Flur: Boden und Waende aus der Zeichnung, Vent gebaut.
from bm_spec import art_floor, vent
from shapely.geometry import box as sbox


def floor(ctx):
    return art_floor(ctx, "floor_BigYHallway")


def props(ctx):
    return vent(ctx, "BigYHallway/BigYVent")
