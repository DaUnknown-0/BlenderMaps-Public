# Skeld / Lower Engine (RightEngine) - dieselbe Maschine wie oben, um -12,21 versetzt (Sprites engineLeft/Right).
import importlib.util
from pathlib import Path

from shapely.geometry import box as sbox

from bm_spec import art_floor, vent

H = 2.0
DY = -12.21
_s = importlib.util.spec_from_file_location("eng", Path(__file__).with_name("_engine.py"))
_m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_m)


def floor(ctx):
    return art_floor(ctx, "floor_RightEngine", [sbox(-19.6, -0.95 + DY, -15.7, 2.45 + DY), sbox(-19.65, 1.3 + DY, -18.7, 2.95 + DY)])


def props(ctx):
    return _m.engine(ctx, "R", DY) + vent(ctx, "RightEngine/Ground/REngineVent")
