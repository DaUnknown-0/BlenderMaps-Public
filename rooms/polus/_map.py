# Polus - kartenweite Teile: Gelaende ausserhalb der Laufwege, Klippe, Abgrund, Bergkulisse.
#
# Gemessen (bm_analyze.py profile/colors):
#   Boden (116,83,135), dunklere Lagen (68,48,98), Gebaeudeschatten (74,63,114), Schnee (205,223,236).
#   Klippe: Bodenkante (50,43,53) 0,04, Abbruchlippe (78,77,79) 0,22, darunter Fels (59,58,60) einfarbig.
#   Bergkulisse (Parallaxe, keine Weltlage): (67,55,86), (40,35,79), (43,37,65), (96,63,114), Himmel schwarz.
# Die Kulisse ist im Spiel eine mitlaufende Ebene; im Nachbau steht sie als ferne Wand im Norden.

import cv2
import numpy as np
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

LIP = (78, 77, 79)
ROCK = (59, 58, 60)
EDGE = (50, 43, 53)
STOP = [(59, 58, 60), (78, 77, 79), (50, 43, 53), (67, 55, 86), (40, 35, 79), (43, 37, 65), (96, 63, 114), (68, 48, 98)]

# Dropship-Rumpf und Triebwerke: gezeichnet (Foto des Innenraums), kein Gelaende
FORBID = [[(10.3, -6.0), (14.3, -6.0), (14.3, 3.4), (10.3, 3.4)],
          [(19.0, -6.0), (22.6, -6.0), (22.6, 3.4), (19.0, 3.4)],
          [(14.3, -0.4), (19.0, -0.4), (19.0, 3.4), (14.3, 3.4)]]

EAST_X, EAST_Y = 41.2, -12.0   # Nordgrenze des Gelaendes oestlich des Labors
# Lavagraben: Nordwand gezeichnet 1,7 hoch (Rand y -13,3, Lava ab -15,4) -> Tiefe 1,7 / k = 3,4. Westteil (Becken)
# bis zum Rohr, unter der Bruecke (RightTubeTop) durch, Ostteil schmal bis x 44,3. Sprungbrett = Bauteil (Outside).
PIT_D = 3.4
PIT_NORTH = [(31.19, -14.61), (32.02, -13.95), (32.6, -13.4), (33.24, -13.3), (38.0, -13.3), (40.0, -13.4),
             (44.0, -13.45), (44.35, -13.9), (44.35, -15.5), (40.0, -15.6), (38.0, -15.6), (31.0, -15.6)]
LAVA_BOX = (30.8, -18.1, 44.4, -14.9)  # Suche nach Lavapixeln (Becken bis zum gezeichneten Suedufer)
LAVA_PAL = [(255, 225, 21), (255, 98, 0), (255, 42, 0)]
_PIT = None


