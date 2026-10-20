# Polaris Express (Zugkarte, Unknown's Atlas, Fassung 4 vom 19.10.: Hauptebene unten durchgehend, Oberdeck nur ueber den
# drei Doppelstockwagen) - kartenweite Teile.
#
# Die Karte ist im Spiel noch eine Graubox ohne Requisiten; der 3D-Nachbau richtet die 14 Raeume komplett ein
# (Konsolen aus map.json, Vents, Kameras, Tueren, Faltenbaelge, Moebel je Wagen) und gibt Waenden und Boeden
# prozedurale Texturen (rooms/train/_common.py). Alle Ebenen liegen auf z 0: die Nightfall-Kamera folgt dem
# Modellboden, Stufen an den Faltenbaelgen wuerden springen; das Oberdeck bleibt an seiner Kartenlage (8 m suedlich),
# von innen sieht man den Unterschied nicht. Treppen sind im Spiel Teleports (Use-Knopf): Messingschild + Handlauf.

import json
import math
import sys
from pathlib import Path

from shapely.geometry import Polygon, Point, LineString, box as sbox
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import _common as C                                                             # noqa: E402
from bm_spec import box, cyl, lathe, tube, obox, prism, rot3, blob               # noqa: E402
import bm_models as M                                                           # noqa: E402

MAPJSON = Path(__file__).resolve().parents[4] / "UnknownsAtlas" / "assets" / "train" / "map.json"
OL = C.OL

UPPER = {"sleeper", "kitchen", "dome"}                                          # Oberdeck (Band B, y < 0)
# Fassung 4 hat Schlafabteile und Aussichtskuppel ins Oberdeck (Band B) und Gepaeckraum, Telegraf und Dynamo auf die
# Hauptebene (Band A) getauscht. Die Einrichtung unten ist in Weltkoordinaten der alten Baender geschrieben: sie wird
# mit dem alten Raumkasten gebaut und danach um den Bandversatz verschoben.
SHIFT = {"sleeper": -8.0, "dome": -8.0, "luggage": 8.0, "telegraph": 8.0, "dynamo": 8.0}
ROOMS = {}                                                                      # key -> (x0, y0, x1, y1)


def _data():
    return json.loads(MAPJSON.read_text(encoding="utf-8"))


def adjust(sc):
    """Oberdeck (eigener Grundriss suedlich) an den Zug haengen: Boden = Wandumriss aus map.json, Raeume = Zonen."""
    d = _data()
    for r in d["rooms"]:
        xs = [p[0] for p in r["area"]]
        ys = [p[1] for p in r["area"]]
        ROOMS[r["key"]] = (min(xs), min(ys), max(xs), max(ys))
    outlines = [Polygon(p).buffer(0) for p in d["walls"] if len(p) >= 3]
    lower = [o for o in outlines if o.centroid.y < 0 and o.area > 2.0]
    low = unary_union(lower).buffer(0)
    for r in d["rooms"]:
        if r["key"] in UPPER:
            g = Polygon(r["area"]).intersection(low).buffer(0)
            if not g.is_empty:
                sc.rooms[r["key"]] = g
    sc.floor = unary_union([sc.floor, low]).buffer(0)
    sc.auto_z = {}


# ------------------------------------------------------------------------------------------- Hilfen

def _nearest_wall(sc, x, y):
    """Naechster Punkt der Bodenkontur und Richtung von der Wand in den Raum (S/E/N/W)."""
    pt = Point(x, y)
    best = None
    for g in getattr(sc.floor, "geoms", [sc.floor]):
        for ring in [g.exterior] + list(g.interiors):
            dd = ring.distance(pt)
            if best is None or dd < best[0]:
                q = ring.interpolate(ring.project(pt))
                best = (dd, q.x, q.y)
    dd, qx, qy = best
    dx, dy = x - qx, y - qy
    if abs(dx) > abs(dy):
        fac = "E" if dx > 0 else "W"
    else:
        fac = "N" if dy > 0 else "S"
    return dd, qx, qy, fac


def _consoles(sc, ctx):
    parts = []
    d = _data()
    for key, (x, y) in d["consoles"].items():
        kind = key.split("/")[1]
        floor_kinds = ("MedScanner", "gasCanConsole", "FuelEngineConsole", "SwipeCardConsole", "MedBayConsole",
                       "ChartCourseConsole", "WeaponConsole", "StabilizeSteeringConsole", "ShieldConsole")
        dd, qx, qy, fac = _nearest_wall(sc, x, y)
        if kind in floor_kinds:
            parts += C.console(ctx, key, x, y, facing=fac if dd < 1.2 else "S", wall=False)
            continue
        if dd < 0.9:
            o = {"S": (0, -0.02), "N": (0, 0.02), "E": (0.02, 0), "W": (-0.02, 0)}[fac]
            parts += C.console(ctx, key, qx + o[0], qy + o[1], facing=fac, wall=True)
        else:
            parts += C.console(ctx, key, x, y, facing="S", wall=False)
    return parts


def _vents_cams(sc, ctx):
    parts = []
    d = _data()
    for k, (x, y) in d["vents"].items():
        parts += M.vent_grate(ctx, f"tv_vent{k}", x - 0.38, y - 0.28, x + 0.38, y + 0.28, z=0.0, rgb=(74, 70, 66), slots=6)
    for i, (x, y) in enumerate(d["cameras"]):
        parts += M.camera_dome(ctx, f"tv_cam{i}", x, y, C.H - 0.08, yaw=0.0)
    return parts


def _doors(sc, ctx):
    parts = []
    d = _data()
    for v in d["verticalDoors"]:
        if v["label"].endswith("-part"):
            parts += C.door_frame(ctx, "tv_door_" + v["label"], v["x"], v["y"], v["length"], along="y", slide=0.7, rgb=C.STEEL_D)
    for hd in d["horizontalDoors"]:
        parts += C.door_frame(ctx, "tv_hdoor_" + hd["label"], hd["x"], hd["y"], hd["length"], along="x", slide=0.55,
                              rgb=C.WALNUT if "tender" not in hd["label"] else C.STEEL_D)
    for h in d["hallways"]:
        xs = [p[0] for p in h]
        ys = [p[1] for p in h]
        parts += C.bellows(ctx, "tv_bellow", min(xs), max(xs), min(ys), max(ys))
    return parts


