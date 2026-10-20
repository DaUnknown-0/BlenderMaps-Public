# Polus / UpperDecon (Schleuse zwischen Labor und Roehre) - Fehlerrunde 19.10. (#266/#267).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _decon import door_frame, nozzles                                             # noqa: E402


def props(ctx):
    H = ctx.scene.H
    parts = []
    # Tuer zum Labor (Westseite): Rahmen an den Kanten der Tueroeffnung zwischen den Wandbloecken (-9,41 / -10,36);
    # vorher an den Enden des Tuerblatts (-8,71 / -10,53), der suedliche Pfosten stand frei im Labor (#303)
    parts += door_frame(ctx, "ud_outer", (37.98, -9.38), (37.98, -10.39), H)
    parts += door_frame(ctx, "ud_inner", (38.36, -11.06), (39.78, -11.06), H)        # Tuer zur Roehre (Suedseite)
    parts += nozzles(ctx, "ud", 38.2, -10.85, 40.95, -8.7, H)
    return parts
