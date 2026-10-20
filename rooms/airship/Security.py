# Airship / Security mit Aussichtsbalkon - am Kartenfoto gemessen.
#
# Kamerapult (task_cams 7,11..9,08 / -10,08..-9,18): schwarzer Tisch mit Monitorfaecher, Hoehe 0,8 (3D, 19.10.).
# Bandgeraete links/rechts (task_tapes_left/right): Mittelsaeule, schraege Fluegel mit gruenen Anzeigen, Hoehe 1,0.
# Balkon (security_outside) haengt aussen an der Flanke: Gelaender (Sprite security_railing, Rohr (174,188,198),
#   Pfosten (66,77,82)), darunter ein Stuetzbauch (99,39,52).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, railing, sprite, tube                         # noqa: E402
from bm_models import security_desk, tape_machine                                  # noqa: E402


def floor(ctx):
    holes = []
    for suf in ("Security/task_cams", "Security/task_tapes_left", "Security/task_tapes_right"):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        holes.append(sbox(x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02))
    return art_floor(ctx, "floor_Security", holes=holes)


def props(ctx):
    parts = []
    k = ctx.k
    _, (x0, y0, x1, y1) = sprite(ctx, "Security/task_cams")
    parts += security_desk(ctx, "sec_cams", (x0 + x1) / 2, (y0 + y1) / 2 - k * 0.8 * 0.5, x1 - x0, (y1 - y0) * 0.7, h=0.8)
    for suf, nm in (("Security/task_tapes_left", "sec_tapes_l"), ("Security/task_tapes_right", "sec_tapes_r")):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        parts += tape_machine(ctx, nm, (x0 + x1) / 2, y0 + 0.3, x1 - x0, 0.6, h=1.0)
    # Balkon: Gelaender entlang der Aussenkanten, Stuetzbauch darunter
    rail = ctx.color("sec_rail", (174, 188, 198))
    path = [(5.25, -13.95), (5.25, -15.05), (8.85, -15.05), (9.65, -15.45), (9.65, -16.85), (10.85, -16.85), (10.85, -14.3)]
    parts += railing(path, 0.6, rail, r=0.025, post_step=0.45, post_r=0.025, outline=(41, 44, 49))
    belly = ctx.color("sec_belly", (99, 39, 52))
    parts.append(tube([(5.6, -14.6, -0.35), (8.8, -14.6, -0.35)], 0.35, belly, seg=16, outline=(40, 15, 20)))
    parts.append(tube([(10.25, -14.3, -0.35), (10.25, -16.5, -0.35)], 0.35, belly, seg=16, outline=(40, 15, 20)))
    return parts