def _stairs(sc, ctx):
    parts = []
    d = _data()
    for i, st in enumerate(d["stairs"]):
        ax, ay = st["a"]
        bx, by = st["b"]
        parts += C.stairs_sign(ctx, f"tv_stairs{i}a", ax, ay + 0.24, "S", "UPPER DECK")       # Absatz unten: hinauf
        parts += C.stairs_sign(ctx, f"tv_stairs{i}b", bx, by + 0.24, "S", "LOWER DECK")       # Absatz oben: hinab
    return parts


def _ticket(sc, ctx):
    """Fahrkarten-Lochzangen der Sabotage "Conductor's Round" (map.json "ticket"): Pult mit Messingzange an der Wand."""
    parts = []
    d = _data()
    tk = d.get("ticket")
    if not tk:
        return parts
    wal = ctx.color("tv_tk_wood", C.WALNUT)
    dk = ctx.color("tv_tk_dark", C.WALNUT_D)
    br = ctx.color("train_brass", C.BRASS)
    for i, (x, y) in enumerate(tk["stations"]):
        dd, qx, qy, fac = _nearest_wall(sc, x, y)
        if dd < 0.9:                                                     # an die Wand ruecken
            o = {"S": (0, -0.22), "N": (0, 0.22), "E": (0.22, 0), "W": (-0.22, 0)}[fac]
            x, y = qx + o[0], qy + o[1]
        parts.append(box(x, y, 0.5, 0.36, 0.0, 0.92, wal, bevel=0.02, outline=OL))
        parts.append(box(x, y, 0.54, 0.4, 0.92, 0.96, dk, outline=OL))
        parts.append(box(x, y, 0.3, 0.2, 0.96, 1.02, br, outline=OL))                        # Zangenfuss
        parts.append(obox((x, y, 1.08), (0.28, 0.06, 0.03), br, pitch=-18.0))                 # Hebel
        parts.append(cyl(x + 0.1, y, 0.03, 1.0, 1.06, br, seg=8))                             # Stempelkopf
        parts.append(box(x - 0.12, y, 0.14, 0.09, 1.02, 1.012, ctx.color("tv_tk_ticket", (236, 212, 150)), rot=8.0))
        # Messingschild "TICKETS" an der Wand ueber dem Pult
        im = C.Image.new("RGB", (320, 110), C.BRASS)
        dr = C.ImageDraw.Draw(im)
        dr.rectangle([6, 6, 313, 103], outline=(90, 70, 30), width=4)
        dr.text((160, 55), "TICKETS", fill=(50, 38, 20), font=C.font(40), anchor="mm")
        b = M.screen_panel(ctx, f"tv_tk_sign{i}", qx, qy, 1.25, 1.49, 0.7, fac, None, C.BRASS, depth=0.02, glow=0.0)
        b[{"S": "front", "N": "face_n", "E": "face_e", "W": "face_w"}[fac]] = ctx.tex(f"tv_tk_sign{i}", im, uv="part")
        b["mat"] = br
        parts.append(b)
    return parts


def _wheel(ctx, name, cx, cy, z, r, mat, spokes=6):
    """Waagerechtes Handrad: Kranz als geschlossenes Rohr, Speichen, Nabe."""
    ring = [(cx + r * math.cos(a * math.pi / 8), cy + r * math.sin(a * math.pi / 8), z) for a in range(17)]
    out = [tube(ring, 0.025, mat, seg=8, outline=OL)]
    for k in range(spokes):
        a = k * 2 * math.pi / spokes
        out.append(tube([(cx, cy, z), (cx + r * math.cos(a), cy + r * math.sin(a), z)], 0.012, mat, seg=6))
    out.append(cyl(cx, cy, 0.05, z - 0.03, z + 0.03, mat, seg=12, outline=OL))
    return out


def _runaway_smoke(ctx):
    """Stationen von "Runaway Train" (Dampfbremse im Fuehrerstand, Handbremse auf der Plattform) und "Smoke in the Cars"
    (drei Rauchklappen in der Decke mit herabhaengender Kurbel), Lagen aus map.json wie die 2D-Objekte (train_props)."""
    parts = []
    d = _data()
    iron = ctx.color("tv_iron", (54, 56, 62))
    br = ctx.color("train_brass", C.BRASS)
    red = ctx.color("tv_brake_red", (190, 40, 40))
    rw = d.get("runaway")
    if rw:
        bx, by = rw["brake"]
        cy = by + 0.3                                                    # 2D: Standlinie an der Station, 0,6 m tief
        parts.append(box(bx, cy, 0.7, 0.5, 0.0, 0.06, iron, bevel=0.01, outline=OL))      # Fussplatte
        parts.append(box(bx, cy + 0.1, 0.16, 0.16, 0.06, 0.95, iron, bevel=0.02, outline=OL))   # Saeule
        parts.append(box(bx, cy + 0.1, 0.5, 0.06, 0.8, 1.05, ctx.color("tv_quadrant", (70, 72, 80)), outline=OL))   # Quadrant
        parts.append(box(bx, cy + 0.06, 0.46, 0.012, 0.83, 1.02, br))                    # Messingskala
        parts.append(obox((bx + 0.1, cy - 0.02, 1.12), (0.04, 0.04, 0.36), iron, pitch=28.0))   # Hebel, zur Seite gelegt
        parts.append(cyl(bx + 0.015, cy - 0.02, 0.045, 1.26, 1.35, red, seg=10, outline=OL))     # Griff am oberen Hebelende
        parts.append(cyl(bx - 0.2, cy + 0.06, 0.08, 1.05, 1.1, br, seg=16, outline=OL))   # Manometer
        hx, hy = rw["handbrake"]
        cy = hy + 0.3
        parts.append(box(hx, cy, 0.6, 0.5, 0.0, 0.05, iron, bevel=0.01, outline=OL))
        parts.append(cyl(hx, cy, 0.05, 0.05, 1.0, iron, seg=12, outline=OL))             # Spindel
        parts.append(cyl(hx, cy, 0.09, 0.15, 0.3, ctx.color("tv_ratchet", (80, 82, 90)), seg=12, outline=OL))   # Ratsche
        parts += _wheel(ctx, "tv_handbrake", hx, cy, 1.02, 0.3, br)
        parts.append(cyl(hx + 0.3, cy, 0.03, 1.02, 1.14, ctx.color("tv_knob", C.WALNUT_D), seg=8))
    sm = d.get("smoke")
    if sm:
        for i, (x, y) in enumerate(sm["hatches"]):
            z = C.H
            parts.append(box(x, y, 0.95, 0.75, z - 0.06, z - 0.01, br, outline=OL))      # Rahmen in der Decke
            parts.append(box(x, y, 0.8, 0.6, z - 0.08, z - 0.05, ctx.color("tv_hatch", (90, 94, 100)), outline=OL))   # Deckel
            parts.append(cyl(x, y - 0.25, 0.015, 1.55, z - 0.08, iron, seg=6))           # Kurbelstange
            parts.append(obox((x + 0.08, y - 0.25, 1.55), (0.18, 0.03, 0.03), iron))     # Kurbelarm
            parts.append(cyl(x + 0.17, y - 0.25, 0.025, 1.45, 1.57, ctx.color("tv_knob", C.WALNUT_D), seg=8))
    return parts