def pit_poly(ref=None):
    """Graben = Nordteil (Wand bis zur Lava) + die gezeichnete Lava selbst (Farbmaske, Suedufer exakt)."""
    global _PIT
    if _PIT is None:
        x0, y0, x1, y1 = LAVA_BOX
        a = np.asarray(ref.crop_full(x0, y0, x1, y1)).astype(int)
        d = np.abs(a[:, :, None, :] - np.array(LAVA_PAL)[None, None]).sum(-1).min(-1)
        m = cv2.morphologyEx((d < 60).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = m.shape
        polys = [Polygon([(x0 + (q[0][0] + 0.5) / w * (x1 - x0), y1 - (q[0][1] + 0.5) / h * (y1 - y0)) for q in c])
                 for c in cs if cv2.contourArea(c) > 40]
        _PIT = unary_union([Polygon(PIT_NORTH)] + [p.buffer(0.04) for p in polys]).buffer(0.02).buffer(-0.02).simplify(0.04)
    return _PIT
BOARD = [(30.99, -16.22), (32.84, -16.14), (32.84, -15.66), (31.01, -15.65)]
PIT_RIM_Y = -13.3                    # Oberkante der gezeichneten Nordwand
PIT_ART = (30.9, -17.8, 44.4, -13.2)  # Bildausschnitt Graben (Wand + Lava)
PIT_FACE_ART = (-15.4, -13.3)         # Wand im Bild: Fuss (Lavakante) .. Oberkante

# Stege zu den Antennensaeulen (bridgeLeft/Right): Laufsteg + runde Plattform ueber dem Abgrund, baut Outside.py
BRIDGES = [{"walk": (4.22, -7.45, 5.06, -4.3), "c": (4.65, -3.98), "pillar": (4.68, -3.91), "r": 1.0},
           {"walk": (23.75, -6.62, 24.59, -3.28), "c": (24.18, -2.96), "pillar": (24.21, -2.89), "r": 1.0}]


def bridge_poly(b):
    from shapely.geometry import Point
    return unary_union([sbox(*b["walk"]), Point(*b["c"]).buffer(b["r"], 48)])


# Kistenstapel neben der Rampe haengen am Dropship-Collider: dort Gelaende statt Wand (Kisten baut Outside.py)
FLOOR_ADD = [[(10.95, -6.42), (11.6, -7.4), (12.4, -8.0), (14.24, -8.05), (14.40, -6.25), (14.30, -6.12), (11.0, -6.12)],
             [(18.93, -6.25), (19.10, -8.0), (20.9, -7.9), (22.39, -6.9), (23.26, -6.60), (23.30, -6.12), (19.0, -6.12)],
             [(14.05, -8.10), (14.55, -8.10), (14.55, -6.10), (14.05, -6.10)],
             [(18.75, -8.10), (19.35, -8.10), (19.35, -6.10), (18.75, -6.10)]]
KEEP_WALLS = [(4.75, -20.3)]          # O2: Zwischenwand storage_middlewall
# Innenraeume, deren Einrichtung im Wand-Collider steckt (Kisten gebaut in der Raumdatei): dort Boden des Raums
FLOOR_ADD_ROOMS = {"Storage": [[(18.55, -12.95), (22.75, -12.95), (22.75, -10.10), (20.25, -10.10), (20.25, -10.75),
                                (18.55, -10.75)],
                               [(17.20, -12.95), (18.60, -12.95), (18.60, -11.62), (17.20, -11.62)],
                               # Werkzeugregal an der Nordwand (Fehlerrunde 19.10.)
                               [(18.30, -10.15), (19.90, -10.15), (19.90, -10.95), (18.30, -10.95)]],
                   # Specimen: der Probentisch steckt im Ship-Collider "RightPod/Walls" (35,0..37,9 / -20,94..-20,32);
                   # daraus wurde eine Wand hinter den Roehren (User 18.10.). Boden bis unter den Tisch, Bank frei.
                   "Specimen": [[(34.95, -21.0), (37.97, -21.0), (37.97, -20.25), (34.95, -20.25)]],
                   # Labor (Fehlerrunde 19.10.): Bettnische Nord, Spindreihe im Flur, Waschraum mit Kabinen standen als
                   # raumhohe Wandbloecke bzw. Tafel im Weg (#261, #264); die Raumdatei baut sie als Koerper
                   # O2: Spind am Ende der Zwischenwand (x 2,08..2,5 / -21,36..-20,61), war ein raumhoher Wandblock (#250)
                   "LifeSupport": [[(2.04, -21.40), (2.54, -21.40), (2.54, -20.58), (2.04, -20.58)]],
                   # Comms-Nordwand: Spinde, WLAN-Kasten und Schreibtisch standen nur als Zeichnung im Wandband (#283)
                   # Fehlerrunde 19.10. abends (#287): der Streifen endete bei -15,50, der Raumboden aber erst bei -15,69;
                   # dazwischen blieb Wand stehen, _regroup machte den abgetrennten Streifen zur Wandmasse und Spinde,
                   # WLAN-Kasten und Schreibtisch steckten wieder in der Wand. Jetzt ueberlappend bis -15,78.
                   "Comms": [[(10.25, -15.78), (12.40, -15.78), (12.40, -14.95), (10.25, -14.95)]],
                   # Weapons: unter der Kanonenkapsel war ein Loch ohne Boden und ohne Wandmasse (Boden-Aussparung an der
                   # gezeichneten Kapsel); man sah dunkel in die Tiefe, darum standen Waende um die Kapsel (#288)
                   "Weapons": [[(9.64, -23.74), (10.02, -23.74), (10.20, -24.02), (11.12, -24.10), (11.56, -24.55),
                                (11.56, -25.22), (9.64, -25.22)],
                               # Waffenpult (L) bis an die Nordwand (Wandfuss -22,18): stand in einer Wandmasse hinter
                               # seinem Front-Collider, nur Teile ragten heraus (#288-Nachpruefung)
                               [(9.64, -22.18), (10.84, -22.18), (10.84, -23.85), (9.64, -23.85)]],
                   # Office-Flur: Topfpflanzen und Wandsockel vor den Wandbloecken (Wandfuss der Zeichnung -18,64, der
                   # Collider liegt 0,2 weiter vorn an den Toepfen); vorher steckten die Toepfe in der Wand (#290/#291)
                   "OfficeHall": [[(17.92, -18.64), (21.62, -18.64), (21.62, -18.98), (17.92, -18.98)],
                                  [(15.98, -18.62), (16.62, -18.62), (16.62, -19.02), (15.98, -19.02)]],
                   "Science": [[(36.85, -7.62), (39.75, -7.62), (39.75, -6.22), (36.85, -6.22)],
                               [(36.85, -8.66), (39.75, -8.66), (39.75, -8.18), (36.85, -8.18)],
                               [(28.00, -9.55), (30.15, -9.55), (30.15, -8.95), (28.00, -8.95)],
                               [(32.63, -9.85), (35.42, -9.85), (35.42, -8.55), (32.63, -8.55)]],
                   # Buero Ost (#294): Schreibtisch, Monitore und ID-Scanner stehen vor der Nordwand (Wandfuss -16,0); der
                   # Collider liegt an der Pultfront (-16,45), dort stand die Wand und die Einrichtung steckte darin
                   "Office": [[(24.00, -16.68), (27.60, -16.68), (27.60, -15.98), (24.00, -15.98)]]}
DS_HULL = [(10.9, -6.15), (22.5, -6.15), (22.5, 3.6), (10.9, 3.6)]   # Rumpf (Dropship.py), Kanten davor offen

CLIFF_D = 8.0          # Tiefe des Abgrunds unter der Hochebene
LIP_D = 0.44           # Abbruchlippe: gezeichnet 0,22 hoch -> 0,22 / k


def adjust(sc):
    """Gelaende: Boden ueber die Laufwege hinaus bis an die gezeichnete Kante fluten (Schnee hinter der Roehre,
    Osthang, Lavagraben). Gesperrt: Klippe, Kulisse, Weltraum, Wandmassen, alles noerdlich der Laufwege."""
    ref, pl = sc.ref, sc.plan
    from bm_plan import RES
    img = ref.img.astype(np.int16)
    stop = (img.sum(-1) / 3 < 30) | (np.abs(img - np.array(sc.cfg["space"])).sum(-1) <= 30)
    for c in STOP + [sc.cfg["hull"]]:
        stop |= np.abs(img - np.array(c)).sum(-1) <= 6
    stop = cv2.resize(stop.astype(np.float32), (int(round(ref.W * RES / ref.ppu)), int(round(ref.H * RES / ref.ppu))),
                      interpolation=cv2.INTER_AREA) > 0.15
    g = np.ones((pl.gh, pl.gw), np.uint8)
    h, w = min(g.shape[0], stop.shape[0]), min(g.shape[1], stop.shape[1])
    g[:h, :w] = stop[:h, :w]
    floor = sc._raster(sc.floor)
    # Wandmassen (Boden + Kontur, Spalten geschlossen) und der Dropship-Rumpf sind tabu
    Wr = sum(r[3] for r in sc.cfg["rim"]) + 0.005
    inner = sc.floor.difference(sc.rooms["Outside"]).buffer(Wr, join_style=2, mitre_limit=3.0)
    forb = sc._raster(unary_union(sc.wall_holes + [inner] + [Polygon(p) for p in FORBID])) & (floor == 0)
    # Nordgrenze je Spalte: nicht ueber den noerdlichsten Laufpunkt hinaus (dahinter beginnt die Kulisse)
    walk = sc._raster(sc.plan.walk)
    cols = np.where(walk.any(0))[0]
    top = np.array([np.argmax(walk[:, c] > 0) for c in cols])
    lim = np.interp(np.arange(walk.shape[1]), cols, top).astype(int)
    # oestlich des Labors beginnt ueber dem Lavagraben gleich die Kulisse (dunkle Bergschicht bis y -11,5)
    ex = int(round((EAST_X - pl.ox) * RES))
    lim[ex:] = int(round((pl.oy - EAST_Y) * RES))
    rows = np.arange(walk.shape[0])[:, None]
    forb |= (rows < lim[None, :] - 2).astype(np.uint8)
    allow = ((g == 0) & (forb == 0) & (floor == 0)).astype(np.uint8)
    # nicht nur vom Laufbereich aus: Schneefeld hinter der Roehre und Osthang sind von Waenden umschlossen
    n, lab, st, _ = cv2.connectedComponentsWithStats(allow, connectivity=4)
    big = np.zeros(n, bool)
    big[1:] = st[1:, cv2.CC_STAT_AREA] > 3.0 * RES * RES
    m = big[lab].astype(np.uint8)
    m = cv2.morphologyEx(m | floor, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    extra = pl._polys(m & (floor == 0)).buffer(0)
    extra = extra.difference(sc.floor).buffer(0)
    pieces = [p for p in getattr(extra, "geoms", [extra]) if p.area > 0.05]
    if pieces:
        add = unary_union(pieces)
        sc.rooms["Outside"] = unary_union([sc.rooms["Outside"], add]).buffer(0)
        sc.floor = unary_union([sc.floor, add]).buffer(0)
    sc.terrain_added = sum(p.area for p in pieces)
    add = unary_union([Polygon(p) for p in FLOOR_ADD]).buffer(0)
    others = unary_union([g for n, g in sc.rooms.items() if n != "Outside"])
    sc.rooms["Outside"] = unary_union([sc.rooms["Outside"], add.difference(others)]).buffer(0)
    sc.floor = unary_union([sc.floor, add]).buffer(0)
    sc.wall_holes = [h.difference(add).buffer(0) for h in sc.wall_holes if not h.difference(add).is_empty]
    for name, polys in FLOOR_ADD_ROOMS.items():
        add = unary_union([Polygon(p) for p in polys]).buffer(0)
        sc.rooms[name] = unary_union([sc.rooms[name], add]).buffer(0)
        for n in sc.rooms:
            if n != name:
                sc.rooms[n] = sc.rooms[n].difference(add).buffer(0)
        sc.floor = unary_union([sc.floor, add]).buffer(0)
        sc.wall_holes = [h.difference(add).buffer(0) for h in sc.wall_holes if not h.difference(add).is_empty]
    # Freistehende Waende, die nur an einen Raum grenzen (sonst als Requisit mit Boden gefuellt)
    from shapely.geometry import Point
    for pt in KEEP_WALLS:
        for hp in list(sc.props_fp):
            if hp.contains(Point(pt)):
                sc.props_fp.remove(hp)
                sc.wall_holes.append(hp)
                sc.floor = sc.floor.difference(hp).buffer(0)
                for n in sc.rooms:
                    sc.rooms[n] = sc.rooms[n].difference(hp).buffer(0)
    # Stege gehoeren nicht zum Gelaende (eigene Planken ueber dem Abgrund)
    br = unary_union([bridge_poly(b) for b in BRIDGES])
    sc.rooms["Outside"] = sc.rooms["Outside"].difference(br).buffer(0)
    sc.floor = sc.floor.difference(br).buffer(0)
    # Lavagraben aus dem Gelaende schneiden (das Sprungbrett baut Outside.py als Planke darueber)
    pit = pit_poly(sc.ref)
    others = unary_union([g for n, g in sc.rooms.items() if n != "Outside"])
    sc.rooms["Outside"] = sc.rooms["Outside"].difference(pit).buffer(0)
    sc.floor = sc.floor.difference(pit.difference(others)).buffer(0)
    cut = unary_union([Polygon(p) for p in FLOOR_CUT]).buffer(0)
    sc.floor = sc.floor.difference(cut).buffer(0)
    for n in list(sc.rooms):
        sc.rooms[n] = sc.rooms[n].difference(cut).buffer(0)
    collider_walls(sc)


# ---------------------------------------------------------------- duenne Waende aus den Collidern (Fehlerrunde 19.10.)
# Polus zeichnet Gebaeudewaende duenn (0,1..0,15, dunkle Kontur). Der Grundriss liess den Boden darueber wachsen und die
# Restspalten-Schliessung (0,12) machte die Loecher zu: LifeSupport, Kesselraum, Weapons, Comms, Admin, Specimen und die
# Roehren standen zur Seite offen (Meldungen #247..#283). Hier wird entlang jeder Wand-Collider-Linie (Ship, */Walls),
# die mitten im Boden liegt (Boden auf beiden Seiten, auf beiden Seiten begehbare Flaeche in Reichweite), ein
# Wandstreifen ausgeschnitten und als Wandmasse gefuehrt.
import re as _re
WALL_PATH = _re.compile(r"/(Walls|TubeWalls)$")
WALL_SKIP = ("Dropship/Walls",)
WALL_HALF = 0.06                       # halbe Wandstaerke
WALL_REACH = 0.8                       # begehbare Flaeche auf beiden Seiten innerhalb dieser Entfernung
WALL_ADD = [                           # Wandmassen, die kein Collider im Boden findet
    # Weapons-Westwand hinter der Kanone (gezeichnet x 9,45..9,62): der Boden wuchs durch das Kanonen-Sprite bis ins Pult
    [(9.40, -21.62), (9.66, -21.62), (9.66, -25.30), (9.40, -25.30)],
    # Labor: Westwand des Waschraums (Shadow x 32,58 von -8,57 bis -11,07), zwischen Flur und Kabinen (#261)
    [(32.47, -8.55), (32.63, -8.55), (32.63, -10.95), (32.47, -10.95)],
    # LowerDecon-Westwand (Shadow x 22,65..22,74 von -23,03 bis -26,18): Collider nur unten, oben sah man ins Admin (#273)
    [(22.62, -23.0), (22.77, -23.0), (22.77, -25.72), (22.62, -25.72)],
    # Specimen: Ecke zwischen Roehren-Nordwand und Konsolen-Diagonale (Lichtschlitz)
    [(33.60, -19.95), (33.60, -20.42), (33.80, -20.42), (34.06, -19.86), (33.92, -19.78)],
    # Fehlerrunde 19.10. abends:
    # Comms-Vorraum: Tuerpfosten beidseits der BottomDoor (Shadow-Collider 10,11..10,22 und 11,59..11,68 bei -18,7..-18,95);
    # dort lag zwischen zwei Wandstreifen ein Schlitz ins Freie (#285/#286)
    [(9.98, -18.30), (10.25, -18.30), (10.25, -19.62), (9.98, -19.62)],
    [(11.57, -18.40), (11.86, -18.40), (11.86, -19.62), (11.57, -19.62)],
    # Comms-Westwand (Ship-Collider Comms/Walls x 9,954..10,243 von -14,73 bis -19,6): der Boden reichte bis x 10,08, die
    # Wand stand 0,16 m zu weit draussen (20.10.); schliesst oben an das Nordband (FLOOR_ADD_ROOMS ab 10,25), unten an den Pfosten
    [(9.95, -14.95), (10.243, -14.95), (10.243, -18.30), (9.95, -18.30)],
    # Storage-Ostwand (x 22,72..22,92): FLOOR_ADD_ROOMS liess den Raumboden direkt an das Gelaende stossen, dort entsteht
    # keine Wand; man sah von draussen in den Lagerraum (#297)
    [(22.72, -10.00), (22.95, -10.00), (22.95, -13.35), (22.72, -13.35)],
    # Office: Wandblock mit Buestenschrank zwischen Besprechungsraum und Flur (Collider 22,88..23,72 / -18,0..-18,75); war
    # Boden mit nur einem duennen Wandstreifen bei -18,1 (#293)
    [(22.88, -18.02), (23.76, -18.02), (23.76, -18.64), (22.88, -18.64)],
    # Labor-Waschraum: Nordwand (Shadow/Ship y -8,42 von x 32,6 bis 35,4); FLOOR_ADD_ROOMS liess den Kabinenboden mit dem
    # Labor verschmelzen, man sah von Norden auf die Kabinen (#301/#302)
    [(32.55, -8.40), (35.47, -8.40), (35.47, -8.56), (32.55, -8.56)],
    # UpperDecon-Westtuer: Wandbloecke beidseits der Tueroeffnung (Science/Walls 37,81..38,15 / -10,36..-10,88 und
    # -9,28..-9,41); suedlich stand der Tuerpfosten frei im Laborboden (#303)
    [(37.80, -10.36), (38.16, -10.36), (38.16, -10.98), (37.80, -10.98)],
    [(37.80, -9.22), (38.16, -9.22), (38.16, -9.42), (37.80, -9.42)],
    # Untere Roehre: Ecke der Aussenwand (Ship RightTube/Walls (26,95|-20,68)-(27,25|-20,39)); die Diagonale bekam keinen
    # Wandstreifen, durch den Spalt sah man auf das Gelaende neben der Roehre (#306)
    [(26.84, -20.28), (27.30, -20.28), (27.30, -20.39), (27.25, -20.39), (26.95, -20.68), (26.95, -20.80), (26.84, -20.80)],
    # Laborbalkon: Westpfeiler (x < 32,62 von -5,82 bis -6,95); vorher Bodenzunge mit einer 0,09 breiten Wandscheibe (#300)
    [(32.46, -5.82), (32.61, -5.82), (32.61, -6.95), (32.46, -6.95)],
]
# Feste Wandfarben (bm_style.RoomStyle): Comms misst sein Nordband seit dem Wandmoebel-Streifen (#287) im Gelaende ueber
# der Wandkrone (lila); Werte = Messung an der alten Nordkante -15,69 (Wandfront mit Spinden und Schreibtisch)
WALL_STYLE = {"Comms": {"main": (63, 64, 83), "accent": (88, 107, 102), "trim": (77, 93, 89)},
              # Office (Besprechungsraum + Buero Ost teilen einen Stil): mit dem Moebelstreifen an der Ostbuero-Nordwand
              # (#294) kippte die Messung auf Holzboden und gruene Tapete; Werte = bisherige Messung (Stand 17:53)
              "Office": {"main": (102, 108, 93), "accent": (144, 149, 130), "trim": (120, 125, 108)}}
# Feste Bodenfarben (Haupt, Zweit): Office wie bisher blauer Teppich; UpperDecon wie bisher (die neuen Wandbloecke an
# der Westtuer verschoben die Messung auf die hellen Kacheln)
FLOOR_STYLE = {"Office": ((59, 90, 154), (165, 146, 112)), "UpperDecon": ((160, 156, 129), (183, 202, 215))}
# Bodenflaechen, die gar nicht zur Karte gehoeren (weder Boden noch Wand): Zunge des Balkons jenseits der Diagonale
# (Collider Science/Walls (32,62|-5,82)-(33,24|-5,26)), dort stand die schmale dunkle Scheibe (#300)
FLOOR_CUT = [
    [(32.30, -4.90), (33.60, -4.90), (33.24, -5.26), (32.62, -5.82), (32.30, -5.82)],
]
# Bereiche, in denen collider_walls keine Wand ziehen darf: Westzaun des Laborhofs (Science/Walls x 24,77, gezeichnet ist
# nur ein Maschendrahtzaun; Outside.py baut ihn), dort stand eine raumhohe weisse Wand (#298/#299)
WALL_SKIP_BOXES = [(24.60, -8.26, 24.95, -6.50)]
# Schatten-Collider von Felsen/Kistenhaufen sind keine Waende (#296: Wandscheibe mitten im Felshaufen bei 26,4..27,4/-13,4)
SHADOW_SKIP = ("RocksNBoxes",)


def collider_walls(sc):
    import math
    from shapely.geometry import LineString, Point
    fl = sc.floor
    walk = sc.plan.walk
    skipbox = unary_union([sbox(*b) for b in WALL_SKIP_BOXES])
    keep = unary_union([Polygon(p) for p in FLOOR_ADD] + [Polygon(p) for ps in FLOOR_ADD_ROOMS.values() for p in ps]
                       + [Polygon(DS_HULL)]).buffer(0.05)
    # nur echte Waende: sie sperren im Spiel das Licht (Shadow-Collider in der Naehe); Betten, Tische und Gelaender
    # haben Ship-Collider, aber keinen Schatten
    shadow = unary_union([LineString(path).buffer(0.9) for w, path in sc.ref.colliders(("Shadow",)) if len(path) > 1
                          and not any(t in w["path"] for t in SHADOW_SKIP)])
    shlines = unary_union([LineString(path) for w, path in sc.ref.colliders(("Shadow",)) if len(path) > 1
                           and not any(t in w["path"] for t in SHADOW_SKIP)])
    runs = []
    for w, path in sc.ref.colliders(("Ship",)):
        if not WALL_PATH.search(w["path"]) or any(t in w["path"] for t in WALL_SKIP):
            continue
        for a, b in zip(path, path[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 1e-4:
                continue
            nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
            n = max(1, int(L / 0.05))
            cur = []
            for i in range(n + 1):
                t = i / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                p = Point(x, y)
                p1, p2 = Point(x + nx * 0.1, y + ny * 0.1), Point(x - nx * 0.1, y - ny * 0.1)
                ok = (fl.contains(p1) and fl.contains(p2) and not keep.contains(p) and shadow.contains(p)
                      and not skipbox.contains(p) and walk.distance(p1) < WALL_REACH and walk.distance(p2) < WALL_REACH
                      and not walk.buffer(-0.02).contains(p))
                # beide Seiten: begehbare Flaeche auf der jeweiligen Seite (nicht nur ueber die Linie hinweg)
                if ok:
                    s1 = LineString([(x + nx * 0.06, y + ny * 0.06), (x + nx * WALL_REACH, y + ny * WALL_REACH)])
                    s2 = LineString([(x - nx * 0.06, y - ny * 0.06), (x - nx * WALL_REACH, y - ny * WALL_REACH)])
                    ok = _reach(s1, walk, shlines) and _reach(s2, walk, shlines)
                if ok:
                    cur.append((x, y))
                elif cur:
                    runs.append(cur)
                    cur = []
            if cur:
                runs.append(cur)
    # Schatten-Collider (Lichtsperren = Waende) ohne Ship-Collider daneben: Specimen-Nordwestwand hinter den Konsolen,
    # dort liegt draussen kein Laufbereich (#270)
    for w, path in sc.ref.colliders(("Shadow",)):
        if any(t in w["path"] for t in SHADOW_SKIP):
            continue
        for a, b in zip(path, path[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 1e-4:
                continue
            nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
            n = max(1, int(L / 0.05))
            cur = []
            for i in range(n + 1):
                t = i / n
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                p = Point(x, y)
                p1, p2 = Point(x + nx * 0.1, y + ny * 0.1), Point(x - nx * 0.1, y - ny * 0.1)
                ok = (fl.contains(p1) and fl.contains(p2) and fl.contains(p) and not keep.contains(p) and not skipbox.contains(p)
                      and (walk.distance(p1) < WALL_REACH or walk.distance(p2) < WALL_REACH)
                      and not walk.buffer(0.05).contains(p))
                if ok:
                    cur.append((x, y))
                elif cur:
                    runs.append(cur)
                    cur = []
            if cur:
                runs.append(cur)
    strips = [LineString(r).buffer(WALL_HALF, cap_style=2, join_style=2) for r in runs if len(r) >= 5]
    strips += [Polygon(p) for p in WALL_ADD]
    if not strips:
        return
    cut = unary_union(strips).buffer(0)
    sc.collider_cut = round(cut.area, 2)
    sc.floor = sc.floor.difference(cut).buffer(0)
    for n in list(sc.rooms):
        sc.rooms[n] = sc.rooms[n].difference(cut).buffer(0)
    sc.wall_holes = sc.wall_holes + [g for g in getattr(cut, "geoms", [cut]) if g.area > 1e-4]
    _regroup(sc, cut)


def _reach(seg, walk, shlines):
    """Erreicht der Strahl begehbare Flaeche, ohne vorher eine Lichtsperre (Shadow-Collider) zu kreuzen? Sonst liegt
    dahinter ein anderer Raum (Specimen-Konsolen: deren Front-Collider wurde sonst zur Wand, #270)."""
    from shapely.geometry import LineString, Point
    hit = seg.intersection(walk)
    if hit.is_empty:
        return False
    a = Point(seg.coords[0])
    d = min(a.distance(g) for g in getattr(hit, "geoms", [hit]))
    if d < 0.02:
        return True
    (x0, y0), (x1, y1) = seg.coords[0], seg.coords[-1]
    L = seg.length
    pre = LineString([(x0, y0), (x0 + (x1 - x0) * d / L, y0 + (y1 - y0) * d / L)])
    return not pre.intersects(shlines)


def _regroup(sc, cut):
    """Nach dem Schnitt: Raumteile ohne Verbindung zum Hauptteil dem Nachbarraum mit der laengsten direkten Grenze
    geben (Gelaende ausserhalb der Roehren gehoerte zur Roehre); abgeschnittene Bodenstuecke ohne begehbare Flaeche
    werden Wandmasse (Schlitze zwischen zwei Wandstreifen)."""
    walk = sc.plan.walk
    for it in range(3):
        moved = False
        for n in list(sc.rooms):
            parts = sorted(getattr(sc.rooms[n], "geoms", [sc.rooms[n]]), key=lambda q: -q.area)
            if len(parts) < 2:
                continue
            main = parts[0]
            keep = [main]
            for q in parts[1:]:
                thin = q.area / max(q.length, 1e-6) < 0.35
                if q.intersection(walk).area < 0.02 and (q.area < 3.0 or thin):
                    # kein begehbarer Teil: Wandmasse
                    sc.floor = sc.floor.difference(q.buffer(0.002)).buffer(0)
                    sc.wall_holes.append(q.buffer(0.002))
                    moved = True
                    continue
                share = {m: sc.rooms[m].buffer(0.02).intersection(q.boundary).length for m in sc.rooms if m != n}
                best = max(share, key=share.get) if share else None
                own = main.buffer(0.02).intersection(q.boundary).length
                if best is not None and share[best] > max(0.3, own) and q.area < 4.0:
                    sc.rooms[best] = unary_union([sc.rooms[best], q]).buffer(0)
                    moved = True
                else:
                    keep.append(q)
            sc.rooms[n] = unary_union(keep).buffer(0)
        if not moved:
            break
    for n in list(sc.rooms):
        sc.rooms[n] = sc.rooms[n].intersection(sc.floor).buffer(0)


def open_edge(sc, a, b, nx, ny):
    """Kanten am Lavagraben haben keine Wand (der Graben baut eigene Felswaende)."""
    from shapely.geometry import LineString
    from shapely.geometry import Point
    mid = Point((a[0] + b[0]) / 2 + nx * 0.05, (a[1] + b[1]) / 2 + ny * 0.05)
    out = getattr(sc, "rooms", {}).get("Outside")
    if out is not None and out.distance(mid) < 0.06 and pit_poly(sc.ref).buffer(0.4).contains(mid):
        return True
    if any(bridge_poly(b).buffer(0.2).contains(mid) for b in BRIDGES):
        return True
    if out is not None and out.distance(mid) < 0.06 and Polygon(DS_HULL).buffer(0.3).contains(mid):
        return True
    rooms = getattr(sc, "rooms", None)
    if not rooms:
        return None
    # Innenraeume haben nie offene Kanten: hinter duennen Polus-Waenden liegt die dunkle Kontur (Mittel < 30), die der
    # Himmelstest fuer Nacht hielt (Admin-Westwand, Specimen, Roehren standen ohne Wand da; Meldungen 19.10.).
    room = sc._room_at(((a[0] + b[0]) / 2 + nx * 0.05, (a[1] + b[1]) / 2 + ny * 0.05))
    behind = []
    for d in (0.15, 0.3, 0.6, 1.0):
        behind.append(Point((a[0] + b[0]) / 2 - nx * d, (a[1] + b[1]) / 2 - ny * d))
    solid = any(sc.floor.contains(q) for q in behind) or any(h.contains(q) for h in sc.wall_holes for q in behind[:3])
    if room in OPEN_ROOMS:
        return not solid
    if room != "Outside":
        return False
    if solid:
        return False                   # Gelaende vor einer Gebaeudewand: Wand (Fassade), nicht offen
    return None


OPEN_ROOMS = ("Balcony",)              # Raeume mit offenen Aussenkanten (Gelaender statt Wand)


BAND = (-34.8, -13.6, -8.0, -0.3)   # sauberer Ausschnitt der Bergkulisse (links der Karte, nichts davor)
RING = (-46.0, -52.0, 86.0, 24.0)   # Kulissenwand rund um die Karte (x0, y0, x1, y1)


def extra(sc, ctx):
    """Klippenwaende an allen offenen Kanten, Abgrund, Bergkulisse als Wand rund um die Karte."""
    import bm_tex as T
    out = []
    br = unary_union([bridge_poly(b) for b in BRIDGES]).buffer(0.15)
    from shapely.geometry import Point as _P
    opens = [e for e in sc.wall_edges() if e["kind"] == "open"
             and not br.contains(_P((e["a"][0] + e["b"][0]) / 2, (e["a"][1] + e["b"][1]) / 2))]
    lip = ctx.color("polus_cliff_lip", LIP)
    rock = ctx.color("polus_cliff_rock", ROCK)
    quads = [{"a": e["a"], "b": e["b"], "n": (-e["n"][0], -e["n"][1]), "uv": [0, 0, 1, 1]} for e in opens]
    out.append({"name": "cliff_lip", "coll": "Terrain", "mat": lip, "kind": "wall_side", "quads": quads,
                "z0": -LIP_D, "h": 0.0})
    out.append({"name": "cliff_rock", "coll": "Terrain", "mat": rock, "kind": "wall_side", "quads": quads,
                "z0": -CLIFF_D, "h": -LIP_D})
    out += lava_pit(sc, ctx)
    # Abgrund: grosse Felsebene unter allem
    x0, y0, x1, y1 = RING
    out.append({"name": "abyss", "coll": "Terrain", "mat": rock, "kind": "under", "z": -CLIFF_D,
                "tris": [[[x0, y0], [x1, y0], [x1, y1]], [[x0, y0], [x1, y1], [x0, y1]]]})
    # Bergkulisse: Ausschnitt in Originalfarben, kachelweise rund um die Karte (Innenseite zur Karte)
    bx0, by0, bx1, by1 = BAND
    mat = ctx.tex("polus_backdrop", backdrop_image(seed=3), uv="quad")
    tw, th = bx1 - bx0, (by1 - by0) * 1.6
    ztop = -CLIFF_D + th
    quads = []
    for (ax, ay), (bx, by), n in [((x0, y1), (x1, y1), (0, -1)), ((x1, y1), (x1, y0), (-1, 0)),
                                  ((x1, y0), (x0, y0), (0, 1)), ((x0, y0), (x0, y1), (1, 0))]:
        L = abs(bx - ax) + abs(by - ay)
        nt = max(1, int(round(L / tw)))
        for i in range(nt):
            f0, f1 = i / nt, (i + 1) / nt
            a = (ax + (bx - ax) * f0, ay + (by - ay) * f0)
            b = (ax + (bx - ax) * f1, ay + (by - ay) * f1)
            quads.append({"a": a, "b": b, "n": n, "uv": [0, 0, 1, 1]})
    out.append({"name": "backdrop", "coll": "Terrain", "mat": mat, "kind": "wall_side", "quads": quads,
                "z0": -CLIFF_D, "h": ztop})
    return out


def backdrop_image(seed=0, w=1024, h=384):
    """Bergkulisse (prozedural): Nachthimmel, zwei Bergketten in den Polus-Bergfarben (96,63,114)/(68,48,98) mit
    Schneekaemmen, keine Spieltextur."""
    import math
    import random
    from PIL import Image as _I, ImageDraw as _D
    rnd = random.Random(seed)
    im = _I.new("RGB", (w, h), (41, 23, 56))
    d = _D.Draw(im)
    for y in range(h // 2):
        t = y / (h / 2)
        d.line([(0, y), (w, y)], fill=(int(41 + 10 * t), int(23 + 8 * t), int(56 + 14 * t)))
    for _ in range(60):
        x, y = rnd.randrange(w), rnd.randrange(h // 2)
        d.point((x, y), fill=(220, 220, 240))
    for col, base, amp, snow in (((68, 48, 98), 0.42, 0.22, (120, 100, 150)), ((96, 63, 114), 0.62, 0.18, (170, 150, 190))):
        pts = [(0, h)]
        for i in range(0, w + 1, 16):
            yy = h * (base + amp * (0.5 * math.sin(i / w * 11 + seed) + 0.3 * math.sin(i / w * 29 + seed * 2) + 0.2 * math.sin(i / w * 61)))
            pts.append((i, int(yy)))
        pts.append((w, h))
        d.polygon(pts, fill=col)
        for i in range(2, len(pts) - 2):
            if pts[i][1] < pts[i - 1][1] and pts[i][1] < pts[i + 1][1]:
                d.polygon([pts[i], (pts[i][0] - 14, pts[i][1] + 14), (pts[i][0] + 14, pts[i][1] + 14)], fill=snow)
    return im


def lava_image(seed=0, s=256):
    """Lava-Kachel 2 x 2 m: orange Grund, weiche rote Mulden, wenige gelbe Glutflecken, dunkle Krustenschollen, danach
    weichgezeichnet (Meldung #295: die gelben Adern wirkten wie Kritzel). Kachelbar: Flecken am Rand werden gespiegelt."""
    import random
    from PIL import Image as _I, ImageDraw as _D, ImageFilter as _F
    rnd = random.Random(seed)
    im = _I.new("RGB", (s, s), (255, 98, 0))
    d = _D.Draw(im)

    def ell(x, y, rx, ry, col):
        for ox in (-s, 0, s):
            for oy in (-s, 0, s):
                d.ellipse([x + ox - rx, y + oy - ry, x + ox + rx, y + oy + ry], fill=col)
    for _ in range(14):
        ell(rnd.randrange(s), rnd.randrange(s), rnd.randint(18, 46), rnd.randint(10, 26), (240, 60, 0))
    for _ in range(9):
        ell(rnd.randrange(s), rnd.randrange(s), rnd.randint(8, 20), rnd.randint(5, 12), (255, 190, 30))
    im = im.filter(_F.GaussianBlur(6))
    d = _D.Draw(im)
    for _ in range(7):
        ell(rnd.randrange(s), rnd.randrange(s), rnd.randint(6, 14), rnd.randint(4, 8), (130, 44, 20))
    return im.filter(_F.GaussianBlur(1.5))


def lava_pit(sc, ctx):
    """Graben: Lava (leuchtend, Zeichnung gestreckt auf die Weltlage), Nordwand mit der gezeichneten Felswand,
    uebrige Waende in der Schattenfarbe des Gesteins."""
    import bm_tex as T
    from bm_scene import tri
    out = []
    pit = pit_poly(sc.ref)
    x0, y0, x1, y1 = PIT_ART
    # Lava 1:1 an ihrer Bildlage; was nicht Lava ist (Ufer, Felswand, Sprungbrett) und der Streifen unter der Nordwand
    # wird aus den Lavafarben ergaenzt (Gelb (255,225,21), Orange (255,98,0), Rot (255,42,0))
    import cv2
    import numpy as np
    from PIL import Image as _I
    lm = ctx.tex("polus_lava", lava_image(seed=5), uv="world", scale=[2.0, 2.0])
    ctx.scene.mats[lm]["emit"] = 1.5
    out.append({"name": "lava", "coll": "Terrain", "mat": lm, "kind": "floor", "z": -PIT_D, "tris": tri(pit)})
    import bm_style
    fm = ctx.tex("polus_pit_face", bm_style.wall_image("rock", (96, 63, 114), trim=(68, 48, 98), H=2.0, seed=11), uv="world", scale=[2.0, 2.0])
    shade = ctx.color("polus_pit_wall", (104, 83, 110))
    ring = list(pit.exterior.coords)
    if not pit.exterior.is_ccw:
        ring = ring[::-1]
    north, other = [], []
    for a, b in zip(ring, ring[1:]):
        L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        if L < 1e-4:
            continue
        n = ((b[1] - a[1]) / L * -1, (b[0] - a[0]) / L)                   # CCW: links = innen
        q = {"a": a, "b": b, "n": n, "uv": [(a[0] - x0) / (x1 - x0), 0, (b[0] - x0) / (x1 - x0), 1]}
        (north if (n[1] < -0.5 and min(a[1], b[1]) > -13.6) else other).append(q)
    out.append({"name": "pit_north", "coll": "Terrain", "mat": fm, "kind": "wall_side", "quads": north,
                "z0": -PIT_D, "h": 0.0})
    out.append({"name": "pit_walls", "coll": "Terrain", "mat": shade, "kind": "wall_side", "quads": other,
                "z0": -PIT_D, "h": 0.0})
    return out
