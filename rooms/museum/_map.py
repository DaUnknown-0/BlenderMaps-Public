# museum (eigene Karte) - Requisiten aus den Sprites des Spiels, Grundriss = Collider (rooms/_atlas_props.py).
#
# T-Rex in der Rotunde eigens gebaut (Hinweis User 17.10.: "Der T-Rex ragt mit dem Kopf in die Decke, das Podest
# ist nicht gut geworden"):
#   Podest wie museum_art "dino": Ellipse um (0,5 | 4,0), rx 2,7, ry 0,9 (Oberseite in voller Tiefe), Hoehe 0,55;
#     Stein lift(#5a5650, 1,65) = (148,141,132), Fussband shade 0,7, Deckkante shade 1,18 mit heller Innenlinie,
#     Sandbett lift(#8a7048, 1,45) = (200,162,104) rx 2,28 ry 0,6 mit Grabungsraster und Steinen, Messingplakette
#     "T. REX" an der Front, Absperrung: Messingpfosten (#c9a24c) 0,9 hoch auf Ellipse rx 2,5 ry 0,76 bei 15..165
#     und 195..345 Grad (je 30), Kordel lift(#7a1e2e, 1,4) mit Durchhang.
#   Skelett: Umriss der drei Sprites (Rumpf, Kopf, Unterkiefer) als Scheibe mit Durchbruechen (Knochen einzeln
#     sichtbar), Bild beidseitig. Die Zeichnung stellt das Skelett senkrecht ueber der Podestmitte (y 4,0) dar:
#     Hoehe z = (Bild-y - 4,0) / K. Kopfoberkante damit 6,7; die Rotunde bekommt 7,8 Raumhoehe.

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _atlas_props as AP                                                         # noqa: E402
from bm_spec import obox, tooth, rot3 as _rot                                     # noqa: E402

K = 0.55
CX, CY, RX, RY, ZT = 0.5, 4.0, 2.7, 0.9, 0.55
STONE = (148, 141, 132)
SAND = (200, 162, 104)
BRASS = (201, 162, 76)
ROPE = (170, 42, 64)
BONE_SIDE = (196, 186, 160)
OUT = (14, 16, 20)
REX_H = 6.4


def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _top_texture(ppm=120):
    """Podestoberseite (Weltlage, Grundriss-bbox): Deckkante, Sandbett mit Raster und Steinen."""
    W, H = int(2 * RX * ppm), int(2 * RY * ppm)
    im = Image.new("RGB", (W, H), _shade(STONE, 1.18))
    d = ImageDraw.Draw(im)

    def E(rx, ry, **kw):
        d.ellipse([W / 2 - rx * ppm, H / 2 - ry * ppm, W / 2 + rx * ppm, H / 2 + ry * ppm], **kw)
    E(RX - 0.05, RY - 0.05, outline=_shade(STONE, 1.35), width=max(1, int(0.03 * ppm)))
    srx, sry = RX - 0.42, RY - 0.3
    E(srx, sry, fill=SAND, outline=_shade(SAND, 0.65), width=max(1, int(0.045 * ppm)))
    E(srx - 0.1, sry - 0.08, outline=_shade(SAND, 0.85), width=max(1, int(0.02 * ppm)))
    for gx in np.arange(-2.0, 2.01, 0.5):                               # Grabungsraster (Schnur)
        h = sry * math.sqrt(max(0.0, 1 - (gx / srx) ** 2)) - 0.06
        if h > 0.05:
            d.line([(W / 2 + gx * ppm, H / 2 - h * ppm), (W / 2 + gx * ppm, H / 2 + h * ppm)], fill=_shade(SAND, 0.78), width=2)
    rs = random.Random(3)
    for _ in range(48):
        a, r = rs.uniform(0, 2 * math.pi), math.sqrt(rs.uniform(0, 1))
        sx, sy = (srx - 0.2) * r * math.cos(a), (sry - 0.15) * r * math.sin(a)
        c = _shade(SAND, rs.choice([0.72, 0.85, 1.15, 1.25]))
        d.ellipse([W / 2 + (sx - 0.06) * ppm, H / 2 - (sy + 0.04) * ppm, W / 2 + (sx + 0.06) * ppm, H / 2 - (sy - 0.04) * ppm],
                  fill=c, outline=_shade(SAND, 0.6))
    return im