def _lamps(sc, ctx):
    parts = []
    for key, (x0, y0, x1, y1) in ROOMS.items():
        n = max(1, int((x1 - x0) / 2.2))
        for i in range(n):
            x = x0 + (x1 - x0) * (i + 0.5) / n
            parts += C.ceiling_lamp(ctx, f"tv_lamp_{key}_{i}", x, (y0 + y1) / 2 + (0.0 if key not in ("sleeper", "tender") else -1.0))
    return parts


# ------------------------------------------------------------------------------------------- Raeume

def _platform(ctx):
    x0, y0, x1, y1 = ROOMS["platform"]
    br = ctx.color("train_brass", C.BRASS)
    out = []
    # Messinggelaender an der Rueckwand (Westen) mit Laterne, Puffer, Schlusslicht
    for y in (y0 + 0.4, y1 - 0.4, (y0 + y1) / 2):
        out.append(cyl(x0 + 0.25, y, 0.02, 0.0, 1.0, br, seg=8))
    out.append(tube([(x0 + 0.25, y0 + 0.4, 1.0), (x0 + 0.25, y1 - 0.4, 1.0)], 0.02, br, seg=8))
    out.append(tube([(x0 + 0.25, y0 + 0.4, 0.5), (x0 + 0.25, y1 - 0.4, 0.5)], 0.015, br, seg=8))
    out.append(box(x0 + 0.25, (y0 + y1) / 2, 0.08, 0.08, 1.0, 1.3, br))
    out.append(lathe(x0 + 0.25, (y0 + y1) / 2, [(0.0, 1.3), (0.08, 1.3), (0.08, 1.5), (0.0, 1.56)], ctx.glow("tv_taillamp", (255, 80, 60), 2.8), seg=10))
    out += M.bench(ctx, "tv_platform_bench", x0 + 0.5, y1 - 0.5, x1 - 0.5, y1 - 0.1, h=0.45, rgb=(150, 108, 66), leg_rgb=C.STEEL_D, slats=4)
    return out


def _office(ctx):
    x0, y0, x1, y1 = ROOMS["office"]
    out = []
    # Zugfuehrerpult an der Nordwand mit Ueberwachungsmonitoren (-24.6, 5.0)
    out += M.security_desk(ctx, "tv_office_desk", -24.6, y1 - 0.45, 2.2, 0.7, h=0.8, screens=3, rgb=(70, 50, 40))
    from bm_spec import office_chair
    out += office_chair(ctx, "tv_office_chair", -24.6, y1 - 1.15, (90, 60, 40), (40, 36, 34), OL, back="S", w=0.5)
    # Aktenschrank Ostwand, Kleiderhaken, Wandleuchte
    out += M.locker_row(ctx, "tv_office_cab", x1 - 0.45, y0 + 0.3, x1 - 0.05, y0 + 1.1, h=1.3, n=1, facing="W", rgb=C.WALNUT, dark=C.WALNUT_D)
    out += C.lamp_sconce(ctx, "tv_office_lamp", x0 + 0.6, y1 - 0.02, 1.25, "S")
    out += M.table(ctx, "tv_office_t", x0 + 0.3, y0 + 0.3, x0 + 1.1, y0 + 0.9, h=0.75, top_rgb=C.WALNUT, leg_rgb=C.WALNUT_D)
    out += M.laptop(ctx, "tv_office_lt", x0 + 0.7, y0 + 0.6, 0.75, yaw=10.0, w=0.3)
    return out


def _sleeper(ctx):
    x0, y0, x1, y1 = ROOMS["sleeper"]
    out = []
    # Zwei Abteile (x -19.5..-17.5, -17.3..-15.3; y 3.2..5.2): Etagenbett an der Nordwand, Klapptisch, Lampe
    for i, (ax0, ax1) in enumerate(((-19.5, -17.5), (-17.3, -15.3))):
        out += C.bunk(ctx, f"tv_bunk{i}", ax0 + 0.15, y1 - 0.65, ax1 - 0.15, y1 - 0.05, head="W")
        out += M.table(ctx, f"tv_abt_t{i}", ax0 + 0.5, 3.3, ax1 - 0.5, 3.75, h=0.7, top_rgb=C.WALNUT, leg_rgb=C.WALNUT_D)
        out += C.lamp_sconce(ctx, f"tv_abt_lamp{i}", (ax0 + ax1) / 2, y1 - 0.02, 1.25, "S")
        out.append(box((ax0 + ax1) / 2, 3.52, 0.3, 0.22, 0.7, 0.705, ctx.color("tv_ticket", (236, 232, 220)), rot=12.0))
    # Gang (y 1..2.7): Klappsitze an der Suedwand, Gepaeckablage
    for x in (-20.6, -16.4, -14.2):
        out += C.seat_bench(ctx, f"tv_sl_seat{x}", x - 0.3, y0 + 0.05, x + 0.3, y0 + 0.5, back="S", rgb=C.GREEN, h=0.45, back_h=0.4)
    out.append(box((x0 + x1) / 2, y0 + 0.2, x1 - x0 - 0.6, 0.35, 1.45, 1.48, ctx.color("tv_rack", C.BRASS)))
    for x in (-20.5, -18.0, -16.0, -14.0):
        out.append(tube([(x, y0 + 0.02, 1.3), (x, y0 + 0.38, 1.47)], 0.012, ctx.color("train_brass", C.BRASS), seg=6))
    out += C.crate(ctx, "tv_sl_case", -18.0, y0 + 0.2, 0.5, 0.3, 0.2, rgb=(90, 60, 40), z0=1.48)
    return out


