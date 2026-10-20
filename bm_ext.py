# bm_ext.py: optionale Erweiterungen (weitere Karten aus anderen Repos), die BlenderMaps nur laedt, wenn sie lokal
# eingetragen sind. Ohne bm_local.json laeuft alles ohne Erweiterung.
#
# bm_local.json (nicht versioniert, neben dieser Datei):  {"ext_dirs": ["D:/pfad/zur/erweiterung", ...]}
# Relative Pfade gelten ab dem BlenderMaps-Ordner. Aus jedem Ordner werden alle bm_ext_*.py geladen; jede Datei hat
# register(api) und meldet dort an:
#   api.add_map(key, source=..., scene=..., rooms=...)
#       source: Eintrag fuer atlas_import.SOURCES (Vorlage der Karte)
#       scene:  Eintrag fuer bm_scene.MAPCFG (Farben, k, H, ...)
#       rooms:  Ordner mit _map.py und Raumdateien der Karte (sonst rooms/<key>/)
#       Die Karte zaehlt damit zu bm_ref.ATLAS_MAPS (Vorlage unter atlasdata/<key>/).
#   api.add_models(pfad)
#       Python-Datei mit Requisiten-Modellen; wird am Ende von rooms/_atlas_models.py importiert und meldet sich dort
#       selbst an: @AM.model("art", ...) fuer neue Arten, AM.variant(fn) fuer Kartenvarianten oeffentlicher Arten
#       (fn(P, kind) -> Teileliste oder None; None = oeffentliche Art bauen).
# register() soll nur anmelden und keine bm_*-Module importieren (die laden die Erweiterung selbst beim Import).

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / "bm_local.json"

SOURCES = {}       # karte -> atlas_import-Quelle
SCENES = {}        # karte -> MAPCFG-Eintrag
ROOMS = {}         # karte -> Ordner der Raumdateien
MAPS = []          # zusaetzliche Atlas-Karten in Anmeldereihenfolge
MODEL_FILES = []   # Modell-Dateien fuer rooms/_atlas_models.py
LOADED = []        # geladene Erweiterungsdateien

_done = False


class Api:
    root = ROOT

    def __init__(self, path):
        self.path = Path(path)
        self.dir = self.path.parent

    def add_map(self, key, source=None, scene=None, rooms=None):
        if key not in MAPS:
            MAPS.append(key)
        if source is not None:
            SOURCES[key] = source
        if scene is not None:
            SCENES[key] = scene
        if rooms is not None:
            ROOMS[key] = Path(rooms)

    def add_models(self, path):
        p = Path(path)
        if not p.is_absolute():
            p = self.dir / p
        if p not in MODEL_FILES:
            MODEL_FILES.append(p)


def ext_dirs():
    if not LOCAL.exists():
        return []
    try:
        cfg = json.loads(LOCAL.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"bm_ext: {LOCAL.name} nicht lesbar ({e}), keine Erweiterungen")
        return []
    out = []
    for d in cfg.get("ext_dirs", []):
        p = Path(d)
        if not p.is_absolute():
            p = ROOT / p
        if p.is_dir():
            out.append(p)
        else:
            print(f"bm_ext: Erweiterungsordner fehlt: {p}")
    return out


def load():
    """Liest bm_local.json und meldet alle Erweiterungen an (einmal je Prozess)."""
    global _done
    if _done:
        return
    _done = True
    for d in ext_dirs():
        for f in sorted(d.glob("bm_ext_*.py")):
            name = f.stem
            sp = importlib.util.spec_from_file_location(name, f)
            mod = importlib.util.module_from_spec(sp)
            sys.modules[name] = mod
            sp.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register(Api(f))
            LOADED.append(f)


def maps():
    load()
    return tuple(MAPS)


def sources():
    load()
    return dict(SOURCES)


def scenes():
    load()
    return dict(SCENES)


def rooms_dir(key):
    """Ordner der Raumdateien einer Karte: Erweiterung oder rooms/<key>/."""
    load()
    return ROOMS.get(key, ROOT / "rooms" / key)


def load_models():
    """Modell-Dateien der Erweiterungen importieren (aufgerufen am Ende von rooms/_atlas_models.py)."""
    load()
    for p in MODEL_FILES:
        name = "bm_extmodels_" + p.stem
        if name in sys.modules:
            continue
        sp = importlib.util.spec_from_file_location(name, p)
        mod = importlib.util.module_from_spec(sp)
        sys.modules[name] = mod
        sp.loader.exec_module(mod)


def unknown(key, known):
    """Sauberer Abbruch fuer eine nicht angemeldete Karte."""
    hint = " (Erweiterung in bm_local.json eintragen)" if not LOADED else ""
    raise SystemExit(f"Karte '{key}' unbekannt{hint}. Bekannt: {', '.join(sorted(known))}")
