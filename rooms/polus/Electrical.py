# Polus / Electrical - am Kartenfoto gemessen.
#
# Boden: Zeichnung (graue Fliesen (123,134,148) mit Fugen). Nordwand: beiges Band (159,151,132) mit orangem Streifen,
#   Fenster und zwei Kaesten (Sprites panel_electrical_elec, panel_data) - bleibt Zeichnung.
# Absperrbock (Sprite barrier 1,61..2,28 / -10,44..-9,80): zwei schwarze Fuesse, Balken rot-weiss (173,81,90).
# Bodengitter (ElectricalVent). Generatorhof (Transformatoren, Zaun) gehoert zum Gelaende (Outside.py).

from shapely.geometry import box as sbox
from bm_spec import art_floor, box, tube, vent


def floor(ctx):
    return art_floor(ctx, "floor_Electrical", holes=[sbox(1.6, -10.45, 2.3, -9.8)])


def props(ctx):
    parts = []
    # Absperrbock: rot-weiss gestreifter Balken auf zwei A-Boecken (#254: wirkte als roter Dreibein-Scheinwerfer)
    from bm_models import sawhorse
    parts += sawhorse(ctx, "el_barrier", 1.92, -10.27, L=0.70, yaw=22.0, h=0.55)
    parts += vent(ctx, "Electrical/ElectricalVent")
    return parts