def _luggage(ctx):
    x0, y0, x1, y1 = ROOMS["luggage"]
    out = []
    # Zwei Gepaeckkaefige (Gitter) an der Nordseite, Koffer- und Kistenstapel, Sackkarre
    steel = ctx.color("tv_cage", (120, 124, 132))
    for i, (ax0, ax1) in enumerate(((-19.5, -17.5), (-17.3, -15.3))):
        for x in (ax0 + 0.1, ax1 - 0.1):
            for k in range(6):
                out.append(box(x, y1 - 0.3 - k * 0.45, 0.02, 0.02, 0.0, 1.6, steel))
        for z in (0.5, 1.0, 1.55):
            out.append(tube([(ax0 + 0.1, y1 - 0.3, z), (ax0 + 0.1, y1 - 2.55, z)], 0.01, steel, seg=4))
            out.append(tube([(ax1 - 0.1, y1 - 0.3, z), (ax1 - 0.1, y1 - 2.55, z)], 0.01, steel, seg=4))
        out += M.crate_stack(ctx, f"tv_lug_c{i}", (ax0 + ax1) / 2, y1 - 0.7, 0.8, 0.5, n=2, rgb=(150, 108, 66), dark=(95, 62, 36), seed=i)
        out += C.crate(ctx, f"tv_lug_trunk{i}", (ax0 + ax1) / 2 - 0.5, y1 - 1.6, 0.7, 0.45, 0.4, rgb=(80, 50, 40), rot=-8.0)
        out += C.crate(ctx, f"tv_lug_trunk{i}b", (ax0 + ax1) / 2 + 0.4, y1 - 1.7, 0.6, 0.4, 0.35, rgb=(60, 70, 90), rot=12.0)
    out += M.crate_stack(ctx, "tv_lug_c3", x1 - 1.0, y0 + 0.6, 0.9, 0.55, n=2, seed=7)
    out += M.crate_stack(ctx, "tv_lug_c4", x0 + 1.0, y0 + 0.6, 0.7, 0.5, n=1, seed=8)
    # Sackkarre
    out.append(obox((x0 + 2.2, y0 + 0.5, 0.6), (0.5, 0.04, 1.1), steel, roll=-20.0))
    out.append(obox((x0 + 2.2, y0 + 0.3, 0.05), (0.5, 0.35, 0.03), steel))
    out.append(lathe(x0 + 1.98, y0 + 0.52, [(0.0, 0.1), (0.12, 0.1), (0.12, 0.14), (0.0, 0.14)], steel, seg=12, tilt=(90.0, 0.0, 0.12)))
    return out


def _dining(ctx):
    x0, y0, x1, y1 = ROOMS["dining"]
    out = []
    # Sitznischen genau auf den Collidern (je 1,2 m breit: Bank 0,28 | Tisch 0,64 | Bank 0,28), Nordseite 3 (y 4,6..5,5),
    # Suedseite 4 (y 1,0..1,9); vorher ragten die Baenke 0,5 m ueber die 2D-Nischen hinaus (20.10.)
    for cx in (-9.0, -7.3, -5.6):
        out += M.table(ctx, f"tv_dt_n{cx}", cx - 0.32, 4.65, cx + 0.32, 5.4, h=0.75, top_rgb=(236, 232, 222), leg_rgb=C.WALNUT_D, pedestal=True)
        out += C.seat_bench(ctx, f"tv_db_n{cx}a", cx - 0.6, 4.6, cx - 0.33, 5.45, back="W", rgb=C.BURGUNDY)
        out += C.seat_bench(ctx, f"tv_db_n{cx}b", cx + 0.33, 4.6, cx + 0.6, 5.45, back="E", rgb=C.BURGUNDY)
        out += _table_setting(ctx, f"tv_ds_n{cx}", cx, 5.0, 0.75, dx=0.14)
    for cx in (-9.8, -8.1, -6.4, -4.7):
        out += M.table(ctx, f"tv_dt_s{cx}", cx - 0.32, 1.1, cx + 0.32, 1.85, h=0.75, top_rgb=(236, 232, 222), leg_rgb=C.WALNUT_D, pedestal=True)
        out += C.seat_bench(ctx, f"tv_db_s{cx}a", cx - 0.6, 1.05, cx - 0.33, 1.9, back="W", rgb=C.BURGUNDY)
        out += C.seat_bench(ctx, f"tv_db_s{cx}b", cx + 0.33, 1.05, cx + 0.6, 1.9, back="E", rgb=C.BURGUNDY)
        out += _table_setting(ctx, f"tv_ds_s{cx}", cx, 1.5, 0.75, dx=0.14)
    # Notfallknopf-Tisch in der Mitte (-7.3, 3.4)
    out += M.table(ctx, "tv_emg_t", -7.85, 2.95, -6.75, 3.85, h=0.8, top_rgb=C.WALNUT, leg_rgb=C.WALNUT_D, pedestal=True, round_=True)
    out.append(cyl(-7.3, 3.4, 0.2, 0.8, 0.86, ctx.color("tv_emg_base", (200, 204, 210)), seg=20, outline=OL))
    out.append(lathe(-7.3, 3.4, [(0.0, 0.86), (0.14, 0.86), (0.15, 0.94), (0.1, 1.0), (0.0, 1.02)], ctx.glow("tv_emg_btn", (230, 50, 50), 1.8), seg=16, outline=OL))
    # Bar am Suedwand-Ostende (Collider -4,0..-3,0 / 1,0..1,6, Atlas 20.10.): Tresen mit Messingleiste, Flaschen, Glaeser
    out += M.kitchen_counter(ctx, "tv_bar", -4.0, 1.0, -3.0, 1.6, h=0.95, rgb=C.WALNUT, top_rgb=(60, 44, 34), stove=None, sink=False, board=False)
    br = ctx.color("train_brass", C.BRASS)
    out.append(tube([(-4.0, 1.66, 0.12), (-3.0, 1.66, 0.12)], 0.018, br, seg=8))
    for i, rgb in enumerate(((70, 120, 60), (150, 90, 40), (120, 30, 40), (200, 190, 150), (60, 90, 130))):
        bx = -3.9 + i * 0.1
        m = ctx.color(f"tv_bottle{i}", rgb)
        out.append(cyl(bx, 1.2, 0.035, 0.95, 1.17, m, seg=10))
        out.append(cyl(bx, 1.2, 0.013, 1.17, 1.25, m, seg=8))
    for i in range(3):
        out.append(cyl(-3.35 + i * 0.1, 1.42, 0.03, 0.95, 1.04, ctx.color("tv_glass", (200, 220, 230)), seg=10))
    return out


