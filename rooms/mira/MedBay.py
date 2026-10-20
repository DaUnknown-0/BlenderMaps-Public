# Mira HQ / MedBay - am Kartenfoto gemessen (k 0,53).
# Echte Koerper: fuenf Krankenbetten (Fuesse, Rahmen, Matratze, Kissen, Decke, Kopf-/Fussteil), Scanner (Sockel,
# Leuchtring, vier Sensor-Pods), Vent als Gitter.

from shapely.geometry import box as sbox

from bm_models import bed, scanner, vent_grate
from bm_spec import art_floor, sprite

BEDS = [(13.76, 14.54), (15.15, 15.93), (16.23, 17.01)]
K = 0.53


def floor(ctx):
    holes = [sbox(x0 - 0.05, 0.75, x1 + 0.05, 2.0) for x0, x1 in BEDS]
    holes += [sbox(13.65, -2.3, 14.8, -0.55), sbox(16.0, -2.3, 17.15, -0.55), sbox(15.4, -0.4, 17.1, 0.65)]
    return art_floor(ctx, "floor_MedBay", holes)


def props(ctx):
    p = []
    for i, (x0, x1) in enumerate(BEDS):
        p += bed(ctx, f"mmed_bed{i}", x0, 0.80, x1, 0.80 + (1.91 - 1.19), head="N", frame_rgb=(123, 130, 148), mattress_rgb=(222, 226, 236),
                 blanket_rgb=(110, 150, 205), h_frame=0.3, h_mattress=0.14)
    for i, (x0, x1) in enumerate(((13.70, 14.72), (16.06, 17.08))):
        p += bed(ctx, f"mmed_hbed{i}", x0, -2.23, x1, -0.85, head="N", frame_rgb=(123, 130, 148), mattress_rgb=(222, 226, 236),
                 blanket_rgb=(110, 150, 205), h_frame=0.28, h_mattress=0.14)
    p += scanner(ctx, "mmed_scan", 16.24, 0.12 - K * 0.36, r=0.58, rgb=(176, 207, 211), side_rgb=(99, 153, 162))
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "MedBay/MedVent")
    p += vent_grate(ctx, "mmed_vent", vx0, vy0, vx1, vy1)
    return p
