# Mira HQ - kartenweite Eingriffe.
#
# Pruefrunde 18.10. (Augenhoehe): Mira zeichnet um fast jeden Raum Wolken, deshalb wurden die Seitenkanten der
# geschlossenen Raeume (Locker, Office, Admin, Storage, Decontam, Garten ...) als "offen" erkannt: man sah vom Raum
# aus unter dem Boden den Himmel, die Waende standen als Splitter in der Luft. Offen bleiben nur die Aussenbereiche
# mit gebautem Gelaender (LaunchPad, Balcony); dort haengt unter der Kante eine Schuerze (Turmfassade), damit der
# Blick ueber den Rand nicht ins Leere unter den Boden geht.
# Die Startplattform (MAPCFG floor_add) lag ausserhalb aller Zonen und fiel an "SkyCarpetHall": falsche Wandfarbe,
# Standpunkte im Raketenrumpf. Sie gehoert zum LaunchPad; kleine SkyCarpetHall-Splitter an den Bruecken-Eingaengen
# gehen an den Nachbarraum mit der laengsten gemeinsamen Kante.

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

OPEN_ROOMS = {"LaunchPad", "Balcony"}
SKIRT_D = 14.0                              # Schuerze unter offenen Kanten (Turmfassade), Tiefe
SKIRT_RGB = (196, 199, 206)


# Einrichtung im Ship-Collider (Storage-Regal storageMid 19,02..21,04 / 2,46..3,09): der Grundriss machte daraus eine
# Wand, das gebaute Regal stand dahinter unsichtbar. Der Streifen wird Raumboden, das Regal steht davor im Raum.
FLOOR_ADD_ROOMS = {"Storage": [[(19.0, 2.36), (21.06, 2.36), (21.06, 3.12), (19.0, 3.12)]]}


def adjust(sc):
    for name, polys in FLOOR_ADD_ROOMS.items():
        add = unary_union([Polygon(q) for q in polys]).buffer(0)
        sc.rooms[name] = unary_union([sc.rooms[name], add]).buffer(0)
        for n in sc.rooms:
            if n != name:
                sc.rooms[n] = sc.rooms[n].difference(add).buffer(0)
        sc.floor = unary_union([sc.floor, add]).buffer(0)
        sc.wall_holes = [h.difference(add).buffer(0) for h in sc.wall_holes if not h.difference(add).is_empty]
    pad = unary_union([Polygon(p) for p in sc.cfg.get("floor_add", [])]).buffer(0)
    if not pad.is_empty and "LaunchPad" in sc.rooms:
        for n in list(sc.rooms):
            if n == "LaunchPad":
                continue
            part = sc.rooms[n].intersection(pad).buffer(0)
            if part.is_empty or part.area < 1e-4:
                continue
            sc.rooms[n] = sc.rooms[n].difference(pad).buffer(0)
            sc.rooms["LaunchPad"] = unary_union([sc.rooms["LaunchPad"], part]).buffer(0)
    sch = sc.rooms.get("SkyCarpetHall")
    if sch is not None:
        pieces = list(getattr(sch, "geoms", [sch]))
        if len(pieces) > 1:
            big = max(pieces, key=lambda q: q.area)
            for q in pieces:
                if q is big or q.area < 1e-4:
                    continue
                best = max((n for n in sc.rooms if n != "SkyCarpetHall"),
                           key=lambda n: sc.rooms[n].buffer(0.05).intersection(q.exterior).length)
                sc.rooms[best] = unary_union([sc.rooms[best], q]).buffer(0)
            sc.rooms["SkyCarpetHall"] = big
    sc.rooms = {n: g for n, g in sc.rooms.items() if not g.is_empty and g.area > 1e-4}


def open_edge(sc, a, b, nx, ny):
    """Nur die Aussenbereiche behalten offene Kanten (automatische Erkennung); alle anderen Kanten sind Wand."""
    rooms = getattr(sc, "rooms", None)
    if not rooms:
        return None
    mid = Point((a[0] + b[0]) / 2 + nx * 0.05, (a[1] + b[1]) / 2 + ny * 0.05)
    room = min(rooms, key=lambda n: rooms[n].distance(mid))
    return None if room in OPEN_ROOMS else False


def extra(sc, ctx):
    """Schuerze (Turmfassade) unter allen offenen Kanten."""
    opens = [e for e in sc.wall_edges() if e["kind"] == "open"]
    if not opens:
        return []
    mat = ctx.color("mira_skirt", SKIRT_RGB)
    quads = [{"a": e["a"], "b": e["b"], "n": e["n"], "uv": [0, 0, e["len"], SKIRT_D]} for e in opens]
    return [{"name": "skirt", "coll": "Terrain", "mat": mat, "kind": "wall_side", "quads": quads, "z0": -SKIRT_D, "h": 0.0}]
