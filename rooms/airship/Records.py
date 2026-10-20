# Airship / Records - am Kartenfoto gemessen.
#
# Zwei hohe Aktenregale mit Rundbogen (records_left nach Suedost, records_right nach Suedwest gedreht, rote Korpusse
#   mit bunten Ordnern), runder Lesetisch mit Papieren, zwei Stuehle, zwei flache Aktenschraenke (3D, 19.10.).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, office_chair, sprite                          # noqa: E402
from bm_models import arch_bookcase, table                                         # noqa: E402


def floor(ctx):
    holes = []
    for suf in ("Records/records_table", "Records/task_records4", "Records/task_records4 (1)"):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        holes.append(sbox(x0, y0, x1, y1))
    return art_floor(ctx, "floor_Records", holes=holes)


def props(ctx):
    parts = []
    for suf, yaw, nm, sd in (("Records/records_left", 45.0, "rec_left", 1), ("Records/records_right", -45.0, "rec_right", 2)):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        parts += arch_bookcase(ctx, nm, (x0 + x1) / 2, y0 + 0.62, 1.3, 0.6, 2.0, yaw=yaw, seed=sd)
    _, (x0, y0, x1, y1) = sprite(ctx, "Records/records_table")
    parts += table(ctx, "rec_table", x0, y0 - 0.12, x1, y1 - 0.12, h=0.45, top_rgb=(222, 170, 170), leg_rgb=(120, 80, 50),
                   pedestal=True, round_=True)
    paper = ctx.color("rec_paper", (235, 238, 240))
    for dx, dy, rot in ((-0.12, 0.1, 15.0), (0.22, -0.08, -20.0)):
        parts.append(box((x0 + x1) / 2 + dx, (y0 + y1) / 2 - 0.12 + dy, 0.26, 0.2, 0.45, 0.46, paper, rot=rot, outline=(120, 120, 130)))
    for suf, back in (("Records/records_chair_left", "W"), ("Records/records_chair_right", "E")):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        parts += office_chair(ctx, "rec_chair", (x0 + x1) / 2, y0 + 0.25, (150, 60, 60), (110, 40, 40), (40, 15, 15),
                              back=back, w=0.45, seat_z=0.36, back_top=0.8)
    for suf, yaw, nm, sd in (("Records/task_records4", -45.0, "rec_cab_r", 3), ("Records/task_records4 (1)", 45.0, "rec_cab_l", 4)):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        parts += arch_bookcase(ctx, nm, (x0 + x1) / 2, y0 + 0.42, 0.9, 0.42, 1.1, yaw=yaw, rgb=(90, 100, 110), dark=(60, 66, 74),
                               arch=False, rows=3, seed=sd)
    return parts
