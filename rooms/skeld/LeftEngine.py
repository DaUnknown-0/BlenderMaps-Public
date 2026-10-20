# Skeld / Upper Engine (LeftEngine) - Maschine siehe _engine.py.
import importlib.util
from pathlib import Path

from shapely.geometry import box as sbox

from bm_spec import art_floor, vent

H = 2.0
_s = importlib.util.spec_from_file_location("eng", Path(__file__).with_name("_engine.py"))
_m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_m)


def floor(ctx):
    return art_floor(ctx, "floor_LeftEngine", [sbox(-19.6, -0.95, -15.7, 2.45), sbox(-19.65, 1.3, -18.7, 2.95)])


def props(ctx):
    return _m.engine(ctx, "L", 0.0) + vent(ctx, "LeftEngine/LEngineVent")
