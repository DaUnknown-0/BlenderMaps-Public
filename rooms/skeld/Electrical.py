# Skeld / Electrical - am Kartenfoto gemessen.
# Schaltschrankblock in der Mitte (electric_frontset): Front im Bild -10,35..-9,18 mit Warnschild und Sicherungs-
# leisten -> 1,98 hoch, Oberseite (90,93,79) bis -8,95; Seiten (126,150,151). Raum daher 2,4 hoch.
# Kabel bleiben Malerei auf dem Boden (so zeichnet sie das Spiel). Vent ElecVent.

from shapely.geometry import box as sbox

from bm_spec import art_container, art_floor, vent

H = 2.4


def floor(ctx):
    return art_floor(ctx, "floor_Electrical", [sbox(-10.3, -10.45, -7.68, -8.9)])


def props(ctx):
    # Schalttafelblock: Korpus mit Anzeigen und Leuchten auf Sued- UND Nordseite (echte Koerper)
    from bm_models import console_block
    h = (-9.18 + 10.35) / ctx.k
    parts = console_block(ctx, "ele_block", -10.25, -10.35, -7.72, -10.12, h, rgb=(126, 150, 151), screens=3, facing="S", seed=1)
    parts += console_block(ctx, "ele_block_n", -10.25, -10.35, -7.72, -10.12, h, rgb=(126, 150, 151), screens=3, facing="N", seed=2)
    return parts + vent(ctx, "Electrical/ElecVent")