def _table_setting(ctx, name, cx, cy, h, dx=0.25):
    out = []
    for dx in (-dx, dx):
        out.append(cyl(cx + dx, cy, 0.1, h, h + 0.008, ctx.color("tv_plate", (240, 240, 236)), seg=16))
        out.append(cyl(cx + dx, cy + 0.17, 0.025, h, h + 0.11, ctx.color("tv_glass", (200, 220, 230)), seg=8))
    out.append(cyl(cx, cy, 0.03, h, h + 0.22, ctx.color("train_brass", C.BRASS), seg=8))
    out.append(lathe(cx, cy, [(0.0, h + 0.2), (0.07, h + 0.22), (0.1, h + 0.32), (0.0, h + 0.34)], ctx.glow("train_lampglass", (255, 226, 170), 2.6), seg=12))
    return out


def _kitchen(ctx):
    x0, y0, x1, y1 = ROOMS["kitchen"]
    out = []
    # Herdzeile Nordwand (Collider -9.6..-5.0 / -3.3..-2.5), Spuele Suedwand (-10.2..-8.0), Regale, Topfhaken, Speiseaufzug
    out += M.kitchen_counter(ctx, "tv_kit_n", -9.6, y1 - 0.75, -5.0, y1 - 0.05, h=0.9, rgb=(120, 126, 134), top_rgb=(170, 176, 184), stove="E", sink=False, board=True)
    out += M.kitchen_counter(ctx, "tv_kit_s", -10.2, y0 + 0.05, -8.0, y0 + 0.7, h=0.9, rgb=(120, 126, 134), top_rgb=(170, 176, 184), stove=None, sink=True, board=False)
    out += M.shelf_unit(ctx, "tv_kit_shelf", x1 - 0.45, y0 + 0.3, x1 - 0.05, y0 + 1.8, h=1.6, boards=3, rgb=(120, 126, 134), items=True, seed=5, facing="W")
    br = ctx.color("train_brass", C.BRASS)
    out.append(tube([(-9.4, y1 - 0.75, 1.5), (-5.2, y1 - 0.75, 1.5)], 0.012, br, seg=6))
    for i, x in enumerate((-9.0, -8.2, -7.4, -6.6, -5.8)):
        out.append(tube([(x, y1 - 0.75, 1.5), (x, y1 - 0.75, 1.4)], 0.005, br, seg=4))
        out.append(lathe(x, y1 - 0.75, [(0.0, 1.2), (0.09, 1.2), (0.1, 1.38), (0.0, 1.4)], ctx.color(f"tv_pot{i % 2}", [(176, 110, 70), (150, 156, 164)][i % 2]), seg=12, outline=OL))
    # Speiseaufzug an der Westwand (Vent 2 bei -7,-6.5 ist der Schacht im Boden; Klappe darueber)
    out.append(box(x0 + 0.08, -4.5, 0.12, 0.9, 0.0, 1.6, ctx.color("tv_dumb", C.WALNUT), outline=OL))
    out.append(box(x0 + 0.15, -4.5, 0.02, 0.7, 0.5, 1.3, ctx.color("tv_dumb_door", (110, 72, 46)), outline=OL))
    out += M.crate_stack(ctx, "tv_kit_crate", x0 + 0.7, y1 - 0.6, 0.5, 0.4, n=2, rgb=(170, 160, 120), seed=4)
    return out


def _dome(ctx):
    x0, y0, x1, y1 = ROOMS["dome"]
    out = []
    # Aussichtswagen: Sitzpaare nach Osten (Fahrtrichtung), Suedseite 3 (Collider 0..1.4 usw.), Nordseite 2
    for i, ax0 in enumerate((0.0, 2.0, 4.0)):
        out += C.seat_bench(ctx, f"tv_dome_s{i}", ax0, y0 + 0.05, ax0 + 1.3, y0 + 0.75, back="W", rgb=C.GREEN, h=0.45, back_h=0.55)
    for i, ax0 in enumerate((1.2, 3.0)):
        out += C.seat_bench(ctx, f"tv_dome_n{i}", ax0, y1 - 0.75, ax0 + 1.2, y1 - 0.05, back="W", rgb=C.GREEN, h=0.45, back_h=0.55)
    # Navigationstisch am Ostende mit Streckenkarte, Messinglampen, Globus
    out += M.map_table(ctx, "tv_nav_map", x1 - 1.4, 2.4, x1 - 0.2, 3.9, h=0.8, rgb=(70, 50, 40), holo=(120, 200, 240), seed=2)
    out += M.potted_plant(ctx, "tv_dome_plant", x0 + 0.4, y1 - 0.4, r=0.14, h=0.7, seed=1)
    out += M.potted_plant(ctx, "tv_dome_plant2", x0 + 0.4, y0 + 0.4, r=0.14, h=0.65, seed=2)
    return out


