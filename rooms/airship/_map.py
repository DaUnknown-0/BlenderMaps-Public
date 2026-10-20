# Airship - kartenweite Teile: Schiffsumriss (Deck), Rumpfflanke, Wolken.
#
# Gemessen (bm_analyze.py colors): Deck (82,36,38), Flanke (150,40,56), Leere (41,23,56), Wolken (242,248,250) mit
#   Schatten (170..173,207,231..234). Grenze Deck/Flanke bei y -13,55 (Bug -10,25, aus der Nightfall-Messung).

import cv2
import numpy as np
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

DECK = (82, 36, 38)
FLANK = (150, 40, 56)
DECK_EDGE_Y = -13.55


# Gap Room (Collider-Ringe GapRoom/Walls): zwei Stege auf Deckebene, unterer Boden rechts (Leiter ladder_gap, Band
# 1,345), Grube dazwischen (-1,796, Nightfall-Messung). Leiterschacht zum Meeting Room (ladder_meeting, Band 4,147)
# zwischen den Shadow-Fluchten x 3,87..5,19 bis y 13,84.
LEFT_LEDGE = [(2.93, 6.23), (4.29, 6.23), (4.53, 6.63), (4.52, 7.72), (5.76, 7.73), (5.98, 7.88), (5.97, 9.47),
              (5.63, 9.69), (3.66, 9.70), (3.53, 9.51), (3.33, 9.43), (2.92, 9.50)]
RIGHT_LEDGE = [(9.54, 9.51), (9.55, 7.86), (9.74, 7.74), (15.06, 7.74), (15.06, 7.97), (16.20, 7.98), (16.20, 9.95),
               (15.06, 9.94), (15.06, 9.46), (14.96, 9.30), (13.85, 9.05), (13.80, 9.14), (13.80, 9.72), (9.86, 9.71)]
GAP_LOWER = [(9.55, 5.53), (15.10, 5.53), (15.10, 7.74), (9.55, 7.74)]
GAP_BOX = (2.92, 5.52, 16.20, 9.72)
LOWER_Z, PIT_Z, MEET_Z = -1.345, -1.796, 4.147
SHAFT = [(3.87, 9.66), (5.19, 9.66), (5.19, 13.84), (3.87, 13.84)]
CLOUD_CUT = [(8.0, -25.0), (16.0, -25.0), (16.0, -17.0), (8.0, -17.0)]   # Wolke unter dem Aussichtsbalkon


def adjust(sc):
    cut = Polygon(CLOUD_CUT)
    sc.floor = sc.floor.difference(cut).buffer(0)
    for n in sc.rooms:
        sc.rooms[n] = sc.rooms[n].difference(cut).buffer(0)
    low = Polygon(GAP_LOWER)
    led = unary_union([Polygon(LEFT_LEDGE), Polygon(RIGHT_LEDGE)]).buffer(0)
    pit = sbox(*GAP_BOX).difference(led).difference(low).buffer(0)
    shaft = Polygon(SHAFT)
    sc.rooms["GapRoom"] = sc.rooms["GapRoom"].difference(low).difference(pit).buffer(0)
    sc.rooms["GapLower"] = low
    sc.rooms["GapPit"] = pit
    sc.rooms["MeetingLadder"] = shaft.difference(sc.rooms["GapRoom"]).difference(sc.rooms["MeetingRoom"]).buffer(0)
    for n in list(sc.rooms):
        if n not in ("GapRoom", "GapLower", "GapPit", "MeetingLadder"):
            sc.rooms[n] = sc.rooms[n].difference(unary_union([low, pit, shaft])).buffer(0)
    sc.floor = unary_union([sc.floor, low, pit, sc.rooms["MeetingLadder"]]).buffer(0)
    sc.wall_holes = [h.difference(unary_union([low, pit, shaft])).buffer(0) for h in getattr(sc, "wall_holes", [])]


OPEN_AREAS = [(5.0, -17.5, 11.0, -13.62),      # Aussichtsbalkon unter Security (Gelaender statt Wand)
              (-16.8, -17.5, -12.0, -12.1)]    # Planke und Aussichtsdeck vor dem Ejection-Raum (Meldungen 18.10.)


def open_edge(sc, a, b, nx, ny):
    """Balkon und Planke haengen aussen an der Flanke: Kanten ohne Wand."""
    from shapely.geometry import Point
    mid = Point((a[0] + b[0]) / 2 + nx * 0.05, (a[1] + b[1]) / 2 + ny * 0.05)
    if any(sbox(*r).contains(mid) for r in OPEN_AREAS):
        return True
    # Alle anderen Kanten sind Wand: Wolken hinter der Kante (Engine-Westseite, Cockpit-Front) galten sonst als
    # offen, und man sah unter dem Boden den Himmel (Pruefrunde 18.10.)
    return False


