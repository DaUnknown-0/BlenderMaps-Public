# Airship / Electrical (Gangsystem) - am Kartenfoto gemessen. Boden und Wandstuecke: Zeichnung.
# Elektro-Kapseln (Sprites ElectroPod): Glaszylinder (107,138,165) leuchtend mit Fassungen (82,105,99), Hoehe 1,2.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from bm_spec import cyl                                                           # noqa: E402


def props(ctx):
    parts = []
    glass = ctx.glow("ae_pod", (107, 138, 165), 1.2)
    cap = ctx.color("ae_pod_cap", (82, 105, 99))
    for p in ctx.ref.world["props"]:
        if "ElectroPod" in p["path"]:
            (x0, y0), (x1, y1) = p["min"], p["max"]
            cx, cy = (x0 + x1) / 2, y0 + 0.22
            parts.append(cyl(cx, cy, 0.2, 0.0, 0.15, cap, seg=20, outline=(24, 28, 33)))
            parts.append(cyl(cx, cy, 0.17, 0.15, 1.05, glass, seg=20))
            parts.append(cyl(cx, cy, 0.2, 1.05, 1.2, cap, seg=20, outline=(24, 28, 33)))
    return parts
