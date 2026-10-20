# bm_scene.py: Szene einer Karte fuer Blender (out/<karte>/scene.json + Texturen).
#
# Aufbau (alles in AU-Einheiten, z = Hoehe):
#   floor/<raum>     Boden je Raum auf z = 0 (Requisiten-Loecher gefuellt, Wandmassen bleiben Loecher)
#   ceiling/<raum>   Decke je Raum auf z = H
#   wall/<raum>      senkrechte Wandflaechen entlang des Grundrissrands, Normale in den Raum
#   cap              Oberseite der Wandmasse (Schiffsumriss minus Boeden) auf z = H, Huellenfarbe
#   hullside         Aussenhaut entlang des Schiffsumrisses
# Wandflaechen tragen ihre Ausrichtung: "north" = Wand im Norden des Raums (Flaeche zeigt nach Sueden), nur
# diese zeichnet Among Us als Band; alle anderen sind "side".
#
# Materialien: {name: {"image": datei, "uv": "bbox"|"world"|"edge", ...}} oder {"color": [r,g,b]}.
# Texturen der Raeume kommen aus rooms/<karte>/<raum>.py (Nachbau); ohne Datei bleibt der Raum auf dem
# Ausschnitt des Kartenfotos ("ref"), damit die Kette schon laeuft.

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, LinearRing
from shapely.ops import unary_union

from bm_ref import Ref, H_WALL, ROOT
from bm_plan import Plan, RES

RIM = [(16, 24, 24, 0.03), (46, 49, 49, 0.09), (16, 24, 24, 0.03)]     # Wandkontur von innen nach aussen (Farbe, Breite)
NORTH_NY = -0.15                                                       # Flaechennormale mit Suedanteil: Among Us zeichnet die Front

def _mira_sky(img):
    """Wolken auf Mira: violettgrau (Blau etwas ueber Rot, Rot etwas ueber Gruen); Mira-Boeden sind warmweiss."""
    r, g, b = img[..., 0].astype(int), img[..., 1].astype(int), img[..., 2].astype(int)
    return (b - r >= 1) & (b - r <= 25) & (r - g >= 2) & (r - g <= 15)


def _polus_sky(img):
    """Polus: Klippengrau (59,58,60), Bergkulisse (violettgraue Schichten) und schwarzer Himmel gelten als offen."""
    a = img.astype(int)
    out = a.sum(-1) / 3 < 30
    for c in ((59, 58, 60), (67, 55, 86), (40, 35, 79), (43, 37, 65), (96, 63, 114), (68, 48, 98)):
        out |= np.abs(a - np.array(c)).sum(-1) <= 6
    return out


def _air_sky(img):
    """Airship: Rumpfflanke (150,40,56)/(175,65,72) und Wolken (weiss, blaugrauer Schatten) sind kein Boden."""
    a = img.astype(int)
    out = np.zeros(a.shape[:2], bool)
    for c in ((150, 40, 56), (175, 65, 72), (99, 39, 52), (242, 248, 250), (239, 247, 250), (170, 207, 234), (173, 207, 231)):
        out |= np.abs(a - np.array(c)).sum(-1) <= 8
    return out


def _fungle_sky(img):
    """Fungle: Meer (243,187,84) mit hellem Uferverlauf, Nachthimmel (42,45,62), Leere (57,26,54) sind kein Boden."""
    a = img.astype(int)
    out = np.zeros(a.shape[:2], bool)
    for c, t in (((243, 187, 84), 14), ((42, 45, 62), 10), ((57, 26, 54), 10)):
        out |= np.abs(a - np.array(c)).sum(-1) <= t
    return out


MAPCFG = {
    "skeld": {"hull": (61, 74, 74), "space": (41, 23, 56), "k": 0.59, "ship": "atlas", "clean": False,
              "rim": [(16, 24, 24, 0.03), (46, 49, 49, 0.09), (16, 24, 24, 0.03)]},
    "polus": {"hull": (60, 74, 74), "ceiling": (128, 134, 140), "space": (41, 23, 56), "k": 0.50, "ship": "buffer", "sky": _polus_sky,
              "rim": [(19, 26, 26, 0.025), (46, 49, 49, 0.065), (19, 26, 26, 0.025)],
              "rest": "Outside", "grow": 1.0, "ship_holes": True, "hull_hole": 0.5,
              # Generatorhof von Electrical liegt im Freien (Zone reicht ueber ihn)
              "zones_add": [# Fehlerrunde 19.10.: Innenflure ohne eigene Zone galten als Gelaende (Himmel, Felswaende)
                            # Roehre Electrical - O2 zwischen den TubeWalls x 4,62 / 6,23
                            ("ElecTube", [(4.55, -13.75), (6.30, -13.75), (6.30, -18.0), (4.55, -18.0)]),
                            # Office-Flur (blau gestreift) und Vorraum zur LeftDoor gehoeren zum Buerogebaeude
                            ("OfficeHall", [(15.95, -18.70), (24.55, -18.70), (24.55, -20.05), (19.48, -20.05), (19.48, -23.05),
                                        (17.40, -23.05), (17.40, -20.05), (15.95, -20.05)]),
                            # Laborbalkon mit Teleskop: offen (Gelaender), ohne Decke
                            ("Balcony", [(32.30, -6.02), (32.60, -5.30), (33.05, -4.95), (35.15, -4.95), (35.50, -5.25),
                                         (35.70, -5.70), (35.70, -6.02)]),
                            ("Outside", [(7.15, -10.45), (11.4, -10.45), (11.4, -13.9), (7.15, -13.9)]),
                            # Gelaende neben der unteren Roehre (lila, Weg vom Office-Ostausgang): lag in der Zone RightTube
                            # (Rechteck 25,73..33,58 / -26,46..-19,46) und bekam Roehrenboden und Decke (#306)
                            ("Outside", [(25.70, -19.30), (33.75, -19.30), (33.75, -20.33), (27.25, -20.35), (26.93, -20.66),
                                         (26.93, -24.05), (26.75, -24.28), (25.70, -24.25)]),
                            # Hof vor dem Labor (Bohrer, Zaun) liegt im Freien
                            ("Outside", [(24.6, -4.8), (28.35, -4.8), (28.35, -8.25), (24.6, -8.25)]),
                            # Probenraum (Specimen) hat keine eigene Zone
                            # (mit der Nordostecke bis zur Roehrenwand, dort stand man sonst unter freiem Himmel, #269)
                            # Achteck nach den Schatten-Collidern (RightPod/Shadows*); das Rechteck vorher schloss die
                            # Nordwestecke draussen mit ein, dort fehlte die Diagonalwand (#270/#271)
                            ("Specimen", [(33.62, -19.29), (34.94, -17.98), (38.14, -17.98), (38.45, -18.3), (38.75, -19.0),
                                          (39.45, -19.25), (39.45, -21.27), (38.11, -22.65), (34.98, -22.65), (33.62, -21.26)])]},
    "airship": {"hull": (82, 36, 38), "ceiling": (150, 112, 92), "world": (96, 120, 168), "space": (41, 23, 56), "k": 0.54, "ship": "map", "sky": _air_sky,
                "rim": [(49, 24, 16, 0.03), (112, 69, 52, 0.03), (5, 2, 3, 0.03)],
                "seeds": [(10.0, 15.0)]},                                   # Meeting Room nur ueber die Leiter
    "fungle": {"hull": None, "world": (42, 45, 62), "space": (243, 187, 84), "k": 0.95, "ship": "buffer", "sky": _fungle_sky, "smooth_tex": True, "cap_art": True, "rim_strips": False,
               "rim": [(49, 9, 21, 0.03), (52, 10, 24, 0.04), (49, 9, 21, 0.03)],
               "rest": "Outside", "grow": 0.3, "ship_holes": True, "hull_hole": 0.5,
               # Hochebenen nur ueber Leitern: Highland, Ledge (Mining Pit), Kuppe, Comms-Plateau
               "seeds": [(14.0, 3.5), (21.3, 13.5)]},
    # Atlas zeichnet mit K 0,55 (museum_art): Wandfront 0,95 -> Wandhoehe 1,73
    "museum": {"no_open": True, "hull": (58, 64, 76), "space": (16, 19, 26), "ceiling": (186, 188, 192), "world": (24, 28, 44), "k": 0.55, "H": 1.73, "ship": "hull_mask", "smooth_tex": True,
               "cap_art": True, "north_stop": 0.3, "rim": [(16, 17, 20, 0.03)]},
    "park": {"hull": (40, 30, 48), "hull_more": [(46, 40, 52)], "space": (14, 13, 25), "world": (26, 22, 52), "k": 0.55, "H": 1.73,
             "ship": "hull_mask", "smooth_tex": True, "cap_art": True, "north_stop": 0.3, "sky_all": True,
             "rim": [(16, 17, 20, 0.03)]},
    "wald": {"hull": (45, 86, 54), "space": (45, 86, 54), "world": (30, 44, 70), "k": 0.55, "H": 1.73, "ship": "hull_mask", "smooth_tex": True,
             "cap_art": True, "north_stop": 0.3, "sky_all": True, "rim": [(16, 17, 20, 0.03)]},
    "train": {"no_open": True, "hull": (40, 32, 30), "space": (16, 19, 28), "ceiling": (126, 116, 104), "world": (18, 22, 36), "k": 0.55, "H": 1.73, "ship": "hull_mask", "smooth_tex": True,
              "cap_art": True, "north_stop": 0.3, "rim": [(16, 17, 20, 0.03)]},
    # Unterdeck der Zugkarte (Gepaeckraum, Kueche, Telegraf, Dynamo) haengt nur ueber Teleport-Treppen am Zug und liegt
    # im Bild ohne Wandmasse ringsum: rooms/train/_map.adjust() haengt es aus map.json an (keine seeds).
    "mira": {"hull": None, "world": (74, 62, 96), "ceiling": (200, 204, 210), "space": (41, 23, 56), "k": 0.53, "ship": "buffer", "sky": _mira_sky,
             "rim": [(6, 5, 0, 0.02), (42, 42, 53, 0.11), (0, 0, 0, 0.02)],
             # Startplattform unter der Rakete (Rakete reicht bis zum Rand, die Flaeche ist nicht eingeschlossen)
             "floor_add": [[(-11.55, 0.15), (-0.35, 0.15), (-0.35, 8.80), (-11.55, 8.80)]]},
}
import bm_ext                                                                       # noqa: E402
MAPCFG.update(bm_ext.scenes())                                                      # Karten optionaler Erweiterungen


