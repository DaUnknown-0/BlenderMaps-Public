# Airship / Medbay - am Kartenfoto gemessen.
#
# Boden Holz (140,101,87) (Zeichnung). Zwei Liegen an der Theke (Bild 23,6..24,4 und 25,2..26,0 / -9,25..-8,0):
#   Polster (201,219,222), Gestell (165,182,198). Wartebereich: Tisch (medbay_table (181,165,96)) mit Zeitschrift und
#   Becher, Sessel (medbaychair (74,130,137)/(46,81,99)), Personenwaage mit Saeule (medbay_scale) (3D, 19.10.).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, cyl, office_chair, sprite                     # noqa: E402
from bm_models import scale_device, table                                          # noqa: E402

BEDS = [(24.0, -9.25, -8.0), (25.6, -9.25, -8.0)]


def floor(ctx):
    return art_floor(ctx, "floor_Medbay", holes=[sbox(23.5, -9.35, 26.2, -7.95), sbox(28.4, -7.7, 29.8, -6.85),
                                                sbox(21.85, -5.95, 22.6, -5.0)])


def props(ctx):
    parts = []
    pad = ctx.color("mb_bed", (201, 219, 222))
    frame = ctx.color("mb_bed_frame", (165, 182, 198))
    for x, y0, y1 in BEDS:
        parts.append(box(x, (y0 + y1) / 2, 0.62, y1 - y0, 0.0, 0.40, frame, outline=(60, 70, 80)))
        parts.append(box(x, (y0 + y1) / 2, 0.58, y1 - y0 - 0.04, 0.40, 0.52, pad, bevel=0.03, outline=(90, 100, 110)))
    _, (x0, y0, x1, y1) = sprite(ctx, "Medbay/medbay_table")
    cy, d = (y0 + y1) / 2 - 0.12, (y1 - y0) * 0.75
    parts += table(ctx, "mb_table", x0, cy - d / 2, x1, cy + d / 2, h=0.42, top_rgb=(181, 165, 96), leg_rgb=(140, 114, 63))
    parts.append(box((x0 + x1) / 2 + 0.1, cy, 0.3, 0.22, 0.42, 0.435, ctx.color("mb_mag", (210, 80, 130)), rot=18.0, outline=(60, 20, 40)))
    parts.append(box((x0 + x1) / 2 + 0.12, cy + 0.02, 0.2, 0.14, 0.435, 0.44, ctx.color("mb_mag2", (90, 150, 220)), rot=18.0))
    parts.append(cyl(x0 + 0.18, cy - 0.1, 0.04, 0.42, 0.5, ctx.color("mb_cup", (235, 238, 240)), seg=12, outline=(120, 120, 130)))
    parts.append(cyl(x1 - 0.14, cy + 0.12, 0.06, 0.42, 0.46, ctx.color("mb_red", (220, 60, 60)), seg=12, outline=(100, 20, 20)))
    for cx in (27.85, 28.4, 29.85, 30.4):
        parts += office_chair(ctx, "mb_chair", cx, -6.95 + (0.0 if cx < 29 else 0.0), (74, 130, 137), (46, 81, 99),
                              (13, 27, 27), back="N", w=0.48, seat_z=0.36, back_top=0.8)
    _, (x0, y0, x1, y1) = sprite(ctx, "Medbay/medbay_scale")
    parts += scale_device(ctx, "mb_scale", (x0 + x1) / 2, y0 + 0.24, yaw=0.0)
    return parts