def _plaque_texture():
    im = Image.new("RGB", (440, 120), (176, 138, 60))
    d = ImageDraw.Draw(im)
    d.rectangle([8, 8, 431, 111], outline=_shade((176, 138, 60), 1.3), width=4)
    try:
        f = ImageFont.truetype("arialbd.ttf", 64)
    except Exception:
        f = ImageFont.load_default()
    d.text((220, 62), "T. REX", fill=(42, 36, 34), font=f, anchor="mm")
    return im


def rex(sc, ctx):
    from shapely.geometry import Point
    from shapely import affinity
    import bm_tex as T
    from bm_spec import box, cyl, lathe, prism, slab, sprite_outline, tube
    parts = []
    ell = affinity.scale(Point(CX, CY).buffer(1.0, 64), RX, RY)
    top = ctx.tex("rex_plinth_top", _top_texture(), uv="bbox", bbox=[CX - RX, CY - RY, CX + RX, CY + RY])
    stone = ctx.color("rex_plinth_stone", STONE)
    parts.append(prism(ell, 0.0, ZT, stone, top=top, outline=OUT))
    foot = ctx.color("rex_plinth_foot", _shade(STONE, 0.7))
    parts.append(prism(affinity.scale(ell, 1.012, 1.03), 0.0, 0.16, foot))
    joint = ctx.color("rex_plinth_joint", _shade(STONE, 0.78))
    for fx in (-2.2, -1.1, 0.0, 1.1, 2.2):                              # Plattenfugen an der Wandung
        yb = CY - RY * math.sqrt(max(0.0, 1 - (fx / RX) ** 2))
        parts.append(box(CX + fx, yb + 0.004, 0.025, 0.02, 0.17, ZT - 0.03, joint))
    pl = ctx.tex("rex_plaque", _plaque_texture(), uv="part")
    pq = box(CX, CY - RY - 0.006, 1.1, 0.02, 0.2, 0.46, ctx.color("rex_plaque_side", (176, 138, 60)))
    pq["front"] = pl
    parts.append(pq)
    # Absperrung
    brass = ctx.color("rex_brass", BRASS)
    rope = ctx.color("rex_rope", ROPE)
    prx, pry = RX - 0.2, RY - 0.14
    for group in (range(15, 166, 30), range(195, 346, 30)):
        pts = [(CX + prx * math.cos(math.radians(a)), CY + pry * math.sin(math.radians(a))) for a in group]
        for x, y in pts:
            parts.append(cyl(x, y, 0.07, ZT, ZT + 0.03, _shade_mat(ctx, "rex_brass_dark", _shade(BRASS, 0.8))))
            parts.append(cyl(x, y, 0.022, ZT + 0.03, ZT + 0.88, brass, seg=12))
            parts.append(lathe(x, y, [(0.0, ZT + 0.86), (0.045, ZT + 0.9), (0.0, ZT + 0.94)], brass, seg=12))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            mx, my = (ax + bx) / 2, (ay + by) / 2
            parts.append(tube([(ax, ay, ZT + 0.84), (mx, my, ZT + 0.64), (bx, by, ZT + 0.84)], 0.018, rope, seg=8))
    # Skelett: echtes 3D-Skelett (User 18.10.: "vor allem der T-Rex"), vorher eine flache Sprite-Scheibe
    parts += rex_skeleton(ctx)
    return parts


# Wirbelsaeule (x, z, Radius) bei y = CY, Kopf nach Westen
SPINE = [(7.3, 3.05, 0.06), (6.2, 3.3, 0.09), (5.0, 3.5, 0.12), (3.8, 3.6, 0.15), (2.5, 3.65, 0.19), (1.2, 3.66, 0.21),
         (0.0, 3.6, 0.2), (-1.2, 3.5, 0.19), (-2.3, 3.45, 0.17), (-3.0, 3.6, 0.15), (-3.55, 3.95, 0.14),
         (-3.95, 4.3, 0.13), (-4.2, 4.45, 0.12)]


