# bm_base.py - "saubere" Vorlage einer Karte: nur die Grundbilder der Raeume (Boden, Wandband), ohne die darauf
# gelegten Einzelobjekte (Kisten, Betten, Konsolen, Maschinen). Was die Objekte verdecken, ist im Grundbild Boden.
#   base_image(ref, include=None) -> PIL-Bild in Atlas-Groesse (ref.ppu), Pixel ohne Grundbild = Atlas.
import re
import numpy as np
from PIL import Image

# Grundbilder je Karte (Pfadmuster, ohne "<Karte>Ship(Clone)/")
BASE = {
    "skeld": [r"^[A-Za-z]+/Ground$", r"Hallway$", r"^TinyHallway/Room$", r"/Ground/shields_floor$", r"/weap_platform$"],
    "mira": [r"^Walls/[A-Za-z]+Walls$", r"^Walls/Dropship"],
    "polus": [r"^[A-Za-z]+/Walls$"],
    "airship": [r"_main$", r"/cockpit_bg$", r"^Exterior/", r"/security_outside$", r"/meeting_side$", r"/hallway_window$",
                r"/halls_photos$"],
}
# Wandteile, die zum Wandband gehoeren (bleiben im Bild der Waende, nicht im Boden)
WALLS = {
    "skeld": [r"walltop$", r"_walls(\.png)?$", r"/reactor_wall$", r"/reactor_ceiling$", r"/weap_wall$", r"shields_backwall$",
              r"shields_wallside$", r"comms_wallstuff$", r"/shields_walls$"],
}


def _strip(path):
    return re.sub(r"^[^/]*\(Clone\)/", "", path)


def classify(key, path):
    p = _strip(path)
    if any(re.search(rx, p) for rx in BASE.get(key, [])):
        return "base"
    if any(re.search(rx, p) for rx in WALLS.get(key, [])):
        return "wall"
    return "object"


def compose(ref, kinds=("base",), background=None):
    """Sprites der gewuenschten Arten in Unity-Reihenfolge (z gross = hinten) auf die Atlasflaeche malen."""
    W, H = ref.image.size
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    props = [p for p in ref.world["props"] if classify(ref.key, p["path"]) in kinds]
    for p in sorted(props, key=lambda p: (-p.get("z", 0), p.get("sortOrder", 0))):
        (x0, y0), (x1, y1) = p["min"], p["max"]
        a, b, w, h = p["rect"]
        spr = ref.sheet.crop((a, b, a + w, b + h))
        px0, py0 = ref.w2p(x0, y1)
        px1, py1 = ref.w2p(x1, y0)
        tw, th = max(1, int(round(px1 - px0))), max(1, int(round(py1 - py0)))
        canvas.alpha_composite(spr.resize((tw, th), Image.LANCZOS), (int(round(px0)), int(round(py0))))
    if background is not None:
        bg = background.convert("RGBA").copy()
        bg.alpha_composite(canvas)
        return bg.convert("RGB"), np.asarray(canvas)[..., 3] > 128
    return canvas, np.asarray(canvas)[..., 3] > 128
