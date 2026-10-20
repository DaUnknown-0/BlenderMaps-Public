# Airship / Comms - am Kartenfoto gemessen. Boden gruenlich (Zeichnung). Funkpult (task_comms: Standkonsole mit
# Schraege, Gehaeuse (99,117,115), blaue Anzeige (60,80,159), zwei Drehknoepfe) an der Nordwand, Hoehe 0,75 (3D, 19.10.);
# uebrige Schraenke bleiben Wandzeichnung.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import box                                                           # noqa: E402
from bm_models import floor_console                                               # noqa: E402

BAND_HOLES = [sbox(-14.95, 2.1, -13.5, 3.1)]


def props(ctx):
    parts = floor_console(ctx, "ac_console", -14.23, 2.38, 1.3, 0.42, 0.75, body_rgb=(99, 117, 115), yaw=0.0, screen_rgb=(60, 80, 159))
    knob = ctx.color("ac_knob", (40, 44, 50))
    for x in (-14.65, -13.81):
        parts.append(box(x, 2.17, 0.06, 0.06, 0.75, 0.8, knob, bevel=0.01))
    return parts