def _spine_at(x):
    """z und Radius der Wirbelsaeule an der Stelle x (linear zwischen den Stuetzpunkten)."""
    pts = sorted(SPINE)
    for (x0, z0, r0), (x1, z1, r1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return z0 + t * (z1 - z0), r0 + t * (r1 - r0)
    return pts[0][1], pts[0][2]


def rex_skeleton(ctx):
    from bm_spec import cyl, lathe, tube
    bone = ctx.color("rex_bone", (228, 216, 188))
    bone_d = ctx.color("rex_bone_dark", (202, 188, 158))
    teeth = ctx.color("rex_teeth", (242, 238, 226))
    socket = ctx.color("rex_socket", (38, 32, 28))
    steel = ctx.color("rex_steel", (58, 60, 64))
    OL = (40, 34, 26)
    parts = []
    y = CY
    # Wirbelsaeule: je Abschnitt ein Rohr mit eigenem Radius, darueber die Dornfortsaetze
    for (x0, z0, r0), (x1, z1, r1) in zip(SPINE, SPINE[1:]):
        parts.append(tube([(x0, y, z0), (x1, y, z1)], (r0 + r1) / 2, bone, seg=12, outline=OL))
    x = 7.0
    while x > -4.1:
        z, r = _spine_at(x)
        if x > 1.6:
            fin = 0.18 + 0.12 * (1 - (x - 1.6) / 5.4)                   # Schwanz: kleiner zur Spitze
        elif x > -2.4:
            fin = 0.46                                                    # Rumpf: hohe Dornfortsaetze
        else:
            fin = 0.3                                                     # Hals
        pitch = 0.0 if x > -2.4 else -35.0                               # Halswirbel folgen der Halsbeuge
        parts.append(obox((x, y, z + r * 0.4 + fin / 2), (0.1, 0.07, fin), bone, pitch=pitch, outline=OL))
        parts.append(obox((x, y, z), (0.16, r * 2.3, r * 1.6), bone_d))   # Wirbelkoerper (breiter als das Rohr)
        if 1.8 < x < 6.6:                                                 # Chevrons unter dem Schwanz
            parts.append(obox((x, y, z - r * 0.5 - 0.1), (0.07, 0.05, 0.22), bone_d, pitch=20.0))
        x -= 0.32
    # Rippen
    for i, rx in enumerate([-2.45 + 0.33 * j for j in range(10)]):
        z, r = _spine_at(rx)
        f = 0.7 if i in (0, 9) else (0.88 if i in (1, 8) else 1.0)
        for sgn in (-1, 1):
            pts = [(rx, y + sgn * r * 0.9, z - 0.05), (rx + 0.04, y + sgn * 0.5 * f, z - 0.42 * f),
                   (rx + 0.08, y + sgn * 0.78 * f, z - 1.05 * f), (rx + 0.13, y + sgn * 0.7 * f, z - 1.7 * f),
                   (rx + 0.18, y + sgn * 0.48 * f, z - 2.15 * f)]
            parts.append(tube(pts, 0.045, bone_d, seg=8, outline=OL))
    # Becken mit Darmbeinschaufeln
    hz, _ = _spine_at(1.2)
    parts.append(obox((1.2, y, hz - 0.35), (1.1, 0.5, 0.62), bone, outline=OL))
    for sgn in (-1, 1):
        parts.append(obox((1.25, y + sgn * 0.3, hz - 0.1), (1.7, 0.07, 0.62), bone, outline=OL))
        parts.append(obox((1.0, y + sgn * 0.22, hz - 0.8), (0.35, 0.08, 0.5), bone_d, pitch=25.0))     # Schambein
    # Beine: Oberschenkel, Schienbein, Mittelfuss, drei Zehen; Gelenkkugeln
    for sgn in (-1, 1):
        hip = (1.15, y + sgn * 0.42, hz - 0.45)
        knee = (0.55, y + sgn * 0.6, 2.0)
        ankle = (1.3, y + sgn * 0.64, 0.98)
        foot = (1.18, y + sgn * 0.64, ZT + 0.07)
        parts.append(tube([hip, knee], 0.13, bone, seg=12, outline=OL))
        parts.append(tube([knee, ankle], 0.1, bone, seg=12, outline=OL))
        parts.append(tube([ankle, foot], 0.08, bone, seg=10, outline=OL))
        for px, pr in ((knee, 0.17), (ankle, 0.13)):
            pz = px[2]
            parts.append(lathe(px[0], px[1], [(0.0, pz - pr), (pr * 0.8, pz - pr * 0.55), (pr, pz), (pr * 0.8, pz + pr * 0.55),
                                              (0.0, pz + pr)], bone, seg=14))
        for d in (-0.26, 0.0, 0.26):
            tip = (0.5 if d == 0.0 else 0.62, y + sgn * 0.64 + d, ZT + 0.04)
            parts.append(tube([foot, tip], 0.045, bone_d, seg=8, outline=OL))
    # Aermchen
    for sgn in (-1, 1):
        sh = (-2.0, y + sgn * 0.42, 3.02)
        el = (-2.45, y + sgn * 0.52, 2.6)
        ha = (-2.8, y + sgn * 0.52, 2.48)
        parts.append(tube([sh, el, ha], 0.045, bone_d, seg=8, outline=OL))
        parts.append(obox((-2.1, y + sgn * 0.48, 2.95), (0.75, 0.06, 0.3), bone, pitch=-30.0))         # Schulterblatt
    # Schaedel: Hirnschaedel, Schnauze, Spitze, Augenhoehlen, Schlaefenfenster, Zaehne; Unterkiefer leicht geoeffnet
    parts.append(obox((-4.55, y, 4.6), (1.0, 0.74, 0.82), bone, outline=OL))
    parts.append(obox((-5.4, y, 4.55), (0.9, 0.52, 0.6), bone, pitch=-4.0, outline=OL))
    parts.append(obox((-5.95, y, 4.48), (0.4, 0.42, 0.46), bone, pitch=-8.0, outline=OL))
    parts.append(obox((-4.35, y, 5.05), (0.6, 0.8, 0.12), bone_d))                                     # Augenbrauenwulst
    for sgn in (-1, 1):
        parts.append(obox((-4.85, y + sgn * 0.37, 4.7), (0.32, 0.05, 0.32), socket))                  # Augenhoehle
        parts.append(obox((-5.35, y + sgn * 0.265, 4.6), (0.3, 0.04, 0.22), socket))                  # Antorbitalfenster
        parts.append(obox((-4.3, y + sgn * 0.375, 4.5), (0.3, 0.04, 0.3), socket))                    # Schlaefenfenster
    for tx in [-5.95 + 0.17 * j for j in range(8)]:
        for sgn in (-1, 1):
            parts.append(tooth((tx, y + sgn * 0.2, 4.2), 0.07, 0.16, teeth, up=False))
    jaw_pitch = 12.0
    hinge = (-4.3, y, 4.12)
    jc = _rot((-0.78, 0.0, -0.09), 0.0, jaw_pitch)
    parts.append(obox((hinge[0] + jc[0], y, hinge[2] + jc[2]), (1.62, 0.5, 0.2), bone, pitch=jaw_pitch, outline=OL))
    for tx in [-5.85 + 0.19 * j for j in range(7)]:
        for sgn in (-1, 1):
            off = _rot((tx - hinge[0], 0.0, 0.02), 0.0, jaw_pitch)
            parts.append(tooth((hinge[0] + off[0], y + sgn * 0.19, hinge[2] + off[2]), 0.065, 0.14, teeth, up=True))
    # Stahlstuetzen des Praeparats (unter Brustkorb und Becken)
    for sx in (-1.5, 1.35):
        z, r = _spine_at(sx)
        parts.append(cyl(sx, y, 0.05, ZT, z - r, steel, seg=12))
        parts.append(cyl(sx, y, 0.16, ZT, ZT + 0.04, steel, seg=16))
    # Rotunde ist 13,5 breit: das 13,3 lange Skelett steckte mit Schwanz und Schnauze in den Waenden (Meldungen
    # 18.10. #202/#203) -> in Laengsrichtung auf 85 % um die Podestmitte
    return _scale_x(parts, CX, 0.85)


def _scale_x(parts, cx, f):
    def sx(x):
        return cx + (x - cx) * f
    for q in parts:
        t = q.get("type")
        if t == "tube":
            q["pts"] = [[sx(p[0]), p[1], p[2]] for p in q["pts"]]
        elif t == "mesh":
            q["verts"] = [[sx(v[0]), v[1], v[2]] for v in q["verts"]]
        elif t == "lathe":
            q["c"] = [sx(q["c"][0]), q["c"][1]]
        elif t == "prism":
            q["pts"] = [[sx(p[0]), p[1]] for p in q["pts"]]
    return parts


def _shade_mat(ctx, name, rgb):
    return ctx.color(name, rgb)


def extra(sc, ctx):
    meshes = AP.build(sc, ctx, skip=("dino", "dino_rex", "dino_rex_head", "dino_rex_jaw"))
    meshes.append({"name": "museum_rex", "coll": "rotunde", "kind": "parts", "parts": rex(sc, ctx)})
    return meshes


def adjust(sc):
    AP.room_heights(sc)
    sc.auto_h["rotunde"] = max(sc.auto_h.get("rotunde", 0.0), REX_H)