def _telegraph(ctx):
    x0, y0, x1, y1 = ROOMS["telegraph"]
    out = []
    # Telegrafentisch an der Suedwand mit Morsetaste, Funkgestell Westwand, Kopfhoerer, Papierrollen
    out += M.table(ctx, "tv_tel_t", x0 + 0.5, y0 + 0.1, x0 + 2.3, y0 + 0.8, h=0.78, top_rgb=C.WALNUT, leg_rgb=C.WALNUT_D)
    br = ctx.color("train_brass", C.BRASS)
    out.append(box(x0 + 1.0, y0 + 0.45, 0.2, 0.14, 0.78, 0.82, ctx.color("tv_key_base", (60, 44, 34))))
    out.append(obox((x0 + 1.0, y0 + 0.45, 0.86), (0.12, 0.02, 0.01), br, roll=8.0))
    out.append(cyl(x0 + 1.06, y0 + 0.45, 0.015, 0.86, 0.9, br, seg=8))
    out.append(cyl(x0 + 1.7, y0 + 0.45, 0.08, 0.78, 0.86, ctx.color("tv_tape", (236, 232, 220)), seg=14))
    out.append(tube([(x0 + 1.7, y0 + 0.45, 0.86), (x0 + 2.5, y0 + 0.2, 0.8), (x0 + 2.8, y0 + 0.3, 0.02)], 0.03, ctx.color("tv_tape", (236, 232, 220)), seg=6))
    out += M.shelf_unit(ctx, "tv_tel_rack", x0 + 0.05, y0 + 1.2, x0 + 0.5, y1 - 0.3, h=1.6, boards=3, rgb=(70, 72, 80), items=False, seed=1, facing="E")
    for i in range(3):
        z = 0.08 + 1.52 * (i + 0.2) / 3
        out.append(box(x0 + 0.27, y0 + 1.6 + i * 0.3, 0.36, 0.5, z + 0.02, z + 0.3, ctx.color("tv_radio", (56, 58, 64)), bevel=0.01, outline=OL))
        out.append(box(x0 + 0.47, y0 + 1.6 + i * 0.3, 0.012, 0.3, z + 0.1, z + 0.22, ctx.glow(f"tv_radio_dial{i}", (120, 200, 160), 1.3)))
    from bm_spec import office_chair
    out += office_chair(ctx, "tv_tel_chair", x0 + 1.2, y0 + 1.3, (90, 60, 40), (40, 36, 34), OL, back="N", w=0.46)
    return out


def _dynamo(ctx):
    x0, y0, x1, y1 = ROOMS["dynamo"]
    out = []
    # Dynamo (Collider 3.4..4.6 / -6.4..-5.2): Generator mit Riemenscheibe, Schaltkasten, Kabel, Sicherungen
    st = ctx.color("tv_dyn_steel", C.STEEL)
    dk = ctx.color("tv_dyn_dark", C.STEEL_D)
    cx, cy = 4.0, -5.8
    out.append(box(cx, cy, 1.2, 1.2, 0.0, 0.3, dk, outline=OL))
    out.append(lathe(cx, cy, [(0.0, 0.28), (0.45, 0.28), (0.45, 1.28), (0.0, 1.28)], ctx.color("tv_dyn_body", (60, 90, 70)), seg=24, outline=OL, tilt=(90.0, 90.0, 0.78)))
    for yy in (cy - 0.52, cy + 0.52):
        out.append(lathe(cx, yy, [(0.0, 0.75), (0.5, 0.75), (0.5, 0.81), (0.0, 0.81)], st, seg=24, outline=OL, tilt=(90.0, 90.0, 0.78)))
    out.append(lathe(cx, cy + 0.62, [(0.0, 0.74), (0.3, 0.74), (0.3, 0.82), (0.0, 0.82)], ctx.color("train_brass", C.BRASS), seg=24, tilt=(90.0, 90.0, 0.78)))
    out.append(obox((cx, cy, 1.3), (0.5, 1.3, 0.04), dk))
    out += M.pipe_run(ctx, "tv_dyn_pipe", [(cx + 0.45, cy, 1.0), (x1 - 0.2, cy, 1.0), (x1 - 0.2, cy, 1.55)], r=0.04, rgb=(110, 120, 130))
    for i, c in enumerate(((230, 70, 60), (80, 220, 90), (240, 200, 70))):
        out.append(cyl(cx - 0.3 + i * 0.3, cy - 0.62, 0.02, 1.0, 1.03, ctx.glow(f"tv_dyn_led{i}", c, 2.0), seg=6))
    return out


def _generator(ctx):
    x0, y0, x1, y1 = ROOMS["generator"]
    out = []
    # Generatorblock (Collider 8.8..10.6 / 4.2..5.5): Motor mit Zylinderkoepfen, Auspuff, Kanister, Werkzeugbrett
    out += M.container(ctx, "tv_gen_block", 8.85, 4.25, 10.55, 5.45, 0.9, rgb=(60, 90, 70), ribs=False, doors=None)
    for i in range(4):
        out.append(cyl(9.1 + i * 0.4, 4.85, 0.14, 0.9, 1.15, ctx.color("tv_gen_cyl", C.STEEL), seg=14, outline=OL))
    out.append(tube([(10.5, 4.85, 1.1), (10.9, 4.85, 1.1), (10.9, 4.85, 1.72)], 0.05, ctx.color("tv_gen_exh", C.STEEL_D), seg=8))
    out.append(lathe(9.3, 4.4, [(0.0, 0.9), (0.2, 0.9), (0.22, 1.2), (0.0, 1.2)], ctx.color("tv_gen_tank", (190, 60, 50)), seg=14, outline=OL))
    for i in range(3):
        out.append(box(x0 + 0.35 + i * 0.3, y0 + 0.3, 0.24, 0.18, 0.0, 0.4, ctx.color("tv_gen_can", (190, 60, 50)), bevel=0.01, outline=OL))
    out.append(box(x1 - 0.1, 2.0, 0.04, 1.2, 0.9, 1.5, ctx.color("tv_gen_board", (150, 108, 66)), outline=OL))
    for i in range(4):
        out.append(tube([(x1 - 0.12, 1.6 + i * 0.3, 1.4), (x1 - 0.12, 1.6 + i * 0.3, 1.0)], 0.012, ctx.color("tv_gen_tool", C.STEEL_D), seg=6))
    return out