def tri(poly):
    """Polygon (mit Loechern) -> Dreiecke als Liste von 3-Tupeln (x, y)."""
    out = []
    for g in getattr(poly, "geoms", [poly]):
        if g.is_empty or g.area < 1e-6:
            continue
        t = shapely.constrained_delaunay_triangles(g)
        for tr in getattr(t, "geoms", [t]):
            cs = list(tr.exterior.coords)[:3]
            # gegen den Uhrzeigersinn (Normale +z)
            (x0, y0), (x1, y1), (x2, y2) = cs
            if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0:
                cs = [cs[0], cs[2], cs[1]]
            out.append([list(map(lambda v: round(v, 4), p)) for p in cs])
    return out


def ship_silhouette(ref, space, tol=30):
    img = ref.img.astype(np.int16)
    m = (np.abs(img - np.array(space, np.int16)).sum(-1) > tol).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))        # Sterne weg
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=4)
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == big).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cs, key=cv2.contourArea)
    pts = [ref.p2w(p[0][0], p[0][1]) for p in c]
    return Polygon(pts).buffer(0).simplify(0.04)


class Scene:
    def __init__(self, key):
        self.key = key
        if key not in MAPCFG:
            bm_ext.unknown(key, MAPCFG)
        self.cfg = MAPCFG[key]
        self.rooms_dir = bm_ext.rooms_dir(key)                              # rooms/<karte>/ oder Erweiterung
        self.ref = Ref(key)
        self.plan = Plan(self.ref, hull_color=self.cfg["hull"], extra_seeds=self.cfg.get("seeds", ()))
        global RIM
        RIM = self.cfg.get("rim", RIM)
        self.out = ROOT / "out" / key
        (self.out / "tex").mkdir(parents=True, exist_ok=True)
        self.H = float(self.cfg.get("H", H_WALL))
        import bm_tex
        bm_tex.SMOOTH = bool(self.cfg.get("smooth_tex"))

    # ------------------------------------------------------------------ Grundriss
    def _merge_splinters(self, rooms):
        """Raumsplitter dem umgebenden Raum geben. Zonen ueberlappen, die kleinere gewinnt; so landeten zwei Stuecke
        TinyHallway mitten in der Storage-Halle, mit 1,39 hoher Decke und Loechern in der 3,6 hohen (Meldungen
        18.10.). Splitter = abgetrenntes Teil (< 3 m2 und < 1/4 des Hauptteils), ringsum fast nur Boden (keine Wand
        dazwischen) und zum groessten Teil von genau einem anderen Raum umgeben."""
        for n in list(rooms):
            parts = sorted(getattr(rooms[n], "geoms", [rooms[n]]), key=lambda q: -q.area)
            if len(parts) < 2:
                continue
            keep = [parts[0]]
            for q in parts[1:]:
                ring = q.buffer(0.08).difference(q)
                on_floor = ring.intersection(self.floor).area
                if q.area > 3.0 or q.area > 0.25 * parts[0].area or on_floor < 0.6 * ring.area:
                    keep.append(q)
                    continue
                share = {m: rooms[m].intersection(ring).area for m in rooms if m != n}
                best = max(share, key=share.get) if share else None
                if best is None or share[best] < 0.5 * on_floor:
                    keep.append(q)
                    continue
                rooms[best] = unary_union([rooms[best], q]).buffer(0)
            rooms[n] = unary_union(keep).buffer(0)

    def build_plan(self):
        ref = self.ref
        if self.cfg.get("north_stop"):
            # eigene Karten: Bewegungskante liegt vor Nordwaenden um north_stop zurueck; Boden = Kante + Streifen
            from shapely.affinity import translate as _tr
            pw = self.plan.walk
            walk = unary_union([pw, _tr(pw, 0, self.cfg["north_stop"])]).buffer(0.02).buffer(-0.02)
        else:
            walk = self.grow_to_outline(self.plan.walk)
        hull = np.array(self.cfg["hull"] or (-999, -999, -999), np.int16)
        img = ref.img.astype(np.int16)
        keep_holes, filled = [], []
        polys = []
        geoms = list(getattr(walk, "geoms", [walk]))
        inner = [q.representative_point() for q in geoms if q.area > 1.0]     # Krumen hinter Requisiten zaehlen nicht
        hthr = self.cfg.get("hull_hole", 0.3)
        rooms = self.plan.rooms(rest_name=self.cfg.get("rest"), overrides=self.cfg.get("zones_add", ()))
        for g in geoms:
            holes = []
            for ring in g.interiors:
                hp = Polygon(ring)
                if any(hp.contains(p_) for p_ in inner):
                    holes.append(hp)                                         # Gebaeudegrundriss mit eigenem Boden
                    continue
                if self.cfg.get("rest"):
                    # Gelaendekarten: Wandmassen sind nicht huellenfarbig; was an zwei Raeume grenzt, ist Wand
                    near = [n for n, rg in rooms.items() if rg.distance(hp) < 0.3]
                    if len(near) >= 2:
                        holes.append(hp)
                        continue
                frac = self._fraction(hp, lambda px: (np.abs(px - hull).sum(-1) <= 6))
                (holes if frac > hthr else filled).append(hp)
            polys.append(Polygon(g.exterior, [h.exterior for h in holes]))
            keep_holes += holes
        self.floor = unary_union(polys + [Polygon(p_) for p_ in self.cfg.get("floor_add", [])]).buffer(0)
        # Mindestabstand Wand - Laufgrenze: Among Us laesst den Spieler bis auf die Kollisionslinie, und wo die
        # gezeichnete Wandkante kaum dahinter liegt, stand die Kamera in der Wand (Shields-Spitze am Vent, Meldungen
        # 18.10.). Duenne Waende zwischen zwei Laufbereichen bleiben ausgespart, sonst verschwaenden sie. Nur nach
        # Sueden, Osten, Westen: nach Norden (auch schraeg) liegen gezeichnete Fronten, deren Band ab der Bodenkante
        # abgetastet wird und sonst verrutschte.
        margin = float(self.cfg.get("wall_margin", 0.15))
        if margin > 0:
            from shapely.geometry import box as _box
            from shapely.ops import nearest_points
            pw = self.plan.walk
            grow = pw.buffer(margin, join_style=2)
            thin = grow.buffer(-margin, join_style=2).difference(pw).difference(self.floor).buffer(0)
            if not thin.is_empty and thin.area > 0.005:
                grow = grow.difference(thin.buffer(margin)).buffer(0)
            extra = grow.difference(self.floor).buffer(0)
            keep = []
            if not extra.is_empty:
                ex0, ey0, ex1, ey1 = extra.bounds
                st = 0.4
                edge = pw.boundary
                for ix in range(int(math.floor(ex0 / st)), int(math.ceil(ex1 / st))):
                    for iy in range(int(math.floor(ey0 / st)), int(math.ceil(ey1 / st))):
                        cell = extra.intersection(_box(ix * st, iy * st, (ix + 1) * st, (iy + 1) * st))
                        for q in getattr(cell, "geoms", [cell]):
                            if q.is_empty or q.area < 1e-6 or q.geom_type != "Polygon":
                                continue
                            c = q.representative_point()
                            p = nearest_points(edge, c)[0]
                            dx_, dy_ = c.x - p.x, c.y - p.y
                            if dy_ <= 0.5 * math.hypot(dx_, dy_):
                                keep.append(q)
            if keep:
                add = unary_union(keep).buffer(0)
                self.floor = unary_union([self.floor, add]).buffer(0.001).buffer(-0.001)
                keep_holes = [h.difference(add).buffer(0) for h in keep_holes if not h.difference(add).is_empty]
        # Kerben im Bodenrand mit gezeichneter Einrichtung statt Huellenfarbe (Tisch/Pult an der Wand: der Collider
        # umschliesst sie zusammen mit der Wand, der Grundriss baute dort einen raumhohen Wandblock; Security-L-Tisch,
        # Meldungen 18.10.) werden Boden, die Einrichtung davor bauen Raumdatei bzw. bm_objects.
        if self.cfg.get("fill_notches", True) and self.cfg.get("hull"):
            nw = 0.6
            notch = self.floor.buffer(nw, join_style=2).buffer(-nw, join_style=2).difference(self.floor)
            notch = notch.buffer(-0.02).buffer(0.02)
            fill = [q for q in getattr(notch, "geoms", [notch])
                    if not q.is_empty and 0.05 < q.area < 1.2 and self._fraction(q, lambda px: (np.abs(px - hull).sum(-1) <= 12)) < 0.1]
            if fill:
                add = unary_union([q.buffer(0.01) for q in fill])
                self.floor = unary_union([self.floor, add]).buffer(0)
                keep_holes = [h.difference(add).buffer(0) for h in keep_holes if not h.difference(add).is_empty]
                self.notches_filled = round(add.area, 2)
        # Restspalten unter 0,12 schliessen (Splitter zwischen aufgefuellten Stuecken standen als duenne Pfeiler)
        self.floor = self.floor.buffer(0.06, join_style=2).buffer(-0.06, join_style=2).buffer(0)
        self.props_fp = filled                                               # Grundflaechen gezeichneter Requisiten
        self.wall_holes = keep_holes                                         # Wandmassen (bleiben Loecher)
        # Raumteile mit den gefuellten Loechern ergaenzen (Loch -> Raum mit der laengsten gemeinsamen Kante)
        for hp in filled:
            best = max(rooms, key=lambda n: rooms[n].buffer(0.05).intersection(hp.exterior).length)
            rooms[best] = unary_union([rooms[best], hp]).buffer(0)
        rooms = {n: g.intersection(self.floor).buffer(0) for n, g in rooms.items()}
        rest = self.floor.difference(unary_union(list(rooms.values()))).buffer(0)      # angewachsener Rand
        # Den Rand nach naechstem Raum aufteilen (Raeume wachsen schrittweise hinein), nicht jedes zusammenhaengende
        # Stueck als Ganzes an einen Raum: ein Randstreifen um Storage bis vor Shields gehoerte sonst komplett
        # RightEngine und trug dessen beige Triebwerkswaende (Meldungen 18.10.)
        for d in (0.04, 0.08, 0.15, 0.25, 0.4, 0.6, 1.0):
            if rest.is_empty or rest.area < 1e-6:
                break
            grabbed = []
            for n in sorted(rooms):
                part = rest.intersection(rooms[n].buffer(d, join_style=2)).buffer(0)
                for q in grabbed:
                    part = part.difference(q).buffer(0)
                if part.is_empty or part.area < 1e-7:
                    continue
                rooms[n] = unary_union([rooms[n], part]).buffer(0)
                grabbed.append(part)
            if grabbed:
                rest = rest.difference(unary_union(grabbed)).buffer(0)
        for piece in getattr(rest, "geoms", [rest]):
            if piece.is_empty or piece.area < 1e-6:
                continue
            best = min(rooms, key=lambda n: (-rooms[n].buffer(0.03).intersection(piece).area, rooms[n].distance(piece)))
            rooms[best] = unary_union([rooms[best], piece]).buffer(0)
        self._merge_splinters(rooms)
        # 4 mm Ueberlappung: zwischen zwei Raumboeden blieben sonst Haarfugen, durch die man ins Leere sah
        rooms = {n: g.buffer(0.004, join_style=2).intersection(self.floor).buffer(0) for n, g in rooms.items()}
        self.rooms = rooms
        self.mapmod = None
        mf = self.rooms_dir / "_map.py"
        if mf.exists():                                                      # kartenweite Eingriffe (Gelaende usw.)
            import importlib.util
            sp = importlib.util.spec_from_file_location(f"map_{self.key}", mf)
            self.mapmod = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(self.mapmod)
            if hasattr(self.mapmod, "adjust"):
                self.mapmod.adjust(self)
        self._pits()
        self._drop_slivers()
        if self.cfg.get("ship") == "buffer":
            Wr = sum(r_[3] for r_ in RIM) + 0.005
            ship = self.ship_of(self.floor)
            opens = [LineString([e["a"], e["b"]]).buffer(Wr + 0.02, cap_style=2) for e in self.wall_edges() if e["kind"] == "open"]
            if opens:
                ship = ship.difference(unary_union(opens).difference(self.floor)).buffer(0)
            self.ship = ship
        elif self.cfg.get("ship") == "hull_mask":
            # Wandmassen = Flaechen in der gezeichneten Wandkronen-Farbe; Rest ausserhalb des Bodens = Gelaende auf 0
            img = ref.img.astype(np.int16)
            m = np.zeros(img.shape[:2], bool)
            for hc in [self.cfg["hull"]] + list(self.cfg.get("hull_more", [])):
                m |= np.abs(img - np.array(hc, np.int16)).sum(-1) <= self.cfg.get("hull_tol", 10)
            m = cv2.resize(m.astype(np.float32), (self.plan.gw, self.plan.gh), interpolation=cv2.INTER_AREA) > 0.3
            m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            self._hullmask = m
            hp = self.plan._polys(m).buffer(0)
            Wr = sum(r_[3] for r_ in RIM) + 0.005
            self.ship = unary_union([self.floor.buffer(Wr, join_style=2, mitre_limit=3.0), hp]).buffer(0)
        elif self.mapmod is not None and hasattr(self.mapmod, "ship"):
            self.ship = self.mapmod.ship(self)                               # kartenweiser Schiffsumriss
        else:
            self.ship = ship_silhouette(ref, self.cfg["space"])
        self.cap = self.ship.difference(self.floor).buffer(0)

    def _drop_slivers(self, amin=0.05):
        """Entartete Loecher und Splitter (Flaeche < amin) aus Boden und Raumpolygonen entfernen. Skeld Weapons hatte
        ein Loch mit Flaeche 0 (drei fast kollineare Punkte): daraus wurden drei Mini-Wandkanten in voller Hoehe und
        ein Schlitz in der Decke, aus der Einfahrt eine duenne wandfarbene Saeule (User 19.10.)."""
        def clean(g):
            g = g.buffer(0)
            out = []
            for pg in getattr(g, "geoms", [g]):
                if pg.is_empty or pg.geom_type != "Polygon" or pg.area < amin:
                    continue
                out.append(Polygon(pg.exterior, [h for h in pg.interiors if Polygon(h).area >= amin]))
            if not out:
                return Polygon()
            return out[0] if len(out) == 1 else MultiPolygon(out)
        def holes_only(g):
            out = []
            for pg in getattr(g, "geoms", [g]):
                if pg.is_empty or pg.geom_type != "Polygon":
                    continue
                out.append(Polygon(pg.exterior, [h for h in pg.interiors if Polygon(h).area >= amin]))
            if not out:
                return Polygon()
            return out[0] if len(out) == 1 else MultiPolygon(out)
        self.floor = clean(self.floor)
        names = list(self.rooms)
        for n in names:
            self.rooms[n] = holes_only(self.rooms[n].buffer(0).intersection(self.floor).buffer(0))
        # Raumsplitter < amin dem Nachbarraum mit der laengsten gemeinsamen Grenze geben; Bodenreste ohne Raum ebenso
        for n in names:
            g = self.rooms[n]
            keep = []
            for pg in getattr(g, "geoms", [g]):
                if pg.geom_type != "Polygon" or pg.is_empty:
                    continue
                if pg.area >= amin:
                    keep.append(pg)
                    continue
                best = max((m for m in names if m != n), key=lambda m: self.rooms[m].buffer(0.01).intersection(pg.boundary).length)
                self.rooms[best] = unary_union([self.rooms[best], pg]).buffer(0)
            self.rooms[n] = unary_union(keep).buffer(0) if keep else Polygon()
        rest = self.floor.difference(unary_union(list(self.rooms.values()))).buffer(0)
        for piece in getattr(rest, "geoms", [rest]):
            if piece.is_empty or piece.area < 1e-6 or piece.geom_type != "Polygon":
                continue
            best = min(self.rooms, key=lambda m: (-self.rooms[m].buffer(0.03).intersection(piece).area, self.rooms[m].distance(piece)))
            self.rooms[best] = unary_union([self.rooms[best], piece]).buffer(0)
        # zuletzt nur noch Loecher filtern (keine Vereinigung mehr, die neue Nullflaechen-Loecher erzeugen koennte)
        for n in names:
            self.rooms[n] = holes_only(self.rooms[n])
        self.rooms = {n: g for n, g in self.rooms.items() if not g.is_empty}

    def spec_of(self, name):
        """Raumdatei rooms/<karte>/<raum>.py (einmal geladen) oder None."""
        cache = self.__dict__.setdefault("_specs", {})
        if name not in cache:
            import importlib.util
            sf = self.rooms_dir / f"{name}.py"
            mod = None
            if sf.exists():
                sp = importlib.util.spec_from_file_location(f"room_{self.key}_{name}", sf)
                mod = importlib.util.module_from_spec(sp)
                sp.loader.exec_module(mod)
            cache[name] = mod
        return cache[name]

    def _pits(self):
        """Gruben aus den Raumdateien (PITS): tiefer liegende Bodenteile, z. B. Maschinendeck unter einer Plattform.
        poly = Grundriss (Oberkante, Weltlage); add=True nimmt ausserhalb des Bodens liegende Teile dazu."""
        self.pits = []
        for name in list(self.rooms):
            sp = self.spec_of(name)
            for pd in (getattr(sp, "PITS", None) or []) if sp else []:
                poly = Polygon(pd["poly"]).buffer(0)
                if pd.get("add"):
                    newp = poly.difference(self.floor).buffer(0)
                    fl = unary_union([self.floor, newp]).buffer(0)
                    # Restinseln zwischen Grube und Plattform (Schnittreste < 0,5 m2) gehoeren zur Grube
                    keep = []
                    for fg in getattr(fl, "geoms", [fl]):
                        holes = []
                        for h in fg.interiors:
                            hp = Polygon(h)
                            if hp.area < 0.5 and hp.distance(newp) < 0.05:
                                newp = unary_union([newp, hp]).buffer(0)
                            else:
                                holes.append(h)
                        keep.append(Polygon(fg.exterior, holes))
                    self.floor = unary_union(keep).buffer(0)
                    for n in self.rooms:
                        if n != name:
                            self.rooms[n] = self.rooms[n].difference(newp).buffer(0)
                    self.rooms[name] = unary_union([self.rooms[name], newp]).buffer(0)
                    if pd.get("cut") == "floor":                            # nur der neu dazugenommene Teil
                        poly = newp
                else:
                    poly = poly.intersection(self.floor).buffer(0)
                if poly.area > 1e-3:
                    self.pits.append(dict(pd, room=name, geom=poly))
                    # Schlitze im Boden entlang der Grubenkante (Gelaender-Collider) schliessen, sonst stehen dort
                    # raumhohe Wandstreifen
                    fl = self.floor
                    slit = fl.buffer(0.12, join_style=2).buffer(-0.12, join_style=2).difference(fl)
                    slit = slit.intersection(Polygon(pd["poly"]).buffer(0.25)).buffer(0)
                    if not slit.is_empty and slit.area > 1e-4:
                        self.floor = unary_union([fl, slit]).buffer(0)
                        self.rooms[name] = unary_union([self.rooms[name], slit]).buffer(0)

    def ship_of(self, floor):
        """Wandmasse fuer "buffer"-Karten: Boden + Konturbreite, Spalten zwischen nahen Boeden geschlossen."""
        Wr = sum(r_[3] for r_ in RIM) + 0.005
        ship = floor.buffer(Wr, join_style=2, mitre_limit=3.0).buffer(0)
        if self.cfg.get("ship_holes") and getattr(self, "wall_holes", None):
            # Gelaendekarten: Wandmassen = die als Wand erkannten Loecher im Laufbereich (nichts dazuerfinden)
            ship = unary_union([ship] + [h.buffer(0.01) for h in self.wall_holes]).buffer(0)
        elif self.cfg.get("ship_close"):
            c = self.cfg["ship_close"]
            ship = ship.buffer(c, join_style=2, mitre_limit=3.0).buffer(-c, join_style=2, mitre_limit=3.0).buffer(0)
        return ship

    def _raster(self, geom):
        pl = self.plan
        m = np.zeros((pl.gh, pl.gw), np.uint8)
        for g in getattr(geom, "geoms", [geom]):
            if g.is_empty:
                continue
            cv2.fillPoly(m, [pl._px(list(g.exterior.coords))], 1)
            for h in g.interiors:
                cv2.fillPoly(m, [pl._px(list(h.coords))], 0)
        return m

    def grow_to_outline(self, floor, iters=None):
        """Boden bis an die gezeichnete Kontur ziehen: die Collider sitzen oft 0,05-0,25 vor der Zeichenkante.
        Waechst nur ueber Pixel, die weder Kontur (dunkel) noch Huelle sind, und nie in die Frontbaender."""
        ref, pl = self.ref, self.plan
        img = ref.img.astype(np.int16)
        hull = np.array(self.cfg["hull"] or (-999, -999, -999), np.int16)
        space = np.array(self.cfg["space"], np.int16)
        stop = (img.sum(-1) / 3 < 34) | (np.abs(img - hull).sum(-1) <= 6) | (np.abs(img - space).sum(-1) <= 30)
        if self.cfg.get("sky"):
            stop |= self.cfg["sky"](img)
        stop = stop.astype(np.uint8)
        # flaechig verkleinern: eine 2 px duenne Konturlinie darf beim Umrechnen auf das Planraster nicht verschwinden
        stop = cv2.resize(stop.astype(np.float32), (int(round(ref.W * RES / ref.ppu)), int(round(ref.H * RES / ref.ppu))),
                          interpolation=cv2.INTER_AREA)
        stop = (stop > 0.15).astype(np.uint8)
        g = np.ones((pl.gh, pl.gw), np.uint8)
        h, w = min(g.shape[0], stop.shape[0]), min(g.shape[1], stop.shape[1])
        g[:h, :w] = stop[:h, :w]
        forb = np.zeros_like(g)
        B = self.cfg["k"] * self.H + sum(r[3] for r in RIM) + 0.08          # Front + Kontur + Rand
        for e in self.wall_edges(floor):
            if e["n"][1] < NORTH_NY:
                (ax, ay), (bx, by) = e["a"], e["b"]
                cv2.fillPoly(forb, [pl._px([(ax, ay), (bx, by), (bx, by + B), (ax, ay + B)])], 1)
        if iters is None:
            iters = int(round(self.cfg.get("grow", 15.0) * RES))
        m = self._raster(floor)
        allow = ((g == 0) & (forb == 0)).astype(np.uint8)
        k = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        for _ in range(iters):
            n = m | (cv2.dilate(m, k) & allow)
            if (n == m).all():
                break
            m = n
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))   # Ritzen an gezeichneten Linien
        return pl._polys(m).buffer(0)

    def _fraction(self, poly, test):
        ref = self.ref
        x0, y0, x1, y1 = poly.bounds
        p0, p1 = ref.w2p(x0, y1), ref.w2p(x1, y0)
        a, b = int(p0[0]), int(p0[1])
        sub = ref.img[b:int(p1[1]) + 1, a:int(p1[0]) + 1].astype(np.int16)
        if sub.size == 0:
            return 0.0
        mask = np.zeros(sub.shape[:2], np.uint8)
        pts = np.array([[ref.w2p(*p)[0] - a, ref.w2p(*p)[1] - b] for p in poly.exterior.coords], np.int32)
        cv2.fillPoly(mask, [pts], 1)
        sel = mask > 0
        if not sel.any():
            return 0.0
        return float(test(sub[sel]).mean())

    # ------------------------------------------------------------------ Waende
    def wall_edges(self, floor=None):
        """Randkanten des Bodens: (a, b, raum, art, normale)."""
        out = []
        floor = self.floor if floor is None else floor
        for g in getattr(floor, "geoms", [floor]):
            for ring, is_hole in [(g.exterior, False)] + [(r, True) for r in g.interiors]:
                cs = list(ring.coords)
                ccw = ring.is_ccw
                inside_left = ccw != is_hole                                 # Aussenring CCW: Boden links
                for a, b in zip(cs, cs[1:]):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    L = math.hypot(dx, dy)
                    if L < 1e-4:
                        continue
                    nx, ny = (-dy / L, dx / L) if inside_left else (dy / L, -dx / L)
                    mid = ((a[0] + b[0]) / 2 + nx * 0.05, (a[1] + b[1]) / 2 + ny * 0.05)
                    room = self._room_at(mid) if hasattr(self, "rooms") else None
                    kind = "north" if ny < NORTH_NY else "side"
                    if self._open(a, b, L, nx, ny):
                        kind = "open"                                # Aussenkante ohne Wand (Plattform, Deck)
                    elif kind == "north" and L > 0.15 and not self._face_drawn(a, b, L):
                        kind = "side"                                # Among Us hat hier keine Front gezeichnet
                    out.append({"a": a, "b": b, "room": room, "kind": kind, "n": (nx, ny), "len": L})
        return out

    def _open(self, a, b, L, nx, ny):
        """Liegt hinter dieser Kante Himmel/Weltraum statt einer gezeichneten Wand? (offene Plattformkante)"""
        mm = getattr(self, "mapmod", None)
        if mm is not None and hasattr(mm, "open_edge"):
            r_ = mm.open_edge(self, a, b, nx, ny)
            if r_ is not None:
                return r_
        if self.cfg.get("no_open"):                                          # reine Innenkarte: jede Kante ist Wand
            return False
        hm = getattr(self, "_hullmask", None)
        if hm is not None:                                                   # Wand nur vor Wandmasse
            hits = 0
            d0 = self.cfg["k"] * self.H if ny < NORTH_NY else 0.0           # Nordwand: hinter der gezeichneten Front
            ds = [0.12, 0.2, 0.3] + ([d0 * 0.5, d0 + 0.12, d0 + 0.3] if d0 else [])  # hinter Kontur/Wandkrone/Front
            for f in (0.25, 0.5, 0.75):
                for d in ds:
                    c, r = self.plan._p((a[0] + (b[0] - a[0]) * f - nx * d, a[1] + (b[1] - a[1]) * f - ny * d))
                    if 0 <= r < hm.shape[0] and 0 <= c < hm.shape[1] and hm[r, c]:
                        hits += 1
                        break
            return hits < 2
        if not self.cfg.get("sky") and self.cfg.get("ship") != "buffer":
            return False
        ref = self.ref
        space = np.array(self.cfg["space"])
        n_sky = n = 0
        for f in np.linspace(0.15, 0.85, 6):
            x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            for d in (0.10, 0.18, 0.26):
                px, py = ref.w2p(x - nx * d, y - ny * d)
                if not (0 <= int(px) < ref.W and 0 <= int(py) < ref.H):
                    continue
                c = ref.img[int(py), int(px)].astype(int)
                sky = np.abs(c - space).sum() <= 30
                if self.cfg.get("sky"):
                    sky = sky or bool(self.cfg["sky"](c[None, None, :])[0, 0])
                n_sky += sky
                n += 1
        return n > 0 and n_sky / n > 0.6

    def _face_drawn(self, a, b, L):
        """Zeigt die Zeichnung ueber dieser Suedwand eine Front, oder nur Huelle/Kontur?"""
        e = {"a": a, "b": b, "len": L}
        st = self.band_strip(e, self.cfg["k"] * self.H * 0.8, self.ref.ppu).astype(int)
        hull = np.array(self.cfg["hull"] or (-999, -999, -999))
        space = np.array(self.cfg["space"])
        dark = (st.sum(-1) / 3 < 50) | (np.abs(st - hull).sum(-1) <= 10) | (np.abs(st - space).sum(-1) <= 30)
        return dark.mean() < 0.6

    def _room_at(self, p):
        from shapely.geometry import Point
        pt = Point(p)
        best, bd = None, 1e9
        for n, g in self.rooms.items():
            d = g.distance(pt)
            if d < bd:
                best, bd = n, d
        return best


    def rim_strips(self):
        """Konturstreifen aussen entlang jeder Bodenkante, Gehrung an den Ecken: [{pts, room, kind}]."""
        W = sum(r[3] for r in RIM)
        out = []
        for g in getattr(self.floor, "geoms", [self.floor]):
            for ring, is_hole in [(g.exterior, False)] + [(r, True) for r in g.interiors]:
                cs = list(ring.coords)[:-1]
                if len(cs) < 3:
                    continue
                inside_left = ring.is_ccw != is_hole
                nrm = []
                for i in range(len(cs)):
                    a, b = cs[i], cs[(i + 1) % len(cs)]
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    L = math.hypot(dx, dy) or 1e-9
                    nx, ny = (-dy / L, dx / L) if inside_left else (dy / L, -dx / L)
                    nrm.append((nx, ny))                                     # nach innen
                off = []
                for i in range(len(cs)):
                    o1 = (-nrm[i - 1][0], -nrm[i - 1][1])
                    o2 = (-nrm[i][0], -nrm[i][1])
                    mx, my = o1[0] + o2[0], o1[1] + o2[1]
                    ml = math.hypot(mx, my)
                    if ml < 1e-6:
                        mx, my, ml = o2[0], o2[1], 1.0
                    mx, my = mx / ml, my / ml
                    d = W / max(0.35, mx * o2[0] + my * o2[1])
                    off.append((cs[i][0] + mx * d, cs[i][1] + my * d))
                for i in range(len(cs)):
                    j = (i + 1) % len(cs)
                    a, b = cs[i], cs[j]
                    if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-4:
                        continue
                    nx, ny = nrm[i]
                    mid = ((a[0] + b[0]) / 2 + nx * 0.05, (a[1] + b[1]) / 2 + ny * 0.05)
                    if self._open(a, b, math.hypot(b[0] - a[0], b[1] - a[1]), nx, ny):
                        continue
                    out.append({"pts": [a, b, off[j], off[i]], "room": self._room_at(mid),
                                "kind": "north" if ny < NORTH_NY else "side"})
        return out

    # ------------------------------------------------------------------ Texturen (Stufe "ref": Ausschnitte)
    def solid(self, name, rgb):
        from PIL import Image
        f = self.out / "tex" / f"{name}.png"
        Image.new("RGB", (4, 4), tuple(int(v) for v in rgb)).save(f)
        self.mats[name] = {"image": f.name, "color": list(rgb)}
        return name

    def band_strip(self, e, B, ppu):
        """Gezeichnetes Wandband ueber der Kante a-b (Among Us zeichnet es senkrecht nach Norden) als Bild."""
        ref = self.ref
        (ax, ay), (bx, by) = e["a"], e["b"]
        w = max(2, int(round(e["len"] * ppu)))
        h = max(2, int(round(B * ppu)))
        u = (np.arange(w) + 0.5) / w
        v = 1.0 - (np.arange(h) + 0.5) / h                                   # Zeile 0 = Oberkante
        X = ax + (bx - ax) * u[None, :] + 0 * v[:, None]
        Y = ay + (by - ay) * u[None, :] + B * v[:, None]
        px = ((X - ref.mn[0]) * ref.ppu - 0.5).astype(np.float32)
        py = ((ref.mx[1] - Y) * ref.ppu - 0.5).astype(np.float32)
        return cv2.remap(ref.img_base, px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    def plain_column(self, north, B):
        """Schlichteste Stelle der gezeichneten Nordwaende: Spalte, die sich zu ihren Nachbarn (+-0,1/0,2) am wenigsten
        unterscheidet (kein Geraet, kein Poster). Rueckgabe Wandfusspunkt (x, y)."""
        ref = self.ref
        best, bp = None, None
        for e in north:
            if e["len"] < 0.5:
                continue
            (ax, ay), (bx, by) = e["a"], e["b"]
            n = max(3, int(e["len"] / 0.1))
            for i in range(1, n):
                u = i / n
                x, y = ax + (bx - ax) * u, ay + (by - ay) * u

                def col(xx):
                    return np.array([ref.img_base[int(ref.w2p(xx, y + B * t)[1]), int(ref.w2p(xx, y + B * t)[0])] for t in np.linspace(0.05, 0.9, 24)], float)
                c0 = col(x)
                d = np.mean([np.abs(c0 - col(x + dx)).mean() for dx in (-0.2, -0.1, 0.1, 0.2)])
                if best is None or d < best:
                    best, bp = d, (x, y)
        return bp

    def band_inpaint(self, arr, e, B, holes, pal):
        """Gebaute Gegenstaende, die in der Zeichnung vor dem Wandband stehen, aus dem Band herausrechnen."""
        from shapely.geometry import Point
        from shapely.ops import unary_union
        hu = unary_union(holes)
        h, w = arr.shape[:2]
        (ax, ay), (bx, by) = e["a"], e["b"]
        m = np.zeros((h, w), np.uint8)
        for j in range(w):
            u = (j + 0.5) / w
            x, y0 = ax + (bx - ax) * u, ay + (by - ay) * u
            for i in range(h):
                if hu.contains(Point(x, y0 + B * (1 - (i + 0.5) / h))):
                    m[i, j] = 1
        if not m.any():
            return arr
        out = cv2.inpaint(arr, m, 5, cv2.INPAINT_TELEA)
        d = np.abs(out[:, :, None, :].astype(int) - pal[None, None, :, :]).sum(-1)
        return np.where(m[:, :, None] > 0, pal[d.argmin(-1)], out).astype(np.uint8)

    # ------------------------------------------------------------------ Licht (Raumwirkung, nicht im Original)
    # Among Us zeigt keine Decken und kein Licht. Fuer die Ich-Perspektive bekommt jeder Innenraum Deckenplatten und
    # Leuchten in einem Raster (Abstand LAMP_STEP, Rand LAMP_INSET), Aussenbereiche Mondlicht und Himmelsfarbe.
    LAMP_STEP = 2.6
    LAMP_INSET = 0.8

    def lintels(self, edges):
        """Sturz an Raumgrenzen (Durchgaenge) zwischen unterschiedlich hohen Innenraeumen: Wand von der Decke des
        niedrigen bis zur Decke des hohen Raums (sonst sieht man aus dem hohen Raum ins Leere)."""
        from shapely.geometry import Point
        groups = {}
        names = sorted(self.rooms)
        top = {n: self.room_z.get(n, 0.0) + self.room_h.get(n, self.H) for n in names}
        for r1 in names:
            if self.room_sky.get(r1):
                continue
            g1 = self.rooms[r1]
            for r2 in names:
                if r2 == r1 or self.room_sky.get(r2):
                    continue
                zr1, zr2 = self.room_z.get(r1, 0.0), self.room_z.get(r2, 0.0)
                other_level = abs(zr1 - zr2) > 0.3
                if other_level:
                    # andere Ebene (Airship Meeting Room ueber dem Gap Room): die gemeinsame Grundrisskante ist kein
                    # Durchgang, sondern eine Trennwand vom tieferen Boden bis zur hoeheren Decke; der hoeher liegende
                    # Raum baut sie (vorher: Sturz nur ab der niedrigen Decke, die Decke des Meeting Rooms hing frei)
                    if zr1 < zr2 or top[r2] > zr1 + 0.5:
                        continue       # tiefer liegender Raum reicht bis in diese Ebene (Leiterschacht): echte Oeffnung
                elif top[r1] <= top[r2] + 0.05:
                    continue
                g2 = self.rooms[r2]
                if g1.distance(g2) > 0.03:
                    continue
                if other_level:
                    # Trennwand zwischen Ebenen: der Rasterrand der Zonen ist gezackt (Airship Meeting Room:
                    # Faltwand aus 0,3-m-Paneelen) -> Kante des geglaetteten Raumumrisses, lueckenlos
                    shared = g1.simplify(0.3).boundary.intersection(g2.buffer(0.45))
                else:
                    shared = g1.boundary.intersection(g2.buffer(0.03))
                segs = []
                lines = [ln for ln in getattr(shared, "geoms", [shared]) if ln.geom_type == "LineString"]
                if other_level:
                    # Stuecke an beiden Enden um 0,6 verlaengern: die geglaettete Kante weicht bis 0,3 vom
                    # gezackten Rand ab, sonst blieb zwischen Trennwand und Aussenwand ein Himmelsschlitz
                    ext = []
                    for ln in lines:
                        cs = list(ln.coords)
                        if len(cs) < 2:
                            continue
                        (ax, ay), (bx, by) = cs[0], cs[1]
                        L0 = math.hypot(bx - ax, by - ay) or 1.0
                        cs[0] = (ax - (bx - ax) / L0 * 0.6, ay - (by - ay) / L0 * 0.6)
                        (ax, ay), (bx, by) = cs[-2], cs[-1]
                        L1 = math.hypot(bx - ax, by - ay) or 1.0
                        cs[-1] = (bx + (bx - ax) / L1 * 0.6, by + (by - ay) / L1 * 0.6)
                        ext.append(LineString(cs))
                    lines = ext
                for ln in lines:
                    cs = list(ln.coords)
                    segs += list(zip(cs, cs[1:]))
                z1 = zr1
                if other_level:
                    key = (r1, round(min(zr1, zr2) - z1, 3), round(max(top[r1], top[r2]) - z1, 3))
                else:
                    key = (r1, round(top[r2] - z1, 3), round(top[r1] - z1, 3))
                for a, b in segs:
                    L = math.hypot(b[0] - a[0], b[1] - a[1])
                    if L < 0.02:
                        continue
                    n = (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)
                    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                    if not g1.contains(Point(m[0] + n[0] * 0.03, m[1] + n[1] * 0.03)):
                        n = (-n[0], -n[1])
                    groups.setdefault(key, []).append({"a": a, "b": b, "n": n, "uv": [0, 0, L, key[2] - key[1]]})
        out = []
        for (r1, z0, h), qs in sorted(groups.items()):
            mat = getattr(self, "room_side_mat", {}).get(r1) or self.solid(f"lintel_{r1}", (70, 80, 84))
            out.append({"name": f"lintel_{r1}_{z0:.2f}", "coll": r1, "mat": mat, "kind": "wall_side", "quads": qs,
                        "z0": z0, "h": h})
        return out

    def pit_meshes(self, ctx, room, pi, pd):
        """Grubenboden in Tiefe d (Zeichnung um k*d nach Sueden versetzt, wie Among Us tiefere Flaechen zeichnet) und
        Seitenwaende von -d bis 0; Nordwaende (von der Plattform aus sichtbar) mit der gezeichneten Front."""
        import bm_tex
        ref, k = self.ref, self.cfg["k"]
        d = float(pd.get("d", 0.4))
        g = pd["geom"]
        x0, y0, x1, y1 = g.bounds
        # aus dem Foto: unter der Plattform liegt gezeichnete Maschinerie, in der sauberen Vorlage ist die Grube
        # transparent (Weltraumfarbe, sah in der Ich-Sicht wie ein Loch aus; Skeld Weapons/Shields 18.10.)
        img = ref.crop_full(x0, y0 - k * d, x1, y1 - k * d)
        nm = f"pit_{room}_{pi}"
        import bm_style
        from bm_spec import Ctx
        if bm_style.on(self):
            # gemessene Grundfarbe der gezeichneten Grube, Boden als Riffelmuster (keine Spieltextur)
            base = bm_style.median_rgb(img)
            nm = Ctx(self, room).tex(nm, bm_style.floor_image("grating", bm_style._sh(base, 1.2), seed=pi), uv="world", scale=[1.0, 1.0])
        else:
            img.save(self.out / "tex" / f"{nm}.png")
            self.mats[nm] = {"image": f"{nm}.png", "uv": "bbox", "bbox": [x0, y0, x1, y1]}
        out = [{"name": nm, "coll": room, "mat": nm, "kind": "floor", "z": -d, "tris": tri(g)}]
        wall = self.solid(nm + "_wall", pd.get("wall", (60, 70, 78)))
        north, other = [], []
        for pg in getattr(g, "geoms", [g]):
            for ring in [pg.exterior] + list(pg.interiors):
                pts = list(ring.coords)
                ccw = LinearRing(pts).is_ccw
                for a, b in zip(pts, pts[1:]):
                    L = math.hypot(b[0] - a[0], b[1] - a[1])
                    if L < 1e-4:
                        continue
                    lx, ly = -(b[1] - a[1]) / L, (b[0] - a[0]) / L            # links von a->b
                    inside_left = ccw == (ring is pg.exterior)
                    n = (lx, ly) if inside_left else (-lx, -ly)              # Normale in die Grube
                    q = {"a": a, "b": b, "n": n, "uv": [(a[0] - x0) / max(1e-6, x1 - x0), 0,
                                                       (b[0] - x0) / max(1e-6, x1 - x0), 1]}
                    (north if n[1] < -0.5 else other).append(q)
        if north:
            yn = max(max(q["a"][1], q["b"][1]) for q in north)
            face = ref.crop_full(x0, yn - k * d, x1, yn)
            if bm_style.on(self):
                fm = ctx.tex(nm + "_front", bm_style.wall_image("plates", bm_style.median_rgb(face), H=max(0.3, d), seed=pi),
                             uv="world", scale=[max(0.3, d), max(0.3, d)])
            else:
                fm = ctx.tex(nm + "_front", bm_tex.label_upscale(face, 2.0), uv="quad")
            out.append({"name": nm + "_n", "coll": room, "mat": fm, "kind": "wall_side", "quads": north, "z0": -d, "h": 0.0})
        if other:
            out.append({"name": nm + "_s", "coll": room, "mat": wall, "kind": "wall_side", "quads": other, "z0": -d,
                        "h": 0.0})
        return out

    def ceiling_material(self):
        from PIL import Image as _I, ImageDraw as _D
        base = tuple(self.cfg.get("ceiling", (122, 130, 136)))
        line = tuple(max(0, int(v * 0.72)) for v in base)
        n = 128
        im = _I.new("RGB", (n, n), base)
        d = _D.Draw(im)
        d.rectangle([0, 0, n - 1, 2], fill=line)
        d.rectangle([0, 0, 2, n - 1], fill=line)
        im.save(self.out / "tex" / "ceiling.png")
        self.mats["ceiling"] = {"image": "ceiling.png", "uv": "world", "scale": 1.0, "color": list(base)}

    def lighting(self):
        from shapely.geometry import Point
        from shapely.ops import polylabel
        lights = []
        for name, g in sorted(self.rooms.items()):
            if self.room_sky.get(name):
                continue
            z = self.room_z.get(name, 0.0) + self.room_h.get(name, self.H) - 0.01
            for part in getattr(g, "geoms", [g]):
                if part.area < 0.6:
                    continue
                inner = part.buffer(-self.LAMP_INSET)
                if inner.is_empty or inner.area < 0.05:
                    inner = part.buffer(-0.45)                            # Gaenge: naeher an die Wand
                pts = []
                if not inner.is_empty:
                    x0, y0, x1, y1 = inner.bounds
                    nx = max(1, int(math.ceil((x1 - x0) / self.LAMP_STEP)))
                    ny = max(1, int(math.ceil((y1 - y0) / self.LAMP_STEP)))
                    for i in range(nx):
                        for j in range(ny):
                            x = x0 + (x1 - x0) * (i + 0.5) / nx
                            y = y0 + (y1 - y0) * (j + 0.5) / ny
                            if inner.contains(Point(x, y)):
                                pts.append((x, y))
                if not pts:
                    c = polylabel(part, 0.05)
                    pts = [(c.x, c.y)]
                for x, y in pts:
                    lights.append({"pos": [round(x, 3), round(y, 3), round(z, 3)], "room": name})
        world = list(self.cfg.get("world", self.cfg.get("space", (41, 23, 56))))
        sun = self.cfg.get("sun")
        if sun is None and (self.cfg.get("sky_all") or any(self.room_sky.values())):
            sun = {"color": [190, 200, 255], "strength": 1.6, "rot": [52, 0, 35]}
        return {"lights": lights, "world": world, "sun": sun}

    def export(self):
        """Zwei Durchgaenge: erst alles bauen, dann die gemalten Abbilder der gebauten Moebel aus der Vorlage rechnen
        (bm_clean) und Boden/Waende aus der bereinigten Vorlage neu erzeugen."""
        import time
        doc = self._export()
        if self.cfg.get("clean", True) and not (ROOT / "atlasdata" / self.key / "floor.png").exists():
            import bm_clean
            from PIL import Image
            t0 = time.time()
            ref, k = self.ref, self.cfg["k"]
            parts = [q for m in doc["meshes"] if m.get("kind") == "parts" and not m["name"].startswith("objects_")
                     for q in m["parts"]]
            holes = bm_clean.holes_of(parts, k)
            shape = (ref.image.height, ref.image.width)
            mask = bm_clean._raster(ref, holes, shape) > 0
            # Stellen, die die Grundbild-Zusammensetzung (bm_base) schon von Einzelobjekten befreit hat, bleiben
            done = np.abs(np.asarray(ref.image).astype(np.int16) - ref.img_full.astype(np.int16)).sum(-1) > 12
            if done.any():
                done = cv2.dilate(done.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
                mask &= ~done
            lab = bm_clean.zones(self, k * self.H)
            log = {}
            img = bm_clean.inpaint(np.asarray(ref.image), mask, lab, log=log)
            ref.image = Image.fromarray(img)
            ref.img_base = img
            Image.fromarray(img).save(self.out / "clean.png")
            self.clean_stats = dict(log, holes=len(holes), seconds=round(time.time() - t0, 1))
            doc = self._export()
        return doc

    def _export(self):
        from PIL import Image
        self.build_plan()
        H, ref = self.H, self.ref
        self.mats, meshes = {}, []
        self.__dict__.pop("_styles", None)                                  # Stilkacheln je Exportdurchgang neu (bm_style)
        self.room_h = {}
        self.room_z = {}
        self.room_sky = {}
        k = self.cfg["k"]
        B = k * H
        edges = self.wall_edges()
        ppu = ref.ppu
        import importlib.util
        import bm_tex
        from bm_spec import Ctx, art_floor, side_from_column
        import bm_style
        proc = bm_style.on(self)                                             # keine Spieltexturen: alles prozedural
        for name, g in sorted(self.rooms.items()):
            spec = self.spec_of(name)
            ctx = Ctx(self, name)
            own = bool(spec and getattr(spec, "PROCEDURAL", False))          # Raumdatei zeichnet selbst (ohne Foto)
            sty = None
            if proc:
                north_e = [e for e in edges if e["room"] == name and e["kind"] == "north"]
                sty = bm_style.room_style(self, ctx, name, g, north_e, B)
            rpits = [pd for pd in getattr(self, "pits", []) if pd["room"] == name]
            pit_u = unary_union([pd["geom"] for pd in rpits]) if rpits else None
            HR = float(getattr(spec, "H")) if (spec and hasattr(spec, "H")) else getattr(self, "auto_h", {}).get(name, H)
            x0, y0, x1, y1 = g.bounds
            tris = tri(g)
            # Boden: Nachbau aus der Raumdatei, sonst Ausschnitt des Kartenfotos; grosse Flaechen (Gelaende) in Kacheln,
            # damit keine Textur ueber 2048 Pixel waechst
            TS = float(getattr(spec, "TILE", 0) or 0) if spec else 0.0
            tiles = []
            if TS and max(x1 - x0, y1 - y0) > TS:
                from shapely.geometry import box as _box
                for ix in range(int(math.floor(x0 / TS)), int(math.ceil(x1 / TS))):
                    for iy in range(int(math.floor(y0 / TS)), int(math.ceil(y1 / TS))):
                        piece = g.intersection(_box(ix * TS, iy * TS, (ix + 1) * TS, (iy + 1) * TS)).buffer(0)
                        if piece.area > 1e-4:
                            tiles.append((f"{name}_{ix}_{iy}", piece))
            else:
                tiles = [(name, g)]
            for tname, piece in tiles:
                ctx.poly = piece
                if spec and hasattr(spec, "floor") and (not proc or own):
                    fmat = spec.floor(ctx) if len(tiles) == 1 else spec.floor(ctx, tname)
                elif proc:
                    fmat = sty.floor
                else:
                    fh = [h for h in getattr(self, "floor_holes", []) if h.intersects(piece.buffer(0.3))]
                    fmat = art_floor(ctx, f"floor_{tname}", holes=fh)  # Zeichnung in Originalpalette
                fl = piece.difference(pit_u).buffer(0) if pit_u is not None else piece
                if not fl.is_empty:
                    meshes.append({"name": f"floor_{tname}", "coll": name, "mat": fmat, "kind": "floor", "tris": tri(fl),
                                   "z": 0.0})
            ctx.poly = g
            if not (spec and getattr(spec, "SKY", False)) and not self.cfg.get("sky_all"):   # Aussenbereiche ohne Decke
                meshes.append({"name": f"ceiling_{name}", "coll": name, "mat": "ceiling", "kind": "ceiling",
                               "tris": [[t[0], t[2], t[1]] for t in tris], "z": HR})
            # Nordwaende: eigenes Material je Kante aus der Raumdatei, sonst das gezeichnete Band, hochskaliert mit
            # Originalpalette, eine Zeile je Kante in einem Bild
            north = [e for e in edges if e["room"] == name and e["kind"] == "north"]
            art, custom = [], {}
            for e in north:
                m = spec.north(ctx, e) if spec and hasattr(spec, "north") and (not proc or own) else None
                if not m and proc:
                    m = sty.wall
                if m:
                    custom.setdefault(m, []).append(e)
                else:
                    art.append(e)
            full = bool(spec and (getattr(spec, "FULL_WALLS", False) or getattr(spec, "BAND_H", 0)))  # Waende bis zur Decke
            for m, es in custom.items():
                meshes.append({"name": f"wallN_{name}_{m}", "coll": name, "mat": m, "kind": "wall_north", "h": HR if full else H,
                               "quads": [{"a": e["a"], "b": e["b"], "n": e["n"], "uv": [0, 0, 1, 1]} for e in es]})
            strips = []
            BR = float(getattr(spec, "BAND_H", 0) or 0) if spec else 0.0    # hohe gezeichnete Wand (Gap Room)
            HB = HR if BR else H                                             # Band deckt die ganze Raumhoehe
            BB = BR or B
            if art:
                sx, sy = bm_tex.TPPU / ppu, bm_tex.TPPU * HB / (BB * ppu)
                for e in art:
                    arr = self.band_strip(e, BB, ppu)
                    pal = bm_tex.palette_of(Image.fromarray(arr))
                    bh = getattr(spec, "BAND_HOLES", None) if spec else None
                    if bh:
                        arr = self.band_inpaint(arr, e, BB, bh, pal)
                    raw = Image.fromarray(arr)
                    up = bm_tex.label_upscale(raw, (sx, sy), pal)
                    strips.append(np.asarray(up))
                W = max(s_.shape[1] for s_ in strips)
                Ht = sum(s_.shape[0] for s_ in strips)
                atlas = np.zeros((Ht, W, 3), np.uint8)
                yy, quads = 0, []
                for e, s_ in zip(art, strips):
                    h, w = s_.shape[:2]
                    atlas[yy:yy + h, :w] = s_
                    quads.append({"a": e["a"], "b": e["b"], "n": e["n"], "uv": [0.0, 1 - (yy + h) / Ht, w / W, 1 - yy / Ht]})
                    yy += h
                Image.fromarray(atlas).save(self.out / "tex" / f"north_{name}.png")
                self.mats[f"north_{name}"] = {"image": f"north_{name}.png", "uv": "quad"}
                meshes.append({"name": f"wallN_{name}", "coll": name, "mat": f"north_{name}", "kind": "wall_north",
                               "quads": quads, "h": HB})
            # Seitenwaende
            side = [e for e in edges if e["room"] == name and e["kind"] == "side"]
            longest = max(north, key=lambda e: e["len"], default=None)
            if spec and hasattr(spec, "side") and (not proc or own):
                mname = spec.side(ctx)
            elif proc:
                mname = sty.wall
            elif longest is not None and longest["len"] > 0.6:
                from bm_spec import side_from_window
                mname = side_from_window(ctx, f"side_{name}", north) if longest["len"] > H + 0.1 else None
                if mname is None:
                    mx, my = self.plain_column(north, B)
                    mname = side_from_column(ctx, f"side_{name}", mx, my, spread=0.08)
            else:
                if strips:
                    low = np.concatenate([s_[int(s_.shape[0] * 0.55):].reshape(-1, 3) for s_ in strips])
                    col = np.median(low, axis=0)
                else:
                    col = (90, 96, 100)
                mname = self.solid(f"side_{name}", col)
            groups = {}
            for e in side:                                                   # je Kante eigenes Material moeglich
                m_ = spec.side_for(ctx, e) if spec and hasattr(spec, "side_for") and (not proc or own) else None
                groups.setdefault(m_ or mname, []).append(e)
            for gi, (m_, es) in enumerate(sorted(groups.items())):
                meshes.append({"name": f"wallS_{name}" + (f"_{gi}" if len(groups) > 1 else ""), "coll": name, "mat": m_,
                               "kind": "wall_side", "h": HR if full else H,
                               "quads": [{"a": e["a"], "b": e["b"], "n": e["n"], "uv": [0, 0, e["len"], HR if full else H]} for e in es]})
            if HR > H + 1e-6 and not full and not BR:
                # obere Wandflaeche hoher Raeume: Abschlussfarbe des Bands (oberes Viertel ohne Kontur)
                if proc:
                    ucol = None
                elif strips:
                    upr = np.concatenate([s_[int(s_.shape[0] * 0.08):int(s_.shape[0] * 0.3)].reshape(-1, 3) for s_ in strips])
                    ucol = np.median(upr, axis=0)
                else:
                    ucol = (70, 80, 84)
                umat = sty.wall if proc else self.solid(f"upper_{name}", ucol)
                allq = [{"a": e["a"], "b": e["b"], "n": e["n"], "uv": [0, 0, e["len"], HR - H]} for e in north + side]
                meshes.append({"name": f"wallU_{name}", "coll": name, "mat": umat, "kind": "wall_upper", "quads": allq,
                               "z0": H, "h": HR})
            self.room_h[name] = HR
            self.__dict__.setdefault("room_side_mat", {})[name] = mname
            self.room_sky[name] = bool(spec and getattr(spec, "SKY", False)) or bool(self.cfg.get("sky_all"))
            self.room_z[name] = float(getattr(spec, "Z", None) if spec and hasattr(spec, "Z")
                                      else getattr(self, "auto_z", {}).get(name, 0.0))
            for pi, pd in enumerate(rpits):
                meshes += self.pit_meshes(ctx, name, pi, pd)
            # Einrichtung
            if spec and hasattr(spec, "props"):
                parts = spec.props(ctx)
                if parts:
                    meshes.append({"name": f"props_{name}", "coll": name, "kind": "parts", "parts": parts})
        meshes += self.lintels(edges)
        if self.mapmod is not None and hasattr(self.mapmod, "extra"):
            meshes += self.mapmod.extra(self, Ctx(self, "Terrain"))
        import bm_base
        if self.key in bm_base.BASE:
            # Einzelobjekte, die keine Raumdatei baut, als 3D-Koerper (die saubere Vorlage zeigt sie nicht mehr)
            import bm_objects
            built = [q for m in meshes if m.get("kind") == "parts" for q in m["parts"]]
            om, self.obj_stats = bm_objects.build(self, Ctx(self, "Objects"), built)
            meshes += om
        # Wandkontur: Bild quer zur Kante (u = 0 am Boden, 1 aussen), eine Spalte je 0,01
        from PIL import Image as _I
        cols = []
        for (r_, g_, b_, w_) in RIM:
            cols += [(r_, g_, b_)] * max(1, int(round(w_ * 100)))
        rim = _I.new("RGB", (len(cols), 2))
        for i, c in enumerate(cols):
            rim.putpixel((i, 0), c)
            rim.putpixel((i, 1), c)
        rim.save(self.out / "tex" / "rim.png")
        self.mats["rim"] = {"image": "rim.png", "uv": "strip", "interp": "Closest"}
        strips = self.rim_strips() if self.cfg.get("rim_strips", True) else []
        for name in sorted(self.rooms):
            for kind in ("north", "side"):
                st = [{"pts": t["pts"]} for t in strips if t["room"] == name and t["kind"] == kind]
                if st:
                    meshes.append({"name": f"rim{kind[0].upper()}_{name}", "coll": name, "mat": "rim",
                                   "kind": f"rim_{kind}", "strips": st, "z": self.room_h.get(name, H)})
        self.ceiling_material()
        capcol = self.cfg["hull"] or RIM[1][:3]                          # ohne Huellenfuellung: Wandkern = Konturmitte
        self.solid("cap", capcol)
        if self.cfg.get("cap_art") and not proc:                             # Oberseite der Wandmassen = Zeichnung
            im = ref.image
            im.save(self.out / "tex" / "cap_art.png")
            bb = [ref.mn[0], ref.mn[1], ref.mn[0] + im.width / ref.ppu, ref.mx[1]]
            self.mats["cap"] = {"image": "cap_art.png", "uv": "bbox", "bbox": bb}
            # Oberseite in Hoehe H liegt in der Zeichnung um k*H weiter noerdlich
            self.mats["cap_top"] = {"image": "cap_art.png", "uv": "bbox", "bbox": [bb[0], bb[1] - k * H, bb[2], bb[3] - k * H]}
        Wr = sum(r[3] for r in RIM)
        cap = self.ship.difference(self.floor.buffer(Wr, join_style=2, mitre_limit=3.0)).buffer(0)
        meshes.append({"name": "cap", "coll": "Hull", "mat": "cap_top" if "cap_top" in self.mats else "cap", "kind": "cap",
                       "tris": tri(cap), "z": H})
        meshes.append({"name": "cap_ground", "coll": "Hull", "mat": "cap", "kind": "ground", "tris": tri(self.cap), "z": 0.0})
        if self.cfg.get("ship") == "hull_mask" and "cap_top" in self.mats:
            from shapely.geometry import box as _bx
            decor = _bx(ref.mn[0], ref.mn[1], ref.mx[0], ref.mx[1]).difference(self.ship).buffer(0)
            meshes.append({"name": "decor", "coll": "Terrain", "mat": "cap", "kind": "floor", "tris": tri(decor), "z": -0.005})
        from shapely.geometry import Point
        hs = []
        # offene Bodenkanten (Planke, Balkon): dort keine Aussenhaut, auch wenn der Schiffsumriss (Karten mit eigenem
        # ship()) nicht an der Bodenkante liegt (Airship-Planke, Meldung 18.10. #178)
        open_zone = unary_union([LineString([e["a"], e["b"]]).buffer(Wr + 0.1, cap_style=2)
                                 for e in edges if e["kind"] == "open"] or [Polygon()])
        for sg in ([] if self.cfg.get("ship_holes") else getattr(self.ship, "geoms", [self.ship])):
            # Gelaendekarten: Wandmassen liegen zwischen Boeden, ihre Raender sind schon Waende; aussen gibt es keine Huelle
            ring = list(sg.exterior.coords)
            if not sg.exterior.is_ccw:
                ring = ring[::-1]
            for a, b in zip(ring, ring[1:]):                                 # Normale nach aussen (CCW: rechts)
                L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
                mid = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                if self.floor.distance(mid) < 0.02 or open_zone.contains(mid):
                    continue                                                 # offene Kante: keine Aussenhaut
                hs.append({"a": a, "b": b, "n": ((b[1] - a[1]) / L, -(b[0] - a[0]) / L), "uv": [0, 0, L, H]})
        self.solid("hullside", tuple(int(v * 0.8) for v in capcol))
        meshes.append({"name": "hullside", "coll": "Hull", "mat": "hullside", "kind": "wall_side", "quads": hs, "h": H})
        # Raeume auf anderer Ebene (Raumdatei Z): alles des Raums wird im Modell angehoben (Vergleich bleibt in der
        # Zeichnungslage); erhoehte Raeume bekommen eine Aussenschuerze von der Deckhoehe bis zu ihrem Boden
        for m in meshes:
            zl = self.room_z.get(m.get("coll"), 0.0)
            if zl:
                m["zlift"] = zl
        # Raeume, die ueber das Deck hinausragen (erhoeht oder hoeher als H): Aussenhaut von der Deckhoehe bis zur
        # Raumdecke und ein Dach von oben, sonst sieht man von aussen durch die einseitigen Innenwaende
        sk = []
        for e in edges:
            top = self.room_z.get(e["room"], 0.0) + self.room_h.get(e["room"], H)
            if top > H + 0.01 and not self.room_sky.get(e["room"]) and e["kind"] != "open":
                # 0,03 nach aussen versetzt: deckungsgleich mit der oberen Innenwand flimmerte die Schuerze (Z-Fighting,
                # Nightfall zeichnet beidseitig; Meldung 19.10. "Schachbrett mit schwarzen Streifen" in Storage)
                ox, oy = -e["n"][0] * 0.03, -e["n"][1] * 0.03
                sk.append({"a": (e["a"][0] + ox, e["a"][1] + oy), "b": (e["b"][0] + ox, e["b"][1] + oy),
                           "n": (-e["n"][0], -e["n"][1]), "uv": [0, 0, 1, 1], "z": round(top, 3)})
        for zt in sorted({q["z"] for q in sk}):
            meshes.append({"name": f"skirt_{zt:.2f}", "coll": "Hull", "mat": "hullside", "kind": "wall_side", "z0": H,
                           "h": zt, "quads": [q for q in sk if q["z"] == zt]})
        # Eckschlitze: Wandkanten eines niedrigen Raums direkt neben einem hoeheren enden auf der niedrigen Decke, aus
        # dem hohen Raum sah man darueber ins Leere (Ecken Storage/AdminHallway, Reactor/CrossHallway, Meldungen 18.10.)
        from shapely.geometry import Point as _Pt
        ext = {}
        for e in edges:
            r = e["room"]
            if e["kind"] == "open" or r is None or self.room_sky.get(r):
                continue
            top = self.room_z.get(r, 0.0) + self.room_h.get(r, H)
            mid = _Pt((e["a"][0] + e["b"][0]) / 2, (e["a"][1] + e["b"][1]) / 2)
            tmax = max([self.room_z.get(n, 0.0) + self.room_h.get(n, H) for n, g in self.rooms.items()
                        if n != r and not self.room_sky.get(n) and g.distance(mid) < 0.35] or [0.0])
            if tmax > top + 0.01:
                for sgn in (1, -1):
                    ox, oy = e["n"][0] * sgn * 0.02, e["n"][1] * sgn * 0.02          # je Seite leicht versetzt (kein Z-Fighting)
                    a_, b_ = (e["a"] if sgn > 0 else e["b"]), (e["b"] if sgn > 0 else e["a"])
                    ext.setdefault((round(top, 3), round(tmax, 3)), []).append(
                        {"a": (a_[0] + ox, a_[1] + oy), "b": (b_[0] + ox, b_[1] + oy),
                         "n": (e["n"][0] * sgn, e["n"][1] * sgn), "uv": [0, 0, 1, 1]})
        for (z0_, z1_), qs in sorted(ext.items()):
            meshes.append({"name": f"cornerfill_{z0_:.2f}_{z1_:.2f}", "coll": "Hull", "mat": "hullside", "kind": "wall_side",
                           "z0": z0_, "h": z1_, "quads": qs})
        for name, g in self.rooms.items():
            top = self.room_z.get(name, 0.0) + self.room_h.get(name, H)
            if top > H + 0.01 and not self.room_sky.get(name):
                meshes.append({"name": f"roof_{name}", "coll": "Hull", "mat": "cap", "kind": "cap", "tris": tri(g),
                               "z": top + 0.01})
        rooms = {n: {"bbox": list(g.bounds)} for n, g in self.rooms.items()}
        doc_light = self.lighting()
        doc = {"map": self.key, "H": H, "k": k, "ppu": ppu, "materials": self.mats, "meshes": meshes, "rooms": rooms,
               "lights": doc_light["lights"], "world": doc_light["world"], "sun": doc_light["sun"],
               "closed": self.plan.closed}
        (self.out / "scene.json").write_text(json.dumps(doc), encoding="utf-8")
        self.check_intrusions(meshes)
        return doc

    def walk_real(self):
        """Wirklich begehbare Flaeche: plan.walk sperrt nur mit Ship-Collidern; Tische, Konsolen, Kisten haben eigene
        geschlossene Collider (Ebenen ShortObjects/Objects), die hier zusaetzlich abgezogen werden."""
        if getattr(self, "_walk_real", None) is not None:
            return self._walk_real
        obst = []
        for w in self.ref.world["walls"]:
            if w.get("closed") and w["layer"] in ("ShortObjects", "Objects", "Ship"):
                for p in w["paths"]:
                    if len(p) >= 3:
                        g = Polygon(p).buffer(0)
                        if 0.01 < g.area < 40:
                            obst.append(g)
        # Offene Collider-Linien (Gelaender: Skeld engine_railback) sperren ebenfalls; der Bereich dahinter ist nur
        # erreichbar, wenn eine Konsole, ein Vent oder der Spawn darin liegt oder er gross ist (Leiter-Ebenen)
        lines = []
        for w in self.ref.world["walls"]:
            # Tuer-Schatten (z. B. Polus Comms/Walls/BottomDoor/Shadow) sind keine Sperre: Tueren stehen offen; sonst fiel
            # der Raum hinter der Tuer aus dem Laufbereich (Comms galt als nicht begehbar, Fehlerrunde 19.10. abends)
            if not w.get("closed") and w["layer"] in ("ShortObjects", "Objects") and "Door" not in w.get("path", ""):
                for p in w["paths"]:
                    if len(p) >= 2:
                        lines.append(LineString(p).buffer(0.03))
        walk = self.plan.walk.difference(unary_union(obst + lines)).buffer(0) if (obst or lines) else self.plan.walk
        from shapely.geometry import Point as _Pt
        anchors = [_Pt(*self.ref.world.get("spawn", (0, 0)))]
        anchors += [_Pt(*c["pos"]) for c in self.ref.world.get("consoles", []) if "pos" in c]
        anchors += [_Pt(*v["pos"]) for v in self.ref.world.get("vents", []) if "pos" in v]
        keep = []
        for g in getattr(walk, "geoms", [walk]):
            if g.area > 12.0 or any(g.buffer(0.3).contains(a) for a in anchors):
                keep.append(g)
        self._walk_real = unary_union(keep).buffer(0) if keep else walk
        return self._walk_real

    def check_intrusions(self, meshes):
        """Bauteile, die in die begehbare Flaeche ragen (dort stuende die Kamera im Moebel; Meldungen 18.10.: O2-Filter,
        Security-Tisch, Luefterschrank). Nur Pruefung: out/<karte>/intrusions.json, Kurzliste auf der Konsole."""
        from shapely.geometry import LineString, Point
        walk = self.walk_real().buffer(-0.04)
        found = []
        for m in meshes:
            if m.get("kind") != "parts":
                continue
            for q in m["parts"]:
                try:
                    t = q.get("type")
                    z0, z1 = q.get("z0", 0.0), q.get("z1", 1.0)
                    if t == "prism" and len(q.get("pts", [])) >= 3:
                        if z0 >= 1.0 or (z1 - z0 < 0.03 and z0 < 0.05):
                            continue                                       # ueber dem Kopf / flach am Boden
                        fp = Polygon(q["pts"]).buffer(0)
                    elif t == "lathe":
                        fp = Point(q["c"]).buffer(max(p[0] for p in q["prof"]))
                    else:
                        continue
                    hit = fp.intersection(walk)
                    if hit.area > 0.01:
                        x0, y0, x1, y1 = hit.bounds
                        found.append({"mesh": m["name"], "mat": q.get("mat"), "area": round(hit.area, 3),
                                      "depth": round(min(x1 - x0, y1 - y0), 2), "at": [round(hit.centroid.x, 2),
                                                                                         round(hit.centroid.y, 2)]})
                except Exception:
                    pass
        found.sort(key=lambda f: -f["area"])
        (self.out / "intrusions.json").write_text(json.dumps(found, indent=1), encoding="utf-8")
        print("Eindringen in den Laufbereich:", len(found), "Teile;",
              "; ".join(f"{f['mesh']}/{f['mat']} {f['area']} m2 @{f['at']}" for f in found[:12]))


if __name__ == "__main__":
    sc = Scene(sys.argv[1] if len(sys.argv) > 1 else "skeld")
    doc = sc.export()
    print("Boden", round(sc.floor.area, 2), "Raeume", len(sc.rooms), "Requisitenflaechen", len(sc.props_fp),
          "Schiff", round(sc.ship.area, 1), "Kappe", round(sc.cap.area, 1))
    print("Meshes", len(doc["meshes"]), "Materialien", len(doc["materials"]), "->", sc.out / "scene.json")
    print("Objekte", getattr(sc, "obj_stats", None), "Bereinigung", getattr(sc, "clean_stats", None))
