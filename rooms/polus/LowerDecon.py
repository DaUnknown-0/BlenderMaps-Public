# Polus / LowerDecon (Schleuse zwischen Admin und Roehre) - Fehlerrunde 19.10. (#272..#274).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _decon import door_frame, nozzles                                             # noqa: E402


def props(ctx):
    H = ctx.scene.H
    parts = []
    parts += door_frame(ctx, "ld_outer", (23.14, -23.2), (24.65, -23.2), H)        # Tuer zum Admin (Nordseite)
    parts += door_frame(ctx, "ld_inner", (25.49, -23.64), (25.49, -25.48), H)         # Tuer zur Roehre (Ostseite)
    parts += nozzles(ctx, "ld", 22.8, -25.6, 25.3, -23.4, H)
    return parts