def _mail(ctx):
    x0, y0, x1, y1 = ROOMS["mail"]
    out = []
    # Sortierregal Suedwand (Collider 12..14.6 / 1..1.4), Posttisch, Saecke, Admin-Kartentisch Nordwand (13.25, 4.8)
    out += M.shelf_unit(ctx, "tv_mail_rack", 12.0, y0 + 0.05, 14.6, y0 + 0.45, h=1.6, boards=5, rgb=C.WALNUT, items=False, seed=2, facing="N")
    for r in range(4):
        for c in range(6):
            z = 0.08 + 1.5 * (r + 0.2) / 5
            out.append(box(12.25 + c * 0.42, y0 + 0.25, 0.3, 0.25, z + 0.02, z + 0.14, ctx.color(f"tv_mail_p{(r + c) % 3}", [(236, 232, 220), (220, 200, 160), (200, 190, 170)][(r + c) % 3]), outline=OL))
    out += M.map_table(ctx, "tv_admin", 12.4, 5.0, 14.1, 5.5, h=0.8, rgb=(70, 50, 40), holo=(120, 200, 120), seed=3)   # Collider Atlas 20.10.
    for i, (x, y) in enumerate(((x0 + 0.5, 2.6), (x0 + 0.9, 3.1), (x0 + 0.4, 3.4))):
        out.append(blob(x, y, 0.0, 0.25, 0.22, 0.5, (ctx.color("tv_sack", (170, 150, 110)), ctx.color("tv_sack_d", (130, 112, 80))), seed=i, seg=10, rings=5, outline=OL))
    out += M.table(ctx, "tv_mail_t", 11.8, 2.0, 12.9, 2.6, h=0.78, top_rgb=C.WALNUT, leg_rgb=C.WALNUT_D)
    out.append(box(12.35, 2.3, 0.25, 0.2, 0.78, 0.9, ctx.color("tv_stamp", (60, 44, 34))))
    return out


def _tender(ctx):
    x0, y0, x1, y1 = ROOMS["tender"]
    out = []
    # Kohlenbunker (y 2.4..5.2) hinter den Luken: Kohlehaufen, Schaufel; Gang (y 1..2.4) mit Rohren, Wasserhahn
    coal = (ctx.color("tv_coal", (36, 34, 36)), ctx.color("tv_coal_d", (24, 22, 24)))
    out.append(blob(18.2, 4.6, 0.0, 1.5, 0.9, 1.1, coal, seed=3, seg=18, rings=7, outline=OL))
    out.append(blob(17.2, 3.6, 0.0, 0.6, 0.5, 0.5, coal, seed=4, seg=12, rings=5))
    out.append(blob(19.4, 3.5, 0.0, 0.5, 0.45, 0.45, coal, seed=5, seg=12, rings=5))
    out.append(tube([(17.0, 3.2, 0.3), (17.4, 3.6, 0.9)], 0.015, ctx.color("tv_shaft", (150, 108, 66)), seg=6))
    out.append(obox((16.95, 3.15, 0.25), (0.18, 0.24, 0.015), ctx.color("tv_blade", C.STEEL), yaw=20.0, pitch=50.0))
    out += M.pipe_run(ctx, "tv_tender_pipe", [(x0 + 0.1, 1.2, 1.5), (x1 - 0.1, 1.2, 1.5)], r=0.05, rgb=(110, 120, 130))
    out += M.pipe_run(ctx, "tv_tender_pipe2", [(x0 + 0.1, 1.1, 1.35), (x1 - 0.1, 1.1, 1.35)], r=0.03, rgb=(140, 100, 70))
    out.append(lathe(18.3, 1.08, [(0.0, 1.15), (0.05, 1.15), (0.05, 1.25), (0.0, 1.25)], ctx.color("tv_valve", (190, 40, 40)), seg=10, tilt=(90.0, 90.0, 1.2)))
    return out


def _cab(ctx):
    x0, y0, x1, y1 = ROOMS["cab"]
    out = []
    # Fuehrerstand: Kesselrueckwand (Stehkessel) an der Ostwand mit Feuertuer, Manometern, Ventilen, Regler
    st = ctx.color("tv_cab_steel", (70, 72, 80))
    br = ctx.color("train_brass", C.BRASS)
    out.append(box(x1 - 0.3, (y0 + y1) / 2, 0.6, y1 - y0 - 0.4, 0.0, C.H, st, bevel=0.03, outline=OL))
    out.append(box(x1 - 0.62, (y0 + y1) / 2, 0.06, 0.7, 0.35, 0.95, ctx.color("tv_firedoor", (90, 80, 76)), outline=OL))
    out.append(box(x1 - 0.65, (y0 + y1) / 2, 0.012, 0.5, 0.45, 0.85, ctx.glow("tv_fire", (255, 150, 60), 2.6)))
    for i, yy in enumerate((2.0, 2.8, 3.7, 4.5)):
        out.append(lathe(x1 - 0.61, yy, [(0.0, 1.28), (0.1, 1.28), (0.1, 1.3), (0.0, 1.3)], ctx.color("tv_gauge", (236, 232, 220)), seg=16, outline=OL, tilt=(90.0, 0.0, 1.3)))
        out.append(box(x1 - 0.64, yy, 0.006, 0.012, 1.3, 1.38, ctx.color("tv_needle", (30, 30, 30))))
    for yy in (2.4, 4.1):
        out.append(lathe(x1 - 0.62, yy, [(0.0, 0.93), (0.08, 0.93), (0.08, 0.97), (0.0, 0.97)], ctx.color("tv_valve", (190, 40, 40)), seg=12, outline=OL, tilt=(90.0, 0.0, 0.95)))
        out.append(tube([(x1 - 0.64, yy, 0.95), (x1 - 0.85, yy, 0.95)], 0.012, br, seg=6))
    out.append(tube([(x1 - 0.62, 3.25, 1.5), (x1 - 1.1, 3.25, 1.3)], 0.02, br, seg=8))                  # Regler
    out.append(lathe(x1 - 1.1, 3.25, [(0.0, 1.26), (0.03, 1.28), (0.03, 1.34), (0.0, 1.36)], ctx.color("tv_knob", (60, 40, 30)), seg=8))
    # Nordsitz entfaellt: dort steht seit 20.10. die Dampfbremse von "Runaway Train" (map.json runaway.brake)
    out += M.bench(ctx, "tv_cab_seat2", x0 + 0.1, y0 + 0.1, x0 + 0.6, y0 + 0.6, h=0.55, rgb=(90, 60, 40), leg_rgb=C.STEEL_D)
    out.append(tube([(x0 + 0.2, 1.4, 0.7), (x0 + 0.2, 1.4, 1.2), (x0 + 0.5, 1.4, 1.3)], 0.014, br, seg=6))
    out.append(lathe(x0 + 0.5, 1.4, [(0.0, 1.3), (0.06, 1.32), (0.07, 1.42), (0.0, 1.44)], ctx.glow("train_lampglass", (255, 226, 170), 2.6), seg=10))
    return out