def ship(sc):
    """Deck = zusammenhaengende Deckfarbe (geschlossen) plus alle Boeden mit Kontur; Flanke darunter gehoert nicht dazu."""
    ref = sc.ref
    img = ref.img.astype(np.int16)
    m = (np.abs(img - np.array(DECK)).sum(-1) <= 8).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 5.0 * ref.ppu * ref.ppu]   # alle Deckteile ab 5 E^2
    cs, _ = cv2.findContours(np.isin(lab, keep).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    deck = unary_union([Polygon([ref.p2w(p[0][0], p[0][1]) for p in c]).buffer(0) for c in cs
                        if cv2.contourArea(c) > 100]).simplify(0.04)
    Wr = sum(r[3] for r in sc.cfg["rim"]) + 0.005
    sc.deck = deck
    return unary_union([deck, sc.floor.buffer(Wr, join_style=2, mitre_limit=3.0)]).buffer(0)


FLANK_LIGHT = (175, 65, 72)
CLOUD_W, CLOUD_S = (242, 248, 250), (170, 207, 234)
BAND_DRAWN = 2.14       # helles Flankenband (gemessen bei x 40: -13,6..-15,74)
KEEL_Z = -7.0           # Kiel (Nightfall-Wert, Zeichnung zeigt nur die Silhouette)
KEEL_IN = 3.0           # Flanke laeuft unten 3 Einheiten nach innen


def extra(sc, ctx):
    """Rumpf: senkrechtes helles Band vom Deck bis zum Knick, darunter schraeg nach innen zum Kiel, Kielboden.
    Wolken: jede gezeichnete Wolke als zwei bis vier Ballen (weiss, Unterseite im Schattenblau)."""
    from bm_scene import tri
    from bm_spec import blob
    H, k = sc.H, sc.cfg["k"]
    zk = H - BAND_DRAWN / k
    light = ctx.color("air_flank_light", FLANK_LIGHT)
    main = ctx.color("air_flank", FLANK)
    # nur das Deck: Anbauten haengen an der Flanke; Ausnahme Planke/Aussichtsdeck (OPEN_AREAS[1]): die liegt ausserhalb
    # der Decksilhouette, das Band lief quer durch sie (Meldungen 18.10. #177/#178)
    plank = sc.floor.intersection(sbox(*OPEN_AREAS[1])).buffer(0.05)
    deck = unary_union([sc.deck, plank]).buffer(0.3).buffer(-0.3)
    outer = max(getattr(deck, "geoms", [deck]), key=lambda g: g.area)
    outer = Polygon(outer.exterior)
    ring = list(outer.exterior.simplify(0.08).coords)
    if not outer.exterior.is_ccw:
        ring = ring[::-1]
    inner = outer.buffer(-KEEL_IN, join_style=2, mitre_limit=3.0)
    inner = max(getattr(inner, "geoms", [inner]), key=lambda g: g.area) if not inner.is_empty else outer
    band, slope = [], []
    from shapely.geometry import Point
    for a, b in zip(ring, ring[1:]):
        L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        if L < 1e-4:
            continue
        n = ((b[1] - a[1]) / L, -(b[0] - a[0]) / L)                       # CCW: rechts = aussen
        band.append({"a": a, "b": b, "n": n, "uv": [0, 0, 1, 1]})
    # Suedseite: gezeichnetes Band (Bullaugen, Fenster, Markierungen) als Textur; was davor gebaut ist (Balkon, Planke),
    # wird aus dem Band herausgerechnet
    import bm_tex as T
    from PIL import Image as _I
    fx0, fx1, fy0, fy1 = -17.84, 42.96, -13.55 - BAND_DRAWN, -13.55
    # Flankenband prozedural: helles Band mit Plattenfugen, Nieten und Bullaugen alle 2,6 m (Zeichnung nur Referenz)
    from PIL import ImageDraw as _ID
    ww, hh = 3040, int(3040 * BAND_DRAWN / (fx1 - fx0))
    _im = _I.new("RGB", (ww, hh), FLANK_LIGHT)
    _d = _ID.Draw(_im)
    ppm = ww / (fx1 - fx0)
    dark = (99, 39, 52)
    for i in range(int((fx1 - fx0) / 2.6) + 1):
        xx = int(i * 2.6 * ppm)
        _d.line([(xx, 0), (xx, hh)], fill=dark, width=3)
        cx_, cy_ = int((i + 0.5) * 2.6 * ppm), hh // 2
        r_ = int(0.32 * ppm)
        _d.ellipse([cx_ - r_ - 6, cy_ - r_ - 6, cx_ + r_ + 6, cy_ + r_ + 6], fill=(60, 40, 44))
        _d.ellipse([cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_], fill=(150, 190, 220))
        for j in range(6):
            _d.ellipse([int((i + 0.08 + j * 0.16) * 2.6 * ppm) - 3, 10, int((i + 0.08 + j * 0.16) * 2.6 * ppm) + 3, 16], fill=dark)
    _d.rectangle([0, 0, ww, 8], fill=dark)
    _d.rectangle([0, hh - 8, ww, hh], fill=dark)
    south_mat = ctx.tex("air_flank_south", _im, uv="quad")
    south = [q for q in band if q["n"][1] < -0.7 and max(abs(q["a"][1] - fy1), abs(q["b"][1] - fy1)) < 0.25
             and min(q["a"][0], q["b"][0]) >= fx0 - 0.1 and max(q["a"][0], q["b"][0]) <= fx1 + 0.1]
    for q in south:
        q["uv"] = [(q["a"][0] - fx0) / (fx1 - fx0), 0.0, (q["b"][0] - fx0) / (fx1 - fx0), 1.0]
    band = [q for q in band if q not in south]
    # Planke/Aussichtsdeck: Band nur unterhalb des Bodens (oben offen, Gelaender statt Wand; Meldung 18.10. #178)
    pr = sbox(*OPEN_AREAS[1]).buffer(0.2)
    low = [q for q in band if pr.contains(Point((q["a"][0] + q["b"][0]) / 2, (q["a"][1] + q["b"][1]) / 2))]
    band = [q for q in band if q not in low]
    out = [{"name": "flank_band", "coll": "Hull", "mat": light, "kind": "wall_side", "quads": band, "z0": zk, "h": H},
           {"name": "flank_plank", "coll": "Hull", "mat": light, "kind": "wall_side", "quads": low, "z0": zk, "h": 0.0},
           {"name": "flank_south", "coll": "Hull", "mat": south_mat, "kind": "wall_side", "quads": south, "z0": zk, "h": H}]
    # Schraege: Vierecke von der Knickkante (aussen, zk) zum naechsten Punkt des Kielrings (innen, KEEL_Z)
    verts, faces = [], []
    for a, b in zip(ring, ring[1:]):
        pa = inner.exterior.interpolate(inner.exterior.project(Point(a)))
        pb = inner.exterior.interpolate(inner.exterior.project(Point(b)))
        i = len(verts)
        verts += [(a[0], a[1], zk), (b[0], b[1], zk), (pb.x, pb.y, KEEL_Z), (pa.x, pa.y, KEEL_Z)]
        faces.append((i, i + 3, i + 2, i + 1))
    from bm_spec import mesh as _mesh
    out.append({"name": "flank_slope", "coll": "Hull", "kind": "parts", "parts": [_mesh(verts, faces, main)]})
    out.append({"name": "keel", "coll": "Hull", "mat": main, "kind": "under", "z": KEEL_Z,
                "tris": [[t[0], t[2], t[1]] for t in tri(inner.simplify(0.05))]})
    # Wolken
    ref = sc.ref
    img = ref.img.astype(np.int16)
    cm = ((np.abs(img - np.array(CLOUD_W)).sum(-1) <= 14) | (np.abs(img - np.array(CLOUD_S)).sum(-1) <= 14)).astype(np.uint8)
    cm = cv2.morphologyEx(cm, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cm, connectivity=8)
    mats = (ctx.color("air_cloud", CLOUD_W), ctx.color("air_cloud_shadow", CLOUD_S))
    parts = []
    import random
    rnd = random.Random(7)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 0.25 * ref.ppu * ref.ppu:
            continue
        x0, y1 = ref.p2w(st[i, cv2.CC_STAT_LEFT], st[i, cv2.CC_STAT_TOP])
        x1, y0 = ref.p2w(st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT])
        w, h = x1 - x0, y1 - y0
        cy = (y0 + y1) / 2
        under = outer.buffer(1.0).contains(Point((x0 + x1) / 2, cy))
        cz = (KEEL_Z - 2.0 if under else -1.5) + rnd.uniform(-1.5, 1.5)
        nb = 2 if w < 1.5 else (3 if w < 3 else 4)
        for j in range(nb):
            fx = x0 + w * (j + 0.5) / nb
            r = max(0.3, w / nb * 0.75)
            parts.append(blob(fx, cy + rnd.uniform(-0.2, 0.2), cz + rnd.uniform(0, 0.3) * (1 if j % 2 else -1),
                              r, max(0.3, h * 0.6), r * 0.62, mats, seed=i * 10 + j, seg=12, rings=7))
    out.append({"name": "clouds", "coll": "Sky", "kind": "parts", "parts": parts})
    return out
