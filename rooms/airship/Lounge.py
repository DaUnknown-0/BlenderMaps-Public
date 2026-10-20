# Airship / Lounge - am Kartenfoto gemessen.
#
# Barhocker (lounge_stool), zwei Billardtische (lounge_pooltable1/2: Korpus (90,60,40), Filz, Bande, Taschen, Kugeln,
#   Queue; 3D, 19.10.), vier Toiletten (task_toilet, weiss (220,226,230)) hinter den Kabinentueren.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, cyl, lathe                                    # noqa: E402
from bm_models import pool_table                                                  # noqa: E402


def floor(ctx):
    holes = []
    for p in ctx.ref.world["props"]:
        if any(t in p["path"] for t in ("lounge_pooltable", "task_toilet")):
            (x0, y0), (x1, y1) = p["min"], p["max"]
            holes.append(sbox(x0, y0, x1, y1))
    return art_floor(ctx, "floor_Lounge", holes=holes)


def props(ctx):
    parts = []
    k = ctx.k
    seat = ctx.color("lo_stool", (180, 60, 70))
    leg = ctx.color("lo_stool_leg", (60, 60, 66))
    porcelain = ctx.color("lo_toilet", (220, 226, 230))
    porcd = ctx.color("lo_toilet_dark", (170, 180, 188))
    for p in ctx.ref.world["props"]:
        (x0, y0), (x1, y1) = p["min"], p["max"]
        cx = (x0 + x1) / 2
        if p["path"].endswith("lounge_stool"):
            cy = y0 + 0.12
            parts.append(cyl(cx, cy, 0.03, 0.0, 0.55, leg, seg=8))
            parts.append(cyl(cx, cy, 0.14, 0.0, 0.03, leg, seg=16))
            parts.append(cyl(cx, cy, 0.15, 0.55, 0.62, seat, seg=20, outline=(60, 20, 25)))
        elif "lounge_pooltable" in p["path"]:
            suf = p["path"].split("/")[-1]
            cy, d = (y0 + y1) / 2 - k * 0.7 * 0.5, (y1 - y0) * 0.85
            parts += pool_table(ctx, "lo_" + suf, x0, cy - d / 2, x1, cy + d / 2, h=0.7, seed=len(parts))
        elif p["path"].endswith("task_toilet"):
            cy = y0 + 0.2
            parts.append(lathe(cx, cy, [(0.0, 0.0), (0.12, 0.0), (0.16, 0.3), (0.18, 0.4), (0.0, 0.4)], porcelain, seg=20,
                               outline=(60, 70, 80)))
            parts.append(box(cx, cy + 0.2, 0.34, 0.12, 0.3, 0.8, porcd, bevel=0.02, outline=(60, 70, 80)))
    return parts