def _boards(ctx):
    x0, y0, x1, y1 = ROOMS["boards"]
    out = []
    # Umlauf um den Kessel: Kessel als liegender Zylinder (Block 24.7..28.0 / 2.4..4.0) mit Rauchkammer, Schornstein,
    # Dampfdom, Laufbretter, Handlauf, Stirnlampe
    st = ctx.color("tv_boiler", (50, 52, 58))
    br = ctx.color("train_brass", C.BRASS)
    cy, r = 3.2, 0.78
    out.append(lathe(26.35, cy, [(0.0, 0.85 - 1.65), (r, 0.85 - 1.65), (r, 0.85 + 1.65), (0.0, 0.85 + 1.65)], st, seg=28, outline=OL, tilt=(90.0, 0.0, 0.85)))
    for x in (25.2, 26.3, 27.4):
        out.append(lathe(x, cy, [(r * 0.99, 0.82), (r * 1.03, 0.82), (r * 1.03, 0.88), (r * 0.99, 0.88)], br, seg=28, tilt=(90.0, 0.0, 0.85)))
    out.append(lathe(28.05, cy, [(0.0, 0.79), (r * 1.05, 0.79), (r * 1.05, 0.91), (0.0, 0.91)], ctx.color("tv_smokebox", (40, 40, 44)), seg=28, outline=OL, tilt=(90.0, 0.0, 0.85)))
    out.append(cyl(27.7, cy, 0.18, 0.85 + r, 0.85 + r + 0.55, st, seg=16, outline=OL))                   # Schornstein
    out.append(lathe(27.7, cy, [(0.18, 0.85 + r + 0.55), (0.26, 0.85 + r + 0.62), (0.0, 0.85 + r + 0.7)], br, seg=16))
    out.append(lathe(25.6, cy, [(0.0, 0.85 + r - 0.1), (0.28, 0.85 + r - 0.05), (0.26, 0.85 + r + 0.25), (0.0, 0.85 + r + 0.3)], st, seg=16, outline=OL))  # Dampfdom
    zl = 0.85 + r * 0.5
    out.append(lathe(28.12, cy, [(0.0, zl - 0.11), (0.1, zl - 0.11), (0.12, zl + 0.09), (0.0, zl + 0.11)], ctx.glow("tv_headlamp", (255, 240, 200), 3.0), seg=12, tilt=(-90.0, 0.0, zl)))
    for yy in (y0 + 0.12, y1 - 0.12):
        out.append(tube([(x0 + 0.1, yy, 0.95), (x1 - 0.1, yy, 0.95)], 0.02, br, seg=8))
        for x in (x0 + 0.3, 26.0, 27.5, x1 - 0.3):
            out.append(cyl(x, yy, 0.02, 0.0, 0.95, br, seg=8))
    for i in range(3):
        out.append(blob(27.7 + i * 0.1, cy, 0.85 + r + 0.9 + i * 0.3, 0.2 + i * 0.1, 0.2 + i * 0.1, 0.25, (ctx.color("tv_smoke", (200, 200, 210)), ctx.color("tv_smoke", (200, 200, 210))), seed=i, seg=8, rings=4))
    return out


def extra(sc, ctx):
    if not ROOMS:
        adjust_rooms_only()
    parts = []
    for fn in (_platform, _office, _sleeper, _luggage, _dining, _kitchen, _dome, _telegraph, _dynamo, _generator, _mail, _tender, _cab, _boards):
        key = fn.__name__[1:]
        dy = SHIFT.get(key, 0.0)
        try:
            if dy:
                x0, y0, x1, y1 = ROOMS[key]
                ROOMS[key] = (x0, y0 - dy, x1, y1 - dy)                   # alter Raumkasten fuer die Einrichtung
                try:
                    parts += _shift(fn(ctx), dy)
                finally:
                    ROOMS[key] = (x0, y0, x1, y1)
            else:
                parts += fn(ctx)
        except Exception:
            import traceback
            traceback.print_exc()
    parts += _consoles(sc, ctx)
    parts += _ticket(sc, ctx)
    parts += _runaway_smoke(ctx)
    parts += _vents_cams(sc, ctx)
    parts += _doors(sc, ctx)
    parts += _stairs(sc, ctx)
    parts += _lamps(sc, ctx)
    return [{"name": "train_interior", "coll": "Props", "kind": "parts", "parts": parts}]


def _shift(parts, dy):
    """Fertige Teile (prism/mesh/lathe/tube) um dy nach Norden verschieben."""
    out = []
    for q in parts:
        q = dict(q)
        t = q.get("type")
        if t == "prism":
            q["pts"] = [(p[0], p[1] + dy) for p in q["pts"]]
        elif t == "mesh":
            q["verts"] = [(v[0], v[1] + dy, v[2]) for v in q["verts"]]
        elif t == "lathe":
            q["c"] = (q["c"][0], q["c"][1] + dy)
        elif t == "tube":
            q["pts"] = [(p[0], p[1] + dy, p[2]) for p in q["pts"]]
        else:
            raise ValueError(f"unbekannter Teiletyp {t}")
        out.append(q)
    return out


def adjust_rooms_only():
    d = _data()
    for r in d["rooms"]:
        xs = [p[0] for p in r["area"]]
        ys = [p[1] for p in r["area"]]
        ROOMS[r["key"]] = (min(xs), min(ys), max(xs), max(ys))
