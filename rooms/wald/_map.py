# wald (eigene Karte) - Requisiten aus den Sprites des Spiels, Grundriss = Collider (rooms/_atlas_props.py).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _atlas_props as AP                                                         # noqa: E402


def extra(sc, ctx):
    return AP.build(sc, ctx)


def adjust(sc):
    AP.room_heights(sc)
