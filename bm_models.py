# bm_models.py - Bibliothek echter 3D-Moebel und Geraete (User 18.10.: "alle Objekte, die es in 2D gibt, in 3D neu
# zeichnen, nicht die 2D-Grafik abskalieren und platzieren"). Jeder Generator baut einen Koerper aus Kaesten,
# Drehkoerpern, Rohren und Netzen in gemessenen Farben; Bildpixel des Spiels kommen hoechstens als Bildschirminhalt
# (ein Monitor IST ein flaches Bild) oder Aufdruck vor, nie als Ersatz fuer Geometrie.
#
# Konventionen: Weltkoordinaten (x Ost, y Nord, z Hoehe), "front" = Suedseite (zum Betrachter wie im Spiel),
# Groessen in Spieleinheiten, Hoehen aus der Zeichnung / VFAC bzw. gemessen. Alle Teile unter Augenhoehe 0,62, wenn
# der Spieler im Spiel durch das Objekt laufen kann (kein Collider), sonst echte Hoehe.

import math
import random

from shapely.geometry import Polygon, box as sbox
from shapely import affinity

from bm_spec import box, cyl, lathe, mesh, obox, prism, tube, wedge_box

OL = (18, 20, 24)


def _shade(rgb, f):
    return tuple(max(0, min(255, int(v * f))) for v in rgb)


def _mat(ctx, name, rgb):
    return ctx.color(name, tuple(int(v) for v in rgb))


def _tex_from_sprite(ctx, name, img, scale=1.0):
    """Bildschirminhalt aus dem Sprite-Ausschnitt (RGB), weich hochgerechnet."""
    import bm_tex as T
    from PIL import Image
    import bm_style
    if bm_style.on(ctx.scene):
        # keine Spieltextur: generische Anzeige in der Farbfamilie des Sprites (Referenz)
        cols = bm_style.sprite_colors(img)
        asp = img.width / max(1, img.height)
        return ctx.tex(name, bm_style.ui_screen(cols, seed=len(name) + int(asp * 7), w=160, h=max(40, int(160 / max(0.5, asp)))), uv="part")
    w = max(8, int(img.width * 4 * scale))
    im = img.convert("RGB").resize((w, max(8, int(img.height * 4 * scale))), Image.LANCZOS)
    return ctx.tex(name, im, uv="part")


def screen_panel(ctx, name, cx, cy, z0, z1, w, facing="S", tex=None, rgb=(120, 190, 200), depth=0.012, glow=1.3):
    """Duenne Anzeigeplatte, Bild auf der Seite facing (S/N/E/W, achsparallel; Prisma, weil nur Prismen Bilder auf
    einer Seite tragen). tex = PIL-Bild (Schirminhalt) oder None -> leuchtende Farbe."""
    if tex is not None:
        m = _tex_from_sprite(ctx, name, tex)
    else:
        m = ctx.glow(name, rgb, glow)
    if facing in ("S", "N"):
        b = box(cx, cy, w, depth, z0, z1, m)
    else:
        b = box(cx, cy, depth, w, z0, z1, m)
    b[{"S": "front", "N": "face_n", "E": "face_e", "W": "face_w"}[facing]] = m
    return b


def _facing(yaw):
    """Achsparallele Richtung der Front (-y bei yaw 0) oder None bei schraeg."""
    a = round(yaw / 90.0) * 90 % 360
    if abs(((yaw - a) + 180) % 360 - 180) > 2:
        return None
    return {0: "S", 90: "E", 180: "N", 270: "W"}[int(a)]


# ----------------------------------------------------------------------------------------------------- Geraete

def wall_console(ctx, name, a, b, z0, z1, body_rgb=(96, 104, 112), screen=None, depth=0.10, frame_rgb=None,
                 ledge=True, glow=None):
    """Konsole an der Wand a -> b (Raum links der Richtung): Kasten mit Tiefe, abgesetzter Rahmen, eingelassener
    Bildschirm (screen = PIL-Bild des Schirminhalts oder RGB), kleine Ablage unten."""
    (ax, ay), (bx, by) = a, b
    L = math.hypot(bx - ax, by - ay)
    if L < 0.05:
        return []
    dx, dy = (bx - ax) / L, (by - ay) / L
    nx, ny = -dy, dx
    yaw = math.degrees(math.atan2(dy, dx))
    h = z1 - z0
    body = _mat(ctx, name + "_body", body_rgb)
    frame = _mat(ctx, name + "_frame", frame_rgb or _shade(body_rgb, 0.62))
    cx, cy = (ax + bx) / 2 + nx * depth / 2, (ay + by) / 2 + ny * depth / 2
    parts = [obox((cx, cy, (z0 + z1) / 2), (L, depth, h), body, yaw=yaw, outline=OL)]
    # Rahmen: ein Rand von 0,03 steht 0,015 vor der Front
    fx, fy = cx + nx * (depth / 2 + 0.008), cy + ny * (depth / 2 + 0.008)
    parts.append(obox((fx, fy, (z0 + z1) / 2), (L - 0.02, 0.016, h - 0.02), frame, yaw=yaw))
    # Bildschirm (zurueckgesetzt in den Rahmen)
    sw, sh = max(0.05, L - 0.08), max(0.04, h - 0.09)
    sx, sy = cx + nx * (depth / 2 + 0.01), cy + ny * (depth / 2 + 0.01)
    zc = (z0 + z1) / 2 + 0.01
    # Front zeigt in Richtung der Wandnormalen n (Raumseite): yaw ist die Wandrichtung, die Front eines Koerpers liegt
    # bei yaw 0 auf -y, also Frontwinkel = yaw - 90 = Winkel(n) = Wandrichtung + 90 -> Frontkoerper um 180 drehen.
    # (Vorher stand der Schirm auf der Wandseite, Meldung 19.10.: "Objekte falsch orientiert".)
    fac = _facing(yaw + 180.0)
    tex = None if (screen is None or isinstance(screen, tuple)) else screen
    rgb = screen if isinstance(screen, tuple) else (120, 190, 200)
    if fac is not None:
        parts.append(screen_panel(ctx, name + "_screen", sx, sy, zc - sh / 2, zc + sh / 2, sw, facing=fac, tex=tex, rgb=rgb,
                                  glow=glow or 1.3))
    else:
        smat = ctx.glow(name + "_screen", rgb, glow or 1.3)
        parts.append(obox((sx, sy, zc), (sw, 0.012, sh), smat, yaw=yaw))
    if ledge and h > 0.2:
        lx, ly = cx + nx * (depth / 2 + 0.02), cy + ny * (depth / 2 + 0.02)
        parts.append(obox((lx, ly, z0 + 0.025), (L - 0.04, 0.05, 0.02), frame, yaw=yaw))
    return parts


def floor_console(ctx, name, cx, cy, w, d, h, body_rgb=(96, 104, 112), screen=None, yaw=0.0, slope=True,
                  keyboard=True, screen_rgb=None):
    """Standkonsole: Sockel, Schrank mit abgeschraegter Oberseite, eingelassener Bildschirm auf der Schraege, Tastatur-
    leiste, Kante. Front zeigt nach -y (yaw 0) bzw. gedreht."""
    body = _mat(ctx, name + "_body", body_rgb)
    dark = _mat(ctx, name + "_dark", _shade(body_rgb, 0.7))
    base_h = min(0.06, h * 0.15)
    parts = [obox((cx, cy, base_h / 2), (w - 0.06, d - 0.06, base_h), dark, yaw=yaw)]
    if slope and h > 0.3:
        hb = h * 0.62
        parts.append(obox((cx, cy, base_h + (hb - base_h) / 2), (w, d, hb - base_h), body, yaw=yaw, outline=OL))
        # Schraege: Keil, Vorderkante bei hb, Hinterkante bei h
        v = [(-w / 2, -d / 2, hb), (w / 2, -d / 2, hb), (w / 2, d / 2, h), (-w / 2, d / 2, h),
             (-w / 2, -d / 2, hb - 0.001), (w / 2, -d / 2, hb - 0.001), (w / 2, d / 2, hb - 0.001), (-w / 2, d / 2, hb - 0.001)]
        from bm_spec import rot3
        verts = []
        for p in v:
            rx, ry, rz = rot3(p, yaw, 0.0)
            verts.append((cx + rx, cy + ry, rz))
        faces = [(0, 1, 2, 3), (7, 6, 5, 4), (4, 5, 1, 0), (5, 6, 2, 1), (6, 7, 3, 2), (7, 4, 0, 3)]
        parts.append(mesh(verts, faces, body, outline=OL))
        # Bildschirm auf der Schraege
        roll = math.degrees(math.atan2(h - hb, d))                      # Hinterkante hoeher: um x kippen
        sz = (hb + h) / 2 + 0.012
        smat = ctx.glow(name + "_screen", screen_rgb or (120, 190, 200), 1.2)
        parts.append(obox((cx, cy, sz), (w * 0.72, d * 0.55, 0.012), smat, yaw=yaw, roll=roll))
        frame = _mat(ctx, name + "_scrframe", _shade(body_rgb, 0.55))
        parts.append(obox((cx, cy, sz - 0.004), (w * 0.76, d * 0.59, 0.01), frame, yaw=yaw, roll=roll))
        if keyboard:
            kb = _mat(ctx, name + "_keys", _shade(body_rgb, 0.5))
            # Tastatur liegt vorn auf der Schraege
            fx, fy = rot3((0.0, -d * 0.3, 0.0), yaw, 0.0)[:2]
            k = obox((cx + fx, cy + fy, hb + 0.045 + d * 0.3 * (h - hb) / d * 0.5), (w * 0.6, d * 0.22, 0.02), kb, yaw=yaw, roll=roll)
            parts.append(k)
    else:
        parts.append(obox((cx, cy, base_h + (h - base_h) / 2), (w, d, h - base_h), body, yaw=yaw, outline=OL))
        if screen is not None or screen_rgb:
            from bm_spec import rot3
            fx, fy = rot3((0.0, -d / 2 - 0.008, 0.0), yaw, 0.0)[:2]
            fac = _facing(yaw)
            if fac is not None:
                parts.append(screen_panel(ctx, name + "_screen", cx + fx, cy + fy, h * 0.38, h * 0.83, w * 0.7, facing=fac, tex=screen,
                                          rgb=screen_rgb or (120, 190, 200)))
            else:
                smat = ctx.glow(name + "_screen", screen_rgb or (120, 190, 200), 1.2)
                parts.append(obox((cx + fx, cy + fy, h * 0.6), (w * 0.7, 0.012, h * 0.45), smat, yaw=yaw))
    return parts


def monitor(ctx, name, cx, cy, z, w, h, screen=None, yaw=0.0, pitch=-8.0, rgb=(54, 58, 66), stand=True,
            screen_rgb=(88, 150, 190), glow=1.4):
    """Bildschirm mit Rahmen auf Fuss/Arm, Schirm zur -y-Seite (yaw 0)."""
    body = _mat(ctx, name + "_body", rgb)
    from bm_spec import rot3
    parts = []
    if stand:
        parts.append(cyl(cx, cy, w * 0.28, z, z + 0.02, body, seg=20, outline=OL))
        parts.append(cyl(cx, cy, 0.02, z + 0.02, z + h * 0.45, body, seg=10))
    zc = z + (h * 0.45 if stand else 0) + h / 2
    fac = _facing(yaw)
    if fac is not None and screen is not None:
        pitch = 0.0
    parts.append(obox((cx, cy, zc), (w, 0.05, h), body, yaw=yaw, roll=pitch, outline=OL))
    off = rot3((0.0, -0.032, 0.0), yaw, 0.0, pitch)
    if fac is not None and abs(pitch) < 1e-6:
        parts.append(screen_panel(ctx, name + "_screen", cx + off[0], cy + off[1], zc - (h - 0.05) / 2, zc + (h - 0.05) / 2, w - 0.05,
                                  facing=fac, tex=screen, rgb=screen_rgb, glow=glow))
    else:
        smat = ctx.glow(name + "_screen", screen_rgb, glow)
        parts.append(obox((cx + off[0], cy + off[1], zc + off[2]), (w - 0.05, 0.012, h - 0.05), smat, yaw=yaw, roll=pitch))
    return parts


def camera_dome(ctx, name, cx, cy, z, yaw=0.0, rgb=(70, 74, 96), lens=(40, 40, 60)):
    """Ueberwachungskamera: Halbkugel-Gehaeuse auf einem Wandarm, zeigt in Richtung yaw."""
    body = _mat(ctx, name + "_body", rgb)
    dark = _mat(ctx, name + "_lens", lens)
    led = ctx.glow(name + "_led", (240, 60, 60), 2.0)
    r = 0.09
    prof = [(0.0, 0.0), (r, 0.0), (r * 0.95, r * 0.4), (r * 0.7, r * 0.8), (0.0, r * 1.0)]
    parts = [lathe(cx, cy, [(a, z - r * 0.5 + b) for a, b in prof], body, seg=18, outline=OL)]
    from bm_spec import rot3
    off = rot3((0.0, -r * 0.8, 0.0), yaw, 0.0)
    parts.append(lathe(cx + off[0], cy + off[1], [(0.0, z - 0.02), (0.035, z - 0.02), (0.035, z + 0.02), (0.0, z + 0.02)], dark, seg=12))
    parts.append(box(cx + off[0] * 0.5, cy + off[1] * 0.5, 0.02, 0.02, z + r * 0.45, z + r * 0.45 + 0.02, led))
    back = rot3((0.0, r * 0.9, 0.0), yaw, 0.0)
    parts.append(obox((cx + back[0], cy + back[1], z - r * 0.3), (0.06, 0.1, 0.03), body, yaw=yaw))
    return parts


def vent_grate(ctx, name, x0, y0, x1, y1, z=0.0, rgb=(82, 96, 100), slots=5, dark=(26, 32, 34)):
    """Bodengitter: Rahmen mit Fase, dunkle Oeffnung, Stege; nichts aufgemalt."""
    frame = _mat(ctx, name + "_frame", rgb)
    hole = _mat(ctx, name + "_hole", dark)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [prism(sbox(x0, y0, x1, y1).difference(sbox(x0 + 0.06, y0 + 0.06, x1 - 0.06, y1 - 0.06)), z, z + 0.035, frame,
                   bevel=0.01, outline=OL),
             box(cx, cy, w - 0.1, d - 0.1, z, z + 0.004, hole)]
    n = max(2, slots)
    for i in range(n):
        yy = y0 + 0.06 + (d - 0.12) * (i + 0.5) / n
        parts.append(box(cx, yy, w - 0.12, 0.035, z + 0.012, z + 0.03, frame))
    return parts


# ----------------------------------------------------------------------------------------------------- Moebel

def bed(ctx, name, x0, y0, x1, y1, head="N", frame_rgb=(123, 130, 148), mattress_rgb=(222, 226, 236),
        blanket_rgb=(93, 138, 196), pillow_rgb=(244, 244, 248), h_frame=0.30, h_mattress=0.14):
    """Krankenbett: vier Fuesse, Rahmen, Matratze mit Fase, Kissen am Kopfende, Decke, Kopf- und Fussteil."""
    frame = _mat(ctx, name + "_frame", frame_rgb)
    matt = _mat(ctx, name + "_mattress", mattress_rgb)
    blank = _mat(ctx, name + "_blanket", blanket_rgb)
    pill = _mat(ctx, name + "_pillow", pillow_rgb)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = []
    for fx in (x0 + 0.06, x1 - 0.06):
        for fy in (y0 + 0.06, y1 - 0.06):
            parts.append(box(fx, fy, 0.05, 0.05, 0.0, h_frame - 0.05, frame))
    parts.append(box(cx, cy, w, d, h_frame - 0.05, h_frame, frame, bevel=0.01, outline=OL))
    parts.append(box(cx, cy, w - 0.04, d - 0.04, h_frame, h_frame + h_mattress, matt, bevel=0.04, outline=OL))
    zt = h_frame + h_mattress
    along_y = head in ("N", "S")
    if along_y:
        hy = y1 - 0.14 if head == "N" else y0 + 0.14
        parts.append(box(cx, hy, w - 0.16, 0.22, zt, zt + 0.07, pill, bevel=0.03, outline=OL))
        by = cy - (0.12 if head == "N" else -0.12)
        parts.append(box(cx, by, w - 0.06, d * 0.55, zt, zt + 0.03, blank, bevel=0.015, outline=OL))
        hb_y = y1 if head == "N" else y0
        parts.append(box(cx, hb_y, w, 0.04, 0.0, zt + 0.28, frame, bevel=0.01, outline=OL))
        fb_y = y0 if head == "N" else y1
        parts.append(box(cx, fb_y, w, 0.04, 0.0, zt + 0.12, frame, bevel=0.01, outline=OL))
    else:
        hx = x1 - 0.14 if head == "E" else x0 + 0.14
        parts.append(box(hx, cy, 0.22, d - 0.16, zt, zt + 0.07, pill, bevel=0.03, outline=OL))
        bx = cx - (0.12 if head == "E" else -0.12)
        parts.append(box(bx, cy, w * 0.55, d - 0.06, zt, zt + 0.03, blank, bevel=0.015, outline=OL))
        hb_x = x1 if head == "E" else x0
        parts.append(box(hb_x, cy, 0.04, d, 0.0, zt + 0.28, frame, bevel=0.01, outline=OL))
        fb_x = x0 if head == "E" else x1
        parts.append(box(fb_x, cy, 0.04, d, 0.0, zt + 0.12, frame, bevel=0.01, outline=OL))
    return parts


def locker_row(ctx, name, x0, y0, x1, y1, h=1.2, n=None, facing="S", rgb=(150, 120, 92), dark=(70, 56, 44),
               handle_rgb=(200, 200, 205)):
    """Spindreihe: Korpus, je Spind eine Tuer mit Fuge, Griff und drei Lueftungsschlitzen auf der Seite facing."""
    body = _mat(ctx, name + "_body", rgb)
    door = _mat(ctx, name + "_door", _shade(rgb, 1.08))
    gap = _mat(ctx, name + "_gap", dark)
    handle = _mat(ctx, name + "_handle", handle_rgb)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, 0.0, h, body, outline=OL), box(cx, cy, w, d, h, h + 0.03, gap)]
    along_x = facing in ("S", "N")
    length = w if along_x else d
    n = n or max(1, int(round(length / 0.42)))
    cell = length / n
    for i in range(n):
        c = (x0 if along_x else y0) + cell * (i + 0.5)
        if facing == "S":
            px, py, yaw, dw = c, y0 - 0.012, 0.0, cell
        elif facing == "N":
            px, py, yaw, dw = c, y1 + 0.012, 180.0, cell
        elif facing == "W":
            px, py, yaw, dw = x0 - 0.012, c, 90.0, cell
        else:
            px, py, yaw, dw = x1 + 0.012, c, -90.0, cell
        from bm_spec import rot3
        og = rot3((0.0, -0.004, 0.0), yaw, 0.0)
        parts.append(obox((px + og[0], py + og[1], h / 2), (dw - 0.01, 0.01, h - 0.04), gap, yaw=yaw))      # Fugenrahmen
        parts.append(obox((px, py, h / 2), (dw - 0.06, 0.03, h - 0.1), door, yaw=yaw, outline=OL))
        o = rot3((dw * 0.3, -0.025, 0.0), yaw, 0.0)
        parts.append(obox((px + o[0], py + o[1], h * 0.52), (0.03, 0.03, 0.12), handle, yaw=yaw, outline=OL))
        for j in range(3):
            o2 = rot3((0.0, -0.018, 0.0), yaw, 0.0)
            parts.append(obox((px + o2[0], py + o2[1], h * 0.82 - j * 0.045), (dw * 0.5, 0.01, 0.014), gap, yaw=yaw))
    return parts


def bench(ctx, name, x0, y0, x1, y1, h=0.42, rgb=(82, 89, 132), leg_rgb=(60, 62, 70), slats=0):
    """Bank: Sitzplatte (mit Fase, optional Latten), vier Beine, Zarge."""
    seat = _mat(ctx, name + "_seat", rgb)
    leg = _mat(ctx, name + "_leg", leg_rgb)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = []
    for fx in (x0 + 0.05, x1 - 0.05):
        for fy in (y0 + 0.05, y1 - 0.05):
            parts.append(box(fx, fy, 0.045, 0.045, 0.0, h - 0.05, leg))
    parts.append(box(cx, cy, w - 0.02, d - 0.02, h - 0.08, h - 0.05, leg))
    if slats:
        along_x = w >= d
        n = slats
        for i in range(n):
            if along_x:
                yy = y0 + d * (i + 0.5) / n
                parts.append(box(cx, yy, w, d / n - 0.02, h - 0.05, h, seat, bevel=0.01, outline=OL))
            else:
                xx = x0 + w * (i + 0.5) / n
                parts.append(box(xx, cy, w / n - 0.02, d, h - 0.05, h, seat, bevel=0.01, outline=OL))
    else:
        parts.append(box(cx, cy, w, d, h - 0.05, h, seat, bevel=0.015, outline=OL))
    return parts


def table(ctx, name, x0, y0, x1, y1, h=0.75, top_rgb=(180, 99, 68), leg_rgb=(139, 137, 136), pedestal=False,
          round_=False, top_tex=None, thick=0.05):
    """Tisch: Platte (rechteckig/oval, optional Aufdruck), vier Beine oder Mittelsaeule mit Fuss."""
    top = _mat(ctx, name + "_top", top_rgb)
    leg = _mat(ctx, name + "_leg", leg_rgb)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = []
    if round_:
        parts.append(cyl(cx, cy, w / 2, h - thick, h, top, top=top_tex, ry=d / 2, seg=48, bevel=0.015, outline=OL))
    else:
        t = box(cx, cy, w, d, h - thick, h, top, bevel=0.015, outline=OL)
        if top_tex:
            t["top"] = top_tex
        parts.append(t)
    if pedestal:
        parts.append(cyl(cx, cy, min(w, d) * 0.08, 0.02, h - thick, leg, seg=16))
        parts.append(cyl(cx, cy, min(w, d) * 0.3, 0.0, 0.03, leg, ry=min(w, d) * 0.3 * (d / w if w > d else 1), seg=32, outline=OL))
    else:
        for fx in (x0 + 0.07, x1 - 0.07):
            for fy in (y0 + 0.07, y1 - 0.07):
                parts.append(box(fx, fy, 0.05, 0.05, 0.0, h - thick, leg))
    return parts


def shelf_unit(ctx, name, x0, y0, x1, y1, h=1.8, boards=4, rgb=(72, 76, 84), items=True, seed=1, facing="S",
               item_colors=((181, 33, 115), (90, 150, 190), (220, 200, 140), (90, 160, 100), (200, 90, 70))):
    """Regal: zwei Seitenwangen, Rueckwand (gegenueber der Seite facing, S/N/E/W), Boeden, darauf Kisten/Dosen/
    Flaschen (kleine Koerper)."""
    body = _mat(ctx, name + "_body", rgb)
    back = _mat(ctx, name + "_back", _shade(rgb, 0.8))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    along_x = facing in ("S", "N")
    # Koordinaten entlang der Front (a) und in der Tiefe (b); Umrechnung in Welt
    a0, a1, b0, b1 = (x0, x1, y0, y1) if along_x else (y0, y1, x0, x1)
    L, D = a1 - a0, b1 - b0
    ca, cb = (a0 + a1) / 2, (b0 + b1) / 2

    def B(a, b, sa, sb, z0, z1, m, **kw):
        return box(a, b, sa, sb, z0, z1, m, **kw) if along_x else box(b, a, sb, sa, z0, z1, m, **kw)

    def C(a, b, r, z0, z1, m, **kw):
        return cyl(a, b, r, z0, z1, m, **kw) if along_x else cyl(b, a, r, z0, z1, m, **kw)

    def LA(a, b, prof, m, **kw):
        return lathe(a, b, prof, m, **kw) if along_x else lathe(b, a, prof, m, **kw)
    parts = [B(a0 + 0.02, cb, 0.04, D, 0.0, h, body, outline=OL), B(a1 - 0.02, cb, 0.04, D, 0.0, h, body, outline=OL)]
    bb = (b1 - 0.02) if facing in ("S", "W") else (b0 + 0.02)
    parts.append(B(ca, bb, L, 0.04, 0.0, h, back))
    rnd = random.Random(seed)
    for i in range(boards):
        z = 0.06 + (h - 0.12) * i / max(1, boards - 1)
        parts.append(B(ca, cb, L - 0.04, D, z, z + 0.03, body, outline=OL))
        if items and i < boards - 1:
            zb = z + 0.03
            a = a0 + 0.08
            while a < a1 - 0.1:
                iw = rnd.uniform(0.08, 0.2)
                ih = rnd.uniform(0.1, min(0.32, (h - 0.12) / max(1, boards - 1) - 0.08))
                col = rnd.choice(item_colors)
                m = _mat(ctx, f"{name}_item{len(parts)}", col)
                kind = rnd.random()
                if kind < 0.4:
                    parts.append(B(a + iw / 2, cb, iw, D * 0.6, zb, zb + ih, m, bevel=0.01, outline=OL))
                elif kind < 0.7:
                    parts.append(C(a + iw / 2, cb, iw * 0.4, zb, zb + ih, m, seg=12, outline=OL))
                else:
                    parts.append(LA(a + iw / 2, cb, [(0.0, zb), (iw * 0.35, zb), (iw * 0.35, zb + ih * 0.6), (iw * 0.15, zb + ih * 0.75),
                                                     (iw * 0.15, zb + ih), (0.0, zb + ih)], m, seg=12, outline=OL))
                a += iw + rnd.uniform(0.03, 0.12)
    return parts


def vending_machine(ctx, name, x0, y0, x1, y1, h=1.8, rgb=(222, 218, 209), dark=(46, 47, 44), glass=(70, 110, 140),
                    rows=4, facing="S", seed=3, products=((200, 60, 60), (240, 200, 60), (60, 160, 90), (70, 110, 220), (240, 240, 240))):
    """Verkaufsautomat: Korpus, Fenster mit Rahmen, Produktreihen hinter Glas, Tastenfeld, Ausgabeklappe, Sockel."""
    body = _mat(ctx, name + "_body", rgb)
    trim = _mat(ctx, name + "_trim", dark)
    gl = _mat(ctx, name + "_glass", glass)
    ctx.scene.mats[gl]["emit"] = 0.6
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w - 0.04, d - 0.04, 0.0, 0.08, trim), box(cx, cy, w, d, 0.08, h, body, bevel=0.015, outline=OL)]
    fy = y0 - 0.006 if facing == "S" else y1 + 0.006
    ww = w * 0.62
    wx = x0 + 0.05 + ww / 2
    sgn = -1.0 if facing == "S" else 1.0
    parts.append(box(wx, fy, ww + 0.04, 0.012, h * 0.3, h * 0.92, trim))
    parts.append(box(wx, fy + sgn * 0.008, ww, 0.008, h * 0.32, h * 0.9, gl))                 # Fensterflaeche (vertieft)
    rnd = random.Random(seed)
    for r in range(rows):
        z = h * 0.34 + (h * 0.54) * r / rows
        parts.append(box(wx, fy + sgn * 0.02, ww - 0.02, 0.03, z, z + 0.008, trim))         # Regalbrett
        x = wx - ww / 2 + 0.03
        while x < wx + ww / 2 - 0.05:
            pw = rnd.uniform(0.05, 0.08)
            m = _mat(ctx, f"{name}_p{len(parts)}", rnd.choice(products))
            parts.append(box(x + pw / 2, fy + sgn * 0.022, pw, 0.03, z + 0.008, z + 0.008 + rnd.uniform(0.06, 0.1), m))
            x += pw + 0.02
    kx = x1 - 0.05 - (w - ww - 0.12) / 2
    parts.append(box(kx, fy, w - ww - 0.12, 0.012, h * 0.55, h * 0.85, trim))
    for i in range(6):
        parts.append(box(kx - 0.02 + (i % 2) * 0.04, fy - (0.006 if facing == "S" else -0.006), 0.025, 0.006, h * 0.6 + (i // 2) * 0.06,
                         h * 0.6 + (i // 2) * 0.06 + 0.03, _mat(ctx, name + "_key", (220, 220, 225))))
    parts.append(box(wx, fy, ww * 0.9, 0.012, h * 0.12, h * 0.24, trim))
    return parts


def planter(ctx, name, x0, y0, x1, y1, h=0.26, kind="fern", trough_rgb=(178, 90, 56), soil_rgb=(70, 50, 36),
            leaf_rgb=(24, 93, 5), leaf_dark=(16, 64, 4), seed=0, density=1.0):
    """Pflanzkasten: Trog mit Rand, Erde, Pflanzen: fern = Blattwedel (schmale Bretter, gefaechert), bush = Buschkugeln."""
    from bm_spec import blob
    trough = _mat(ctx, name + "_trough", trough_rgb)
    rim = _mat(ctx, name + "_rim", _shade(trough_rgb, 1.15))
    soil = _mat(ctx, name + "_soil", soil_rgb)
    leaf = _mat(ctx, name + "_leaf", leaf_rgb)
    ldark = _mat(ctx, name + "_leafdark", leaf_dark)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [prism(sbox(x0, y0, x1, y1).difference(sbox(x0 + 0.04, y0 + 0.04, x1 - 0.04, y1 - 0.04)), 0.0, h, trough, outline=OL),
             box(cx, cy, w - 0.04, d - 0.04, 0.0, h - 0.06, trough),
             prism(sbox(x0 - 0.01, y0 - 0.01, x1 + 0.01, y1 + 0.01).difference(sbox(x0 + 0.05, y0 + 0.05, x1 - 0.05, y1 - 0.05)), h, h + 0.02, rim),
             box(cx, cy, w - 0.08, d - 0.08, h - 0.06, h - 0.03, soil)]
    rnd = random.Random(seed)
    if kind == "fern":
        n = max(3, int(w * 6 * density))
        for i in range(n):
            px = x0 + 0.12 + (w - 0.24) * (i + 0.5) / n + rnd.uniform(-0.03, 0.03)
            py = cy + rnd.uniform(-d * 0.25, d * 0.25)
            for j in range(5):
                a = rnd.uniform(0, 360)
                pitch = rnd.uniform(-70, -35)
                L = rnd.uniform(0.18, 0.34)
                m = leaf if j % 2 else ldark
                from bm_spec import rot3
                o = rot3((L / 2, 0.0, 0.0), a, pitch)
                parts.append(obox((px + o[0], py + o[1], h - 0.03 + o[2]), (L, 0.05, 0.012), m, yaw=a, pitch=pitch))
    else:
        # Buschwerk (19.10., User: "verbessere das"): viele kleine Kugeln in zwei Reihen, dazwischen Blueten und Stiele,
        # statt einer Kugel je 0,45 m, die wie ein gruener Felsen wirkte
        flower = _mat(ctx, name + "_flower", (235, 225, 120))
        nx = max(3, int(w * 5 * density))
        for row, fy in enumerate((-0.25, 0.22)):
            for i in range(nx):
                px = x0 + 0.1 + (w - 0.2) * (i + 0.5 + 0.3 * row) / nx + rnd.uniform(-0.02, 0.02)
                py = cy + fy * d + rnd.uniform(-0.03, 0.03)
                r = rnd.uniform(0.07, 0.12)
                parts.append(blob(px, py, h - 0.04 + r * 0.5, r, min(r * 0.9, d * 0.3), r * 0.9, (leaf, ldark), seed=seed * 10 + i + row * 7,
                                  seg=8, rings=5, outline=(0, 44, 0)))
                if rnd.random() < 0.35:
                    parts.append(cyl(px, py, 0.006, h - 0.03, h + r * 0.9 + 0.08, ldark, seg=5))
                    parts.append(lathe(px, py, [(0.0, h + r * 0.9 + 0.07), (0.03, h + r * 0.9 + 0.09), (0.0, h + r * 0.9 + 0.12)], flower, seg=6))
    return parts


def potted_plant(ctx, name, cx, cy, z0=0.0, r=0.1, h=0.45, pot_rgb=(170, 90, 60), leaf_rgb=(40, 120, 40), flower=None, seed=0):
    """Topfpflanze: Topf (Drehkoerper), Erde, Stiel, Blaetter als Stern, optional Bluete."""
    pot = _mat(ctx, name + "_pot", pot_rgb)
    soil = _mat(ctx, name + "_soil", (60, 44, 32))
    leaf = _mat(ctx, name + "_leaf", leaf_rgb)
    stem = _mat(ctx, name + "_stem", _shade(leaf_rgb, 0.7))
    parts = [lathe(cx, cy, [(0.0, z0), (r * 0.75, z0), (r, z0 + h * 0.32), (r * 1.05, z0 + h * 0.36), (0.0, z0 + h * 0.36)], pot, seg=18, outline=OL),
             cyl(cx, cy, r * 0.92, z0 + h * 0.34, z0 + h * 0.36, soil, seg=18)]
    rnd = random.Random(seed)
    parts.append(tube([(cx, cy, z0 + h * 0.35), (cx, cy, z0 + h * 0.8)], 0.012, stem, seg=6))
    from bm_spec import rot3
    for i in range(6):
        a = i * 60 + rnd.uniform(-15, 15)
        pitch = rnd.uniform(-30, 10)
        L = r * rnd.uniform(1.4, 2.0)
        o = rot3((L / 2, 0.0, 0.0), a, pitch)
        parts.append(obox((cx + o[0], cy + o[1], z0 + h * 0.72 + o[2]), (L, r * 0.6, 0.012), leaf, yaw=a, pitch=pitch))
    if flower:
        fm = _mat(ctx, name + "_flower", flower)
        parts.append(lathe(cx, cy, [(0.0, z0 + h * 0.8), (r * 0.5, z0 + h * 0.82), (r * 0.35, z0 + h * 0.95), (0.0, z0 + h)], fm, seg=10))
    return parts


def vine(ctx, name, x, y_wall, z_top, length, side=1.0, rgb=(40, 70, 48), leaf_rgb=(60, 120, 60), seed=0, sway=0.25):
    """Ranke an der Wand: Hauptstrang als geschwungenes Rohr von oben nach unten, zwei Seitentriebe, Blaetter."""
    rnd = random.Random(seed)
    stem = _mat(ctx, name + "_stem", rgb)
    leaf = _mat(ctx, name + "_leaf", leaf_rgb)
    parts = []
    n = 8
    pts = [(x + math.sin(i / n * math.pi * 2.3 + rnd.uniform(-0.3, 0.3)) * sway, y_wall - 0.04 * side, z_top - length * i / n) for i in range(n + 1)]
    parts.append(tube(pts, 0.03, stem, seg=8, outline=OL))
    for j in range(2):
        i0 = rnd.randint(2, n - 3)
        p0 = pts[i0]
        sub = [p0, (p0[0] + rnd.uniform(-0.35, 0.35), p0[1], p0[2] - 0.3), (p0[0] + rnd.uniform(-0.6, 0.6), p0[1], p0[2] - 0.7)]
        parts.append(tube(sub, 0.018, stem, seg=6))
    from bm_spec import rot3
    for i in range(1, n):
        px, py, pz = pts[i]
        for _ in range(2):
            a = rnd.uniform(0, 360)
            o = rot3((0.07, 0.0, 0.0), a, rnd.uniform(-40, 40))
            parts.append(obox((px + o[0], py + o[1] * 0.3, pz + o[2]), (0.12, 0.07, 0.01), leaf, yaw=a, pitch=rnd.uniform(-40, 40)))
    return parts


def tree(ctx, name, cx, cy, z0=0.0, h=2.4, trunk_r=0.1, crown_r=0.9, trunk_rgb=(90, 62, 44), leaf_rgb=(44, 110, 52),
         leaf_dark=(30, 78, 36), seed=0, crowns=4):
    """Baum: Stamm (leicht konisch), Astgabel, mehrere Kronenballen."""
    from bm_spec import blob
    trunk = _mat(ctx, name + "_trunk", trunk_rgb)
    leaf = _mat(ctx, name + "_leaf", leaf_rgb)
    ldark = _mat(ctx, name + "_leafdark", leaf_dark)
    rnd = random.Random(seed)
    parts = [lathe(cx, cy, [(0.0, z0), (trunk_r * 1.3, z0), (trunk_r, z0 + h * 0.2), (trunk_r * 0.75, z0 + h * 0.62), (0.0, z0 + h * 0.64)],
                   trunk, seg=14, outline=OL)]
    for i in range(3):
        a = rnd.uniform(0, 360)
        e = (cx + math.cos(math.radians(a)) * crown_r * 0.5, cy + math.sin(math.radians(a)) * crown_r * 0.5, z0 + h * 0.78)
        parts.append(tube([(cx, cy, z0 + h * 0.55), e], trunk_r * 0.45, trunk, seg=8))
    for i in range(crowns):
        a = i / crowns * 360 + rnd.uniform(-20, 20)
        rr = crown_r * rnd.uniform(0.55, 0.8)
        px = cx + math.cos(math.radians(a)) * crown_r * 0.45
        py = cy + math.sin(math.radians(a)) * crown_r * 0.45
        parts.append(blob(px, py, z0 + h * 0.78 + rnd.uniform(-0.1, 0.15), rr, rr, rr * 0.75, (leaf, ldark), seed=seed * 7 + i, seg=12, rings=7,
                          outline=(0, 44, 0)))
    parts.append(blob(cx, cy, z0 + h * 0.9, crown_r * 0.7, crown_r * 0.7, crown_r * 0.55, (leaf, ldark), seed=seed * 7 + 99, seg=12, rings=7,
                      outline=(0, 44, 0)))
    return parts


def tank(ctx, name, cx, cy, r, h, z0=0.0, rgb=(150, 160, 170), band_rgb=(90, 100, 110), glass=None, pipes=2, seed=0):
    """Tank/Behaelter: Zylinder mit gewoelbtem Deckel, Baender, Sockel, Rohre seitlich."""
    body = _mat(ctx, name + "_body", rgb)
    band = _mat(ctx, name + "_band", band_rgb)
    parts = [cyl(cx, cy, r * 1.08, z0, z0 + 0.06, band, seg=36, outline=OL),
             cyl(cx, cy, r, z0 + 0.06, z0 + h - r * 0.4, body, seg=36, outline=OL),
             lathe(cx, cy, [(r, z0 + h - r * 0.4), (r * 0.85, z0 + h - r * 0.15), (r * 0.5, z0 + h), (0.0, z0 + h + 0.01)], body, seg=36)]
    for f in (0.3, 0.7):
        parts.append(cyl(cx, cy, r * 1.03, z0 + h * f, z0 + h * f + 0.05, band, seg=36))
    if glass:
        gm = ctx.glow(name + "_glass", glass, 1.0)
        parts.append(cyl(cx, cy, r * 1.01, z0 + h * 0.38, z0 + h * 0.62, gm, seg=36))
    rnd = random.Random(seed)
    for i in range(pipes):
        a = math.radians(rnd.uniform(0, 360))
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        parts.append(tube([(px, py, z0 + h * 0.5), (px + math.cos(a) * 0.25, py + math.sin(a) * 0.25, z0 + h * 0.5),
                           (px + math.cos(a) * 0.25, py + math.sin(a) * 0.25, z0)], 0.035, band, seg=8))
    return parts


def crate_stack(ctx, name, cx, cy, s, h, n=2, rgb=(185, 165, 125), dark=(120, 100, 70), tape=(220, 190, 60), seed=0):
    """Kartonstapel: Kisten mit Fase, Deckelfuge und Klebeband-Streifen, leicht gegeneinander verdreht."""
    rnd = random.Random(seed)
    body = _mat(ctx, name + "_body", rgb)
    edge = _mat(ctx, name + "_edge", dark)
    tp = _mat(ctx, name + "_tape", tape)
    parts = []
    z = 0.0
    for i in range(n):
        rot = rnd.uniform(-12, 12)
        ss = s * (1.0 - 0.12 * i)
        sq = affinity.rotate(sbox(cx - ss / 2, cy - ss / 2, cx + ss / 2, cy + ss / 2), rot, origin=(cx, cy))
        parts.append(prism(sq, z, z + h, body, bevel=0.015, outline=OL))
        parts.append(prism(sq.buffer(0.004), z + h - 0.02, z + h, edge))
        parts.append(obox((cx, cy, z + h + 0.004), (ss * 0.98, 0.06, 0.006), tp, yaw=rot))
        z += h
        h *= 0.85
    return parts


def map_table(ctx, name, x0, y0, x1, y1, h=0.75, rgb=(74, 105, 82), holo=(120, 230, 120), seed=0):
    """Kartentisch (Admin): Korpus mit Fase, umlaufender Rand, leuchtende Kartenscheibe mit Rasterlinien, Holo-Waende."""
    body = _mat(ctx, name + "_body", rgb)
    rim = _mat(ctx, name + "_rim", _shade(rgb, 1.25))
    glow = ctx.glow(name + "_holo", holo, 2.0)
    line = ctx.glow(name + "_hololine", _shade(holo, 0.75), 1.5)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, 0.0, h - 0.04, body, bevel=0.02, outline=OL),
             prism(sbox(x0, y0, x1, y1).difference(sbox(x0 + 0.08, y0 + 0.08, x1 - 0.08, y1 - 0.08)), h - 0.04, h, rim, outline=OL),
             cyl(cx, cy, min(w, d) * 0.42, h - 0.04, h - 0.03, glow, ry=min(w, d) * 0.42 * (d / w if d < w else 1.0), seg=48)]
    rnd = random.Random(seed)
    for i in range(7):
        xx = x0 + 0.15 + (w - 0.3) * rnd.random()
        yy = y0 + 0.15 + (d - 0.3) * rnd.random()
        ww, dd = rnd.uniform(0.1, 0.35), rnd.uniform(0.1, 0.3)
        parts.append(prism(sbox(xx, yy, xx + ww, yy + dd).difference(sbox(xx + 0.012, yy + 0.012, xx + ww - 0.012, yy + dd - 0.012)),
                           h - 0.03, h + 0.05, line))
    return parts


def pipe_run(ctx, name, pts, r=0.06, rgb=(110, 120, 130), flanges=True):
    """Rohrleitung entlang pts mit Flanschen an den Knicken."""
    body = _mat(ctx, name + "_pipe", rgb)
    fl = _mat(ctx, name + "_flange", _shade(rgb, 0.7))
    parts = [tube(pts, r, body, seg=12, outline=OL)]
    if flanges:
        for p in pts[1:-1]:
            parts.append(lathe(p[0], p[1], [(0.0, p[2] - r * 1.3), (r * 1.35, p[2] - r * 1.3), (r * 1.35, p[2] + r * 1.3), (0.0, p[2] + r * 1.3)],
                               fl, seg=12))
    return parts


def fan_unit(ctx, name, cx, cy, z, r=0.17, yaw=0.0, rgb=(60, 66, 72), blade_rgb=(40, 44, 48)):
    """Luefter: Ring, Nabe, vier Fluegel, in Richtung yaw (Wandluefter: Achse waagerecht)."""
    ring = _mat(ctx, name + "_ring", rgb)
    blade = _mat(ctx, name + "_blade", blade_rgb)
    parts = [lathe(cx, cy, [(r * 0.85, z - 0.04), (r, z - 0.04), (r, z + 0.04), (r * 0.85, z + 0.04)], ring, seg=24, tilt=(90.0, yaw, z), outline=OL),
             lathe(cx, cy, [(0.0, z - 0.03), (r * 0.18, z - 0.03), (r * 0.18, z + 0.03), (0.0, z + 0.03)], blade, seg=12, tilt=(90.0, yaw, z))]
    from bm_spec import rot3
    for i in range(4):
        a = i * 90 + 20
        o = rot3((r * 0.5, 0.0, 0.0), a, 0.0)
        # Fluegel liegen in der Ringebene (senkrecht), um die Achse gedreht
        parts.append(obox((cx, cy, z), (r * 0.9, 0.012, r * 0.32), blade, yaw=yaw + 90, pitch=a))
    return parts


def stepped_desk(ctx, name, x0, y0, x1, y1, h_front=0.5, h_back=1.1, step_frac=0.5, rgb=(90, 96, 112), screen=None,
                 facing="S"):
    """Pult mit Stufe (Mira Reactor-Borders): niedriger vorderer Teil zur Seite facing, hoher hinterer Teil, Anzeige
    an der Stufe, Tastenfeld auf dem niedrigen Teil."""
    body = _mat(ctx, name + "_body", rgb)
    dark = _mat(ctx, name + "_dark", _shade(rgb, 0.72))
    w, d = x1 - x0, y1 - y0
    parts = []
    if facing in ("S", "N"):
        yf0, yf1 = (y0, y0 + d * step_frac) if facing == "S" else (y1 - d * step_frac, y1)
        yb0, yb1 = (yf1, y1) if facing == "S" else (y0, yf0)
        cx = (x0 + x1) / 2
        parts.append(box(cx, (yf0 + yf1) / 2, w, yf1 - yf0, 0.0, h_front, body, bevel=0.015, outline=OL))
        parts.append(box(cx, (yb0 + yb1) / 2, w, yb1 - yb0, 0.0, h_back, body, bevel=0.015, outline=OL))
        parts.append(box(cx, (yf0 + yf1) / 2, w - 0.08, (yf1 - yf0) - 0.08, h_front, h_front + 0.012, dark))
        sy = yb0 - 0.006 if facing == "S" else yb1 + 0.006
        parts.append(screen_panel(ctx, name + "_scr", cx, sy, h_front + 0.08, h_back - 0.08, w * 0.7, facing=facing, tex=screen))
    else:
        xf0, xf1 = (x0, x0 + w * step_frac) if facing == "W" else (x1 - w * step_frac, x1)
        xb0, xb1 = (xf1, x1) if facing == "W" else (x0, xf0)
        cy = (y0 + y1) / 2
        parts.append(box((xf0 + xf1) / 2, cy, xf1 - xf0, d, 0.0, h_front, body, bevel=0.015, outline=OL))
        parts.append(box((xb0 + xb1) / 2, cy, xb1 - xb0, d, 0.0, h_back, body, bevel=0.015, outline=OL))
        parts.append(box((xf0 + xf1) / 2, cy, (xf1 - xf0) - 0.08, d - 0.08, h_front, h_front + 0.012, dark))
        sx = xb0 - 0.006 if facing == "W" else xb1 + 0.006
        parts.append(screen_panel(ctx, name + "_scr", sx, cy, h_front + 0.08, h_back - 0.08, d * 0.7, facing=facing, tex=screen))
    return parts


def lab_bench(ctx, name, x0, y0, x1, y1, h=0.9, rgb=(200, 205, 210), top_rgb=(230, 232, 236), seed=0, items=True):
    """Labortisch: Unterschrank mit Schubladen, Arbeitsplatte, darauf Reagenzglasstaender, Kolben, Mikroskop."""
    body = _mat(ctx, name + "_body", rgb)
    top = _mat(ctx, name + "_top", top_rgb)
    drawer = _mat(ctx, name + "_drawer", _shade(rgb, 0.85))
    handle = _mat(ctx, name + "_handle", (90, 94, 100))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w - 0.04, d - 0.04, 0.0, h - 0.04, body, outline=OL), box(cx, cy, w, d, h - 0.04, h, top, bevel=0.01, outline=OL)]
    n = max(1, int(w / 0.5))
    for i in range(n):
        xx = x0 + 0.02 + (w - 0.04) * (i + 0.5) / n
        for j in range(2):
            z = 0.12 + j * (h - 0.3) / 2
            parts.append(box(xx, y0 - 0.004, (w - 0.04) / n - 0.05, 0.008, z, z + (h - 0.3) / 2 - 0.05, drawer, outline=OL))
            parts.append(box(xx, y0 - 0.012, 0.12, 0.012, z + (h - 0.3) / 4, z + (h - 0.3) / 4 + 0.02, handle))
    if items:
        rnd = random.Random(seed)
        glass = ctx.glow(name + "_glass", (170, 220, 230), 0.8)
        liquid = ctx.glow(name + "_liquid", (110, 220, 140), 1.4)
        # Reagenzglasstaender
        rx = x0 + 0.2
        parts.append(box(rx + 0.2, cy, 0.4, 0.14, h, h + 0.03, handle))
        for i in range(5):
            tx = rx + 0.05 + i * 0.08
            parts.append(cyl(tx, cy, 0.018, h + 0.03, h + 0.18, glass, seg=10))
            parts.append(cyl(tx, cy, 0.015, h + 0.03, h + 0.03 + rnd.uniform(0.04, 0.1), liquid, seg=10))
        # Erlenmeyerkolben
        fx = x1 - 0.3
        parts.append(lathe(fx, cy, [(0.0, h), (0.09, h), (0.03, h + 0.14), (0.03, h + 0.2), (0.0, h + 0.2)], glass, seg=14))
        parts.append(lathe(fx, cy, [(0.0, h + 0.002), (0.085, h + 0.002), (0.05, h + 0.07), (0.0, h + 0.07)], liquid, seg=14))
    return parts


def sample_console(ctx, name, cx, cy, yaw=0.0, rgb=(128, 170, 178), dark=(70, 110, 120), screen=None):
    """Probenkonsole (Skeld MedBay "Inspect Sample"): Schrank mit abgeschraegtem Pult, grosser Monitor auf Arm,
    Tastatur, links ein Glaszylinder mit leuchtenden Proben, Ablage mit Pipette."""
    parts = floor_console(ctx, name, cx, cy, 0.62, 0.5, 0.78, body_rgb=rgb, yaw=yaw, screen=None, screen_rgb=(90, 150, 200))
    from bm_spec import rot3
    o = rot3((0.05, 0.05, 0.0), yaw, 0.0)
    parts += monitor(ctx, name + "_mon", cx + o[0], cy + o[1], 0.78, 0.46, 0.36, screen=screen, yaw=yaw, pitch=0.0, stand=True)
    glass = ctx.glow(name + "_glass", (190, 235, 240), 0.9)
    green = ctx.glow(name + "_sample", (90, 230, 110), 2.2)
    g = rot3((-0.4, 0.0, 0.0), yaw, 0.0)
    gx, gy = cx + g[0], cy + g[1]
    parts.append(cyl(gx, gy, 0.14, 0.0, 0.55, _mat(ctx, name + "_pedestal", dark), seg=20, outline=OL))
    parts.append(cyl(gx, gy, 0.12, 0.55, 1.0, glass, seg=20, outline=OL))
    for i in range(3):
        parts.append(cyl(gx, gy, 0.03, 0.62 + i * 0.12, 0.7 + i * 0.12, green, seg=10))
    parts.append(cyl(gx, gy, 0.14, 1.0, 1.05, _mat(ctx, name + "_cap", dark), seg=20, outline=OL))
    return parts


def scanner(ctx, name, cx, cy, r=0.6, rgb=(176, 207, 211), side_rgb=(99, 153, 162), pods=4, glass_tex=None):
    """MedBay-Scanner: flacher Sockel mit Rand, Glasplatte mit leuchtendem Ring, vier niedrige Kapseln (Sensor-Pods)
    mit Lichtschlitz, Kabelkanal am Boden."""
    # Neu 19.10. (User: "Verbessere den Scanner"): runder Sockel mit Stufe, leuchtende Standplatte, hinten ein
    # Scannerbogen (zwei Stuetzen, Querbalken mit Lichtleiste), seitlich ein Steuerpult mit kleinem Schirm; keine Kapseln
    top = _mat(ctx, name + "_top", rgb)
    side = _mat(ctx, name + "_side", side_rgb)
    rim = _mat(ctx, name + "_rim", _shade(side_rgb, 0.8))
    glow = ctx.glow(name + "_ring", (120, 230, 160), 2.0)
    steel = _mat(ctx, name + "_steel", (190, 196, 204))
    parts = [cyl(cx, cy, r, 0.0, 0.06, side, seg=48, outline=OL),
             cyl(cx, cy, r * 0.9, 0.06, 0.12, top, seg=48, bevel=0.02, outline=OL),
             cyl(cx, cy, r * 0.58, 0.12, 0.135, glass_tex or glow, seg=48, top=glass_tex),
             lathe(cx, cy, [(r * 0.58, 0.12), (r * 0.66, 0.12), (r * 0.66, 0.15), (r * 0.58, 0.15)], rim, seg=48)]
    # Scannerbogen auf der Nordseite: Stuetzen bei +-0,7 r, Balken 1,45 hoch mit Lichtleiste nach Sueden
    zb = 1.45
    for sx in (-1, 1):
        parts.append(box(cx + sx * r * 0.7, cy + r * 0.75, 0.1, 0.12, 0.0, zb, steel, bevel=0.01, outline=OL))
    parts.append(box(cx, cy + r * 0.75, r * 1.4 + 0.1, 0.14, zb - 0.12, zb, steel, bevel=0.01, outline=OL))
    parts.append(box(cx, cy + r * 0.75 - 0.075, r * 1.2, 0.012, zb - 0.09, zb - 0.03, glow))
    # Emitter: kleiner Kegel unter dem Balken
    parts.append(lathe(cx, cy + r * 0.75 - 0.03, [(0.0, zb - 0.3), (0.05, zb - 0.14), (0.0, zb - 0.12)], ctx.glow(name + "_emit", (180, 240, 220), 2.4), seg=12))
    # Steuerpult an der Westseite des Sockels
    parts += monitor(ctx, name + "_mon", cx - r * 0.85, cy + r * 0.3, 0.75, 0.3, 0.22, yaw=90.0, stand=True)
    parts.append(box(cx - r * 0.85, cy + r * 0.3, 0.18, 0.18, 0.0, 0.75, side, outline=OL))
    return parts


def console_block(ctx, name, x0, y0, x1, y1, h, rgb=(96, 104, 112), screens=1, facing="S", lights=True, seed=0,
                  screen_rgbs=None):
    """Allgemeine Geraetekonsole/Schrank: Korpus mit Fase, Sockel, Deckplatte, ein bis drei eingelassene Anzeigen auf
    der Seite facing (S/N/E/W), Statusleuchten, Lueftungsfeld unten; fuer alles, was sonst nur ein Kasten mit Bild
    waere."""
    body = _mat(ctx, name + "_body", rgb)
    dark = _mat(ctx, name + "_dark", _shade(rgb, 0.7))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w - 0.04, d - 0.04, 0.0, 0.05, dark), box(cx, cy, w, d, 0.05, h, body, bevel=0.015, outline=OL),
             box(cx, cy, w - 0.06, d - 0.06, h, h + 0.01, dark)]
    along = w if facing in ("S", "N") else d
    lo = x0 if facing in ("S", "N") else y0
    fpos = {"S": y0 - 0.006, "N": y1 + 0.006, "W": x0 - 0.006, "E": x1 + 0.006}[facing]
    cols = screen_rgbs or [(120, 190, 200), (90, 160, 120), (200, 160, 80)]

    def at(c, zz0, zz1, ww, depth, mat, face=False):
        if facing in ("S", "N"):
            b_ = box(c, fpos, ww, depth, zz0, zz1, mat)
        else:
            b_ = box(fpos, c, depth, ww, zz0, zz1, mat)
        if face:
            b_[{"S": "front", "N": "face_n", "E": "face_e", "W": "face_w"}[facing]] = mat
        return b_
    for i in range(screens):
        c = lo + along * (i + 0.5) / screens
        sm = ctx.glow(f"{name}_scr{i}", cols[i % len(cols)], 1.3)
        parts.append(at(c, h * 0.53, h * 0.9, along / screens - 0.06, 0.006, dark))
        parts.append(at(c, h * 0.55, h * 0.88, along / screens - 0.08, 0.012, sm, face=True))
    if lights:
        for i in range(3):
            lm = ctx.glow(f"{name}_led{i}", [(240, 70, 70), (240, 200, 60), (80, 220, 100)][i], 2.0)
            parts.append(at(lo + 0.06 + i * 0.05, h * 0.3, h * 0.3 + 0.025, 0.025, 0.012, lm))
    parts.append(at(lo + along / 2, h * 0.1, h * 0.26, along - 0.1, 0.008, dark))
    return parts


def chair_simple(ctx, name, cx, cy, yaw=0.0, rgb=(70, 74, 90), w=0.42, seat_z=0.42):
    """Stuhl: vier Beine, Sitz, Lehne (Richtung yaw = Lehne hinten)."""
    body = _mat(ctx, name + "_body", rgb)
    from bm_spec import rot3
    parts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        o = rot3((sx * w * 0.4, sy * w * 0.4, 0.0), yaw, 0.0)
        parts.append(box(cx + o[0], cy + o[1], 0.035, 0.035, 0.0, seat_z - 0.03, body))
    parts.append(obox((cx, cy, seat_z - 0.015), (w, w, 0.03), body, yaw=yaw, outline=OL))
    o = rot3((0.0, w * 0.45, 0.0), yaw, 0.0)
    parts.append(obox((cx + o[0], cy + o[1], seat_z + 0.2), (w, 0.04, 0.4), body, yaw=yaw, outline=OL))
    return parts


def mop(ctx, name, cx, cy, h=1.3, lean=12.0):
    """Wischmopp an der Wand: Stiel (leicht geneigt), Moppkopf aus Fransen, Eimer daneben."""
    stick = _mat(ctx, name + "_stick", (150, 110, 70))
    head = _mat(ctx, name + "_head", (200, 196, 180))
    bucket = _mat(ctx, name + "_bucket", (180, 40, 50))
    dz = math.tan(math.radians(lean)) * h
    parts = [tube([(cx, cy, 0.05), (cx + dz * 0.3, cy + dz, h)], 0.018, stick, seg=8)]
    for i in range(7):
        a = i / 7 * math.pi * 2
        parts.append(tube([(cx, cy, 0.12), (cx + math.cos(a) * 0.07, cy + math.sin(a) * 0.07, 0.0)], 0.014, head, seg=6))
    parts.append(lathe(cx + 0.22, cy, [(0.0, 0.0), (0.11, 0.0), (0.13, 0.26), (0.0, 0.26)], bucket, seg=16, outline=OL))
    return parts


def laptop(ctx, name, cx, cy, z, yaw=0.0, w=0.3, rgb=(60, 64, 72), screen_rgb=(120, 200, 180)):
    """Laptop: Unterteil mit Tastenfeld, aufgeklappter Deckel mit leuchtendem Schirm."""
    body = _mat(ctx, name + "_body", rgb)
    keys = _mat(ctx, name + "_keys", _shade(rgb, 0.75))
    scr = ctx.glow(name + "_screen", screen_rgb, 1.5)
    from bm_spec import rot3
    parts = [obox((cx, cy, z + 0.01), (w, w * 0.7, 0.02), body, yaw=yaw, outline=OL),
             obox((cx, cy, z + 0.021), (w * 0.8, w * 0.4, 0.004), keys, yaw=yaw)]
    o = rot3((0.0, w * 0.33, 0.0), yaw, 0.0)
    parts.append(obox((cx + o[0], cy + o[1], z + 0.02 + w * 0.3), (w, 0.015, w * 0.62), body, yaw=yaw, roll=20.0, outline=OL))
    o2 = rot3((0.0, w * 0.33 - 0.012, 0.0), yaw, 0.0)
    parts.append(obox((cx + o2[0], cy + o2[1], z + 0.02 + w * 0.3), (w * 0.9, 0.006, w * 0.52), scr, yaw=yaw, roll=20.0))
    return parts


def microscope(ctx, name, cx, cy, z, rgb=(70, 74, 86)):
    """Mikroskop: Fuss, Saeule, geneigter Tubus, Objektivrevolver, Objekttisch."""
    body = _mat(ctx, name + "_body", rgb)
    light = _mat(ctx, name + "_light", _shade(rgb, 1.5))
    parts = [lathe(cx, cy, [(0.0, z), (0.09, z), (0.07, z + 0.02), (0.0, z + 0.02)], body, seg=16, outline=OL),
             tube([(cx, cy + 0.05, z + 0.02), (cx, cy + 0.05, z + 0.22)], 0.015, body, seg=8),
             box(cx, cy - 0.01, 0.1, 0.08, z + 0.1, z + 0.115, light),
             tube([(cx, cy + 0.04, z + 0.2), (cx, cy - 0.04, z + 0.3)], 0.022, body, seg=10, outline=OL),
             lathe(cx, cy - 0.02, [(0.0, z + 0.13), (0.03, z + 0.13), (0.03, z + 0.16), (0.0, z + 0.16)], body, seg=10)]
    return parts


def gas_pump(ctx, name, x0, y0, x1, y1, h=1.8, rgb=(110, 120, 125)):
    """Zapfsaeule (LaunchPad/Storage): Konsolenkorpus mit Anzeige, Zapfschlauch seitlich, Griff."""
    parts = console_block(ctx, name, x0, y0, x1, y1, h, rgb=rgb, screens=1, lights=True)
    hose = _mat(ctx, name + "_hose", (40, 40, 44))
    nozzle = _mat(ctx, name + "_nozzle", (200, 60, 60))
    parts.append(tube([(x1, (y0 + y1) / 2, h * 0.7), (x1 + 0.1, (y0 + y1) / 2, h * 0.5), (x1 + 0.05, (y0 + y1) / 2, h * 0.3),
                       (x1 + 0.02, y0 - 0.02, h * 0.45)], 0.02, hose, seg=8))
    parts.append(box(x1 + 0.02, y0 - 0.03, 0.05, 0.06, h * 0.42, h * 0.5, nozzle, outline=OL))
    return parts


def engine_pod(ctx, name, cx, y0, y1, zc, r, rgb=(104, 124, 123), dark=(41, 48, 49), fan_rgb=(148, 162, 165)):
    """Seitentriebwerk (Mira LaunchPad): liegender Zylinder entlang y, Einlauf mit Luefter vorn (Sueden), Duese hinten,
    Streben zum Boden."""
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", dark)
    parts = [tube([(cx, y0 + 0.2, zc), (cx, y1 - 0.2, zc)], r, body, seg=28, outline=OL),
             lathe(cx, y0 + 0.2, [(0.0, zc - 0.0001), (r * 1.05, zc - 0.0001), (r * 1.05, zc + 0.16), (r * 0.9, zc + 0.16), (0.0, zc + 0.16)], dk, seg=28,
                   tilt=(-90.0, 90.0, zc)),
             lathe(cx, y1 - 0.2, [(0.0, zc), (r * 0.75, zc), (r * 0.95, zc + 0.25), (0.0, zc + 0.3)], dk, seg=28, tilt=(90.0, 90.0, zc))]
    parts += fan_unit(ctx, name + "_fan", cx, y0 + 0.14, zc, r=r * 0.8, yaw=90.0, rgb=fan_rgb, blade_rgb=dark)
    for sy in (y0 + 0.45, y1 - 0.45):
        for sx in (-1, 1):
            parts.append(tube([(cx + sx * r * 0.6, sy, zc - r * 0.7), (cx + sx * r * 0.85, sy, 0.0)], 0.05, dk, seg=8))
    return parts


def container(ctx, name, x0, y0, x1, y1, h, rgb=(52, 84, 74), dark=None, ribs=True, doors="S"):
    """Frachtcontainer: Korpus, senkrechte Sicken auf allen Seiten, Eckbeschlaege, Tuerfuge und zwei Verschluss-
    stangen auf der Seite doors."""
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", dark or _shade(rgb, 0.72))
    edge = _mat(ctx, name + "_edge", _shade(rgb, 0.55))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, 0.0, h, body, bevel=0.01, outline=OL)]
    for fx in (x0 + 0.04, x1 - 0.04):
        for fy in (y0 + 0.04, y1 - 0.04):
            parts.append(box(fx, fy, 0.08, 0.08, 0.0, h, edge))
    if ribs:
        n = max(2, int(w / 0.22))
        for i in range(1, n):
            xx = x0 + w * i / n
            parts.append(box(xx, y0 - 0.012, 0.05, 0.024, 0.08, h - 0.08, dk))
            parts.append(box(xx, y1 + 0.012, 0.05, 0.024, 0.08, h - 0.08, dk))
        n2 = max(2, int(d / 0.22))
        for i in range(1, n2):
            yy = y0 + d * i / n2
            parts.append(box(x0 - 0.012, yy, 0.024, 0.05, 0.08, h - 0.08, dk))
            parts.append(box(x1 + 0.012, yy, 0.024, 0.05, 0.08, h - 0.08, dk))
    if doors:
        fy = y0 - 0.02 if doors == "S" else y1 + 0.02
        parts.append(box(cx, fy, 0.02, 0.03, 0.06, h - 0.06, edge))
        for dx in (-w * 0.2, w * 0.2):
            parts.append(box(cx + dx, fy - (0.01 if doors == "S" else -0.01), 0.03, 0.03, 0.1, h - 0.1, edge))
            parts.append(box(cx + dx + 0.05, fy - (0.02 if doors == "S" else -0.02), 0.08, 0.02, h * 0.45, h * 0.45 + 0.03, dk))
    return parts


def tv_unit(ctx, name, cx, cy, w, h, z_cab=0.48, facing="E", rgb=(123, 117, 96), screen_rgb=(60, 140, 120), depth=0.55):
    """Fernsehschrank: niedriger Schrank mit Tuerfugen, darauf ein grosser Bildschirm (Rahmen, leuchtender Schirm) zur
    Seite facing."""
    yaw = {"S": 0.0, "E": 90.0, "N": 180.0, "W": 270.0}[facing]       # Front -y bei yaw 0, yaw gegen den Uhrzeiger
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", _shade(rgb, 0.7))
    along_x = facing in ("S", "N")
    sx, sy = (w, depth) if along_x else (depth, w)
    parts = [box(cx, cy, sx, sy, 0.0, z_cab, body, bevel=0.015, outline=OL),
             box(cx, cy, sx - 0.06, sy - 0.06, z_cab, z_cab + 0.01, dk)]
    parts += monitor(ctx, name + "_tv", cx, cy, z_cab, w - 0.1, h, yaw=yaw, pitch=0.0, stand=True, screen_rgb=screen_rgb, glow=1.3)
    return parts


# ------------------------------------------------------------------------------------------- Airship (19.10.)

def _fx(yaw):
    """Hilfe: lokale Verschiebung (lx, ly, lz) -> Welt bei Drehung yaw (Front = -y lokal)."""
    from bm_spec import rot3

    def f(lx, ly, lz=0.0):
        return rot3((lx, ly, lz), yaw, 0.0)
    return f


def arch_bookcase(ctx, name, cx, cy, w, d, h, yaw=0.0, rgb=(170, 62, 70), dark=(120, 40, 50), shelf_rgb=(200, 205, 210),
                  rows=3, seed=0, arch=True):
    """Aktenregal mit Rundbogen-Oberseite (Airship Records): Korpus, gewoelbter Deckel aus Stufen, Boeden mit bunten
    Ordnern, gelbes Namensschild, Sockel. Front zur -y-Seite (yaw 0), gedreht um yaw."""
    rnd = random.Random(seed)
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", dark)
    shelf = _mat(ctx, name + "_shelf", shelf_rgb)
    f = _fx(yaw)
    parts = []
    hb = h * 0.82 if arch else h                                        # Korpus bis zum Bogenansatz
    parts.append(obox((cx, cy, hb / 2), (w, d, hb), body, yaw=yaw, outline=OL))
    n = 5 if arch else 0                                                # Rundbogen aus Stufen, nach oben schmaler
    for i in range(n):
        t = (i + 0.5) / n
        ww = w * math.sqrt(max(0.0, 1 - t * t))
        z0, z1 = hb + (h - hb) * i / n, hb + (h - hb) * (i + 1) / n
        parts.append(obox((cx, cy, (z0 + z1) / 2), (ww, d, z1 - z0), body, yaw=yaw, outline=OL))
    parts.append(obox((cx, cy, 0.03), (w + 0.08, d + 0.08, 0.06), dk, yaw=yaw, outline=OL))
    nw, nd = w * 0.8, 0.22                                              # Nische mit Boeden an der Front
    o = f(0, -d / 2 + nd / 2 + 0.005)
    parts.append(obox((cx + o[0], cy + o[1], hb * 0.5), (nw, nd, hb * 0.78), dk, yaw=yaw))
    cols = ((220, 70, 70), (240, 200, 60), (70, 170, 90), (230, 230, 230), (90, 130, 220), (240, 140, 60))
    for r in range(rows):
        zs = hb * 0.12 + r * (hb * 0.76 / rows)
        o = f(0, -d / 2 + nd / 2)
        parts.append(obox((cx + o[0], cy + o[1], zs), (nw, nd, 0.025), shelf, yaw=yaw, outline=OL))
        nb = max(4, int(nw / 0.11))
        bw = nw / nb
        for b in range(nb):
            c = cols[rnd.randrange(len(cols))]
            lx = -nw / 2 + (b + 0.5) * bw
            bh = hb * 0.76 / rows * (0.62 + 0.18 * rnd.random())
            o = f(lx, -d / 2 + 0.06)
            parts.append(obox((cx + o[0], cy + o[1], zs + 0.0125 + bh / 2), (bw - 0.012, 0.11, bh),
                              _mat(ctx, f"{name}_b{r}_{b}", c), yaw=yaw, outline=OL))
    o = f(0, -d / 2 - 0.006)
    parts.append(obox((cx + o[0], cy + o[1], hb * 0.93), (w * 0.3, 0.012, 0.08), _mat(ctx, name + "_sign", (236, 204, 60)), yaw=yaw))
    return parts


def security_desk(ctx, name, cx, cy, w, d, h=0.8, rgb=(52, 51, 52), screens=4, screen_rgb=(120, 200, 200)):
    """Kamerapult (Airship Security): schwarzer Tisch mit Kabelkanal, vier Monitore im Faecher an der Rueckkante
    (zur Front geneigt), zwei seitliche Monitore schraeg, Tastatur. Front = -y."""
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", _shade(rgb, 0.7))
    parts = [box(cx, cy, w, d, 0.0, h, body, bevel=0.02, outline=OL),
             box(cx, cy + d * 0.3, w * 0.9, 0.06, h, h + 0.02, dk)]
    for i in range(screens):                                            # Faecher: links nach Suedost, rechts nach Suedwest
        t = (i + 0.5) / screens - 0.5
        mx = cx + t * w * 0.82
        yaw = -t * 70.0                                                 # Front -y: positiver yaw dreht nach Osten
        parts += monitor(ctx, f"{name}_m{i}", mx, cy + d * 0.32, h, w / screens * 0.8, 0.32, yaw=yaw, pitch=-10.0,
                         screen_rgb=screen_rgb, stand=True)
    for sx, yaw in ((-1, 55.0), (1, -55.0)):
        parts += monitor(ctx, f"{name}_s{sx + 1}", cx + sx * (w / 2 + 0.12), cy - d * 0.1, h * 0.5, 0.34, 0.26, yaw=yaw,
                         pitch=-6.0, screen_rgb=screen_rgb, stand=True)
    parts.append(box(cx, cy - d * 0.25, w * 0.4, 0.14, h, h + 0.02, dk, bevel=0.005))
    return parts


def tape_machine(ctx, name, cx, cy, w, d, h=1.0, rgb=(87, 93, 102), light=(140, 146, 151), screen_rgb=(90, 210, 120)):
    """Bandgeraet (Airship Security): Mittelsaeule, zwei schraeg nach vorn gestellte Fluegel mit gruenen Anzeigen,
    aussen zwei Schaltfelder, Sockel mit Stufe. Front = -y."""
    from bm_spec import rot3
    body = _mat(ctx, name + "_body", rgb)
    lt = _mat(ctx, name + "_light", light)
    scr = ctx.glow(name + "_screen", screen_rgb, 1.4)
    key = _mat(ctx, name + "_key", (60, 64, 70))
    parts = [box(cx, cy + d * 0.1, w * 0.95, d * 0.8, 0.0, 0.1, _mat(ctx, name + "_base", _shade(rgb, 0.6)), bevel=0.01, outline=OL),
             box(cx, cy + d * 0.15, w * 0.3, d * 0.7, 0.1, h, body, bevel=0.015, outline=OL),
             box(cx, cy - d * 0.2, w * 0.3, d * 0.3, 0.1, h * 0.55, lt, bevel=0.015, outline=OL)]
    for sx in (-1, 1):
        yaw = -sx * 38.0
        wx, wy = cx + sx * w * 0.3, cy + d * 0.05
        parts.append(obox((wx, wy, 0.1 + (h - 0.1) * 0.5), (w * 0.34, 0.12, h - 0.1), body, yaw=yaw, outline=OL))
        o = rot3((0.0, -0.065, 0.0), yaw, 0.0)
        parts.append(obox((wx + o[0], wy + o[1], 0.1 + (h - 0.1) * 0.55), (w * 0.26, 0.012, (h - 0.1) * 0.55), scr, yaw=yaw))
        px = cx + sx * (w * 0.5 - 0.04)
        parts.append(box(px, cy + d * 0.05, 0.08, d * 0.45, 0.1, h * 0.9, lt, bevel=0.01, outline=OL))
        for j in range(4):
            parts.append(box(px - sx * 0.045, cy + d * 0.05 - d * 0.15 + j * d * 0.1, 0.01, 0.05, h * 0.5, h * 0.52, key))
    return parts


def cargo_net(ctx, name, x0, y0, x1, y1, h, rgb=(145, 112, 77), dark=(132, 94, 66), net=(211, 181, 71), seed=0,
              cells=(3, 3)):
    """Frachtstapel mit Netz (Airship Storage): Kistenblock mit Fase und Fugen, darueber ein gelbes Netz aus Rohren
    (ueber die Oberseite und an den Seiten herab), Zurrringe am Boden."""
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", dark)
    rope = _mat(ctx, name + "_net", net)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, 0.0, h, body, bevel=0.02, outline=OL)]
    if h > 0.6:
        parts.append(box(cx, cy, w + 0.004, d + 0.004, h * 0.5 - 0.01, h * 0.5 + 0.01, dk))
    nx = max(1, int(w / 0.8))
    for i in range(1, nx):
        parts.append(box(x0 + w * i / nx, cy, 0.012, d + 0.004, 0.04, h - 0.04, dk))
    r = 0.016
    nxc, nyc = cells
    for i in range(nxc + 1):
        xx = x0 + 0.05 + (w - 0.1) * i / nxc
        parts.append(tube([(xx, y0 - 0.02, 0.02), (xx, y0 - 0.02, h + 0.02), (xx, y1 + 0.02, h + 0.02), (xx, y1 + 0.02, 0.02)], r, rope, seg=6))
    for j in range(nyc + 1):
        yy = y0 + 0.05 + (d - 0.1) * j / nyc
        parts.append(tube([(x0 - 0.02, yy, 0.02), (x0 - 0.02, yy, h + 0.02), (x1 + 0.02, yy, h + 0.02), (x1 + 0.02, yy, 0.02)], r, rope, seg=6))
    ring = _mat(ctx, name + "_ring", (90, 90, 96))
    for fx, fy in ((x0 - 0.02, y0 - 0.02), (x1 + 0.02, y0 - 0.02), (x0 - 0.02, y1 + 0.02), (x1 + 0.02, y1 + 0.02)):
        parts.append(cyl(fx, fy, 0.035, 0.0, 0.03, ring, seg=10))
    return parts


def safe_box(ctx, name, cx, cy, w, d, h, rgb=(214, 161, 55), dark=(195, 108, 41), facing="S"):
    """Tresor (Airship Storage): Korpus, Tuer mit Fuge auf der Seite facing, Drehgriff mit drei Speichen, Scharniere,
    Sockel."""
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", dark)
    steel = _mat(ctx, name + "_steel", (120, 118, 110))
    yaw = {"S": 0.0, "E": 90.0, "N": 180.0, "W": 270.0}[facing]
    f = _fx(yaw)
    parts = [obox((cx, cy, 0.04), (w + 0.04, d + 0.04, 0.08), dk, yaw=yaw, outline=OL),
             obox((cx, cy, h / 2), (w, d, h), body, yaw=yaw, outline=OL)]
    o = f(0, -d / 2 - 0.008)
    parts.append(obox((cx + o[0], cy + o[1], h / 2), (w - 0.1, 0.016, h - 0.14), dk, yaw=yaw, outline=OL))
    o = f(w * 0.08, -d / 2 - 0.03)
    parts.append(obox((cx + o[0], cy + o[1], h * 0.55), (0.06, 0.03, 0.06), steel, yaw=yaw))
    for a in (0, 120, 240):
        o2 = f(w * 0.08 + 0.09 * math.cos(math.radians(a)), -d / 2 - 0.045, 0.09 * math.sin(math.radians(a)))
        parts.append(obox((cx + o2[0], cy + o2[1], h * 0.55 + o2[2]), (0.02, 0.02, 0.1), steel, yaw=yaw, pitch=90.0 - a))
    for zz in (h * 0.25, h * 0.75):
        o = f(-w / 2 + 0.02, -d / 2 - 0.012)
        parts.append(obox((cx + o[0], cy + o[1], zz), (0.04, 0.024, 0.08), steel, yaw=yaw))
    return parts


def kitchen_counter(ctx, name, x0, y0, x1, y1, h=0.75, rgb=(123, 142, 148), top_rgb=(165, 182, 189), stove="E", sink=False,
                    board=True, seed=0):
    """Kuechenzeile (Airship Kitchen): Korpus mit Schubladenfugen und Griffen, Arbeitsplatte, Kochfeld (schwarz, vier
    Brennerringe, Pfanne) auf der Seite stove (E/W/None), Spuele mit Hahn, Schneidbrett mit Messer, Messerblock."""
    body = _mat(ctx, name + "_body", rgb)
    top = _mat(ctx, name + "_top", top_rgb)
    dk = _mat(ctx, name + "_dark", _shade(rgb, 0.65))
    black = _mat(ctx, name + "_hob", (30, 32, 36))
    ring = _mat(ctx, name + "_ring", (110, 112, 118))
    handle = _mat(ctx, name + "_handle", (200, 205, 210))
    grip = _mat(ctx, name + "_grip", (40, 30, 30))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, 0.0, h - 0.04, body, bevel=0.01, outline=OL),
             box(cx, cy, w + 0.03, d + 0.03, h - 0.04, h, top, bevel=0.012, outline=OL)]
    n = max(2, int(w / 0.55))
    for i in range(n):
        xx = x0 + w * (i + 0.5) / n
        parts.append(box(xx, y0 - 0.006, w / n - 0.06, 0.012, 0.08, h - 0.1, dk))
        parts.append(box(xx, y0 - 0.02, 0.12, 0.02, h * 0.55, h * 0.57, handle))
    zt = h
    if stove:
        sx0 = x1 - w * 0.4 if stove == "E" else x0 + 0.03
        sx1 = x1 - 0.03 if stove == "E" else x0 + w * 0.4
        parts.append(box((sx0 + sx1) / 2, cy, sx1 - sx0, d * 0.8, zt, zt + 0.015, black, outline=OL))
        for i in range(2):
            for j in range(2):
                bx = sx0 + (sx1 - sx0) * (0.28 + 0.44 * i)
                by = cy + d * 0.8 * (-0.25 + 0.5 * j)
                parts.append(lathe(bx, by, [(0.0, zt + 0.015), (0.06, zt + 0.015), (0.07, zt + 0.03), (0.055, zt + 0.03),
                                            (0.05, zt + 0.02), (0.0, zt + 0.02)], ring, seg=16))
        pan = _mat(ctx, name + "_pan", (60, 40, 36))
        px, py = sx0 + (sx1 - sx0) * 0.72, cy + d * 0.8 * 0.25
        parts.append(lathe(px, py, [(0.0, zt + 0.03), (0.1, zt + 0.03), (0.11, zt + 0.07), (0.09, zt + 0.07), (0.085, zt + 0.04),
                                    (0.0, zt + 0.04)], pan, seg=20, outline=OL))
        parts.append(tube([(px + 0.1, py, zt + 0.06), (px + 0.3, py + 0.02, zt + 0.08)], 0.012, pan, seg=6))
    if sink:
        kx0 = x0 + w * 0.3 if stove == "E" else x0 + w * 0.5
        kx1 = kx0 + 0.45
        parts.append(box((kx0 + kx1) / 2, cy, kx1 - kx0, d * 0.5, zt - 0.1, zt + 0.004, _mat(ctx, name + "_basin", (140, 160, 168)),
                         outline=OL))
        tap = _mat(ctx, name + "_tap", (190, 196, 200))
        parts.append(tube([((kx0 + kx1) / 2, y1 - 0.08, zt), ((kx0 + kx1) / 2, y1 - 0.08, zt + 0.2), ((kx0 + kx1) / 2, y1 - 0.2, zt + 0.2)],
                          0.012, tap, seg=8))
    if board:
        bx = x0 + w * 0.22
        wood = _mat(ctx, name + "_board", (190, 140, 90))
        parts.append(box(bx, cy - d * 0.05, 0.3, 0.22, zt, zt + 0.02, wood, bevel=0.004, outline=OL))
        parts.append(box(bx + 0.02, cy + d * 0.05, 0.22, 0.03, zt + 0.02, zt + 0.03, _mat(ctx, name + "_knife", (210, 214, 220))))
        parts.append(box(bx + 0.17, cy + d * 0.05, 0.08, 0.03, zt + 0.02, zt + 0.035, grip))
        kb = _mat(ctx, name + "_block", (120, 80, 50))
        parts.append(box(x0 + 0.1, y1 - 0.14, 0.1, 0.14, zt, zt + 0.16, kb, outline=OL))
        for i in range(3):
            parts.append(box(x0 + 0.06 + i * 0.03, y1 - 0.12, 0.012, 0.03, zt + 0.16, zt + 0.22, grip))
    return parts


def chest(ctx, name, cx, cy, w, d, h, rgb=(110, 70, 45), top_rgb=(140, 95, 60), band=(70, 72, 84), facing="S"):
    """Schatztruhe (Airship Main Hall): Korpus, gewoelbter Deckel aus Stufen, zwei Metallbaender, Schloss vorn
    (Seite facing)."""
    body = _mat(ctx, name + "_body", rgb)
    top = _mat(ctx, name + "_top", top_rgb)
    bd = _mat(ctx, name + "_band", band)
    yaw = {"S": 0.0, "E": 90.0, "N": 180.0, "W": 270.0}[facing]
    f = _fx(yaw)
    hb = h * 0.6
    parts = [obox((cx, cy, hb / 2), (w, d, hb), body, yaw=yaw, outline=OL)]
    n = 4
    for i in range(n):
        t = (i + 0.5) / n
        dd = d * math.sqrt(max(0.0, 1 - t * t))
        z0, z1 = hb + (h - hb) * i / n, hb + (h - hb) * (i + 1) / n
        parts.append(obox((cx, cy, (z0 + z1) / 2), (w, dd, z1 - z0), top, yaw=yaw, outline=OL))
    for lx in (-w * 0.3, w * 0.3):
        o = f(lx, 0)
        parts.append(obox((cx + o[0], cy + o[1], h * 0.5), (0.05, d + 0.02, h + 0.01), bd, yaw=yaw))
    o = f(0, -d / 2 - 0.012)
    parts.append(obox((cx + o[0], cy + o[1], hb), (0.08, 0.024, 0.1), bd, yaw=yaw, outline=OL))
    return parts


def display_case(ctx, name, x0, y0, x1, y1, h=0.7, rgb=(60, 66, 79), glass=(209, 224, 225), items="rifles", seed=0):
    """Vitrine (Airship Armory): Unterschrank mit Schubladen und Griffen, Glasaufsatz (Rahmenstangen, helle Scheiben),
    darin zwei Gewehre auf Haltern."""
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", _shade(rgb, 0.7))
    gl = ctx.glow(name + "_glass", glass, 0.55)
    frame = _mat(ctx, name + "_frame", (40, 44, 52))
    handle = _mat(ctx, name + "_handle", (190, 194, 200))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hb = h * 0.55
    parts = [box(cx, cy, w, d, 0.0, hb, body, bevel=0.01, outline=OL)]
    n = max(2, int(w / 0.45))
    for i in range(n):
        xx = x0 + w * (i + 0.5) / n
        parts.append(box(xx, y0 - 0.006, w / n - 0.05, 0.012, hb * 0.3, hb * 0.8, dk))
        parts.append(box(xx, y0 - 0.018, 0.1, 0.014, hb * 0.55, hb * 0.57, handle))
    for fx in (x0 + 0.02, x1 - 0.02):
        for fy in (y0 + 0.02, y1 - 0.02):
            parts.append(box(fx, fy, 0.03, 0.03, hb, h, frame))
    parts.append(box(cx, cy, w, d, h - 0.02, h, gl, bevel=0.005, outline=OL))
    parts.append(box(cx, y0 + 0.01, w - 0.06, 0.01, hb, h - 0.02, gl))
    parts.append(box(cx, y1 - 0.01, w - 0.06, 0.01, hb, h - 0.02, gl))
    parts.append(box(x0 + 0.01, cy, 0.01, d - 0.06, hb, h - 0.02, gl))
    parts.append(box(x1 - 0.01, cy, 0.01, d - 0.06, hb, h - 0.02, gl))
    if items == "rifles":
        gun = _mat(ctx, name + "_gun", (60, 50, 40))
        steel = _mat(ctx, name + "_steel", (120, 124, 130))
        for yy in (cy - d * 0.22, cy + d * 0.22):
            zz = hb + 0.05
            parts.append(obox((cx - w * 0.1, yy, zz), (w * 0.5, 0.025, 0.04), gun, yaw=0.0, outline=OL))
            parts.append(obox((cx + w * 0.22, yy, zz + 0.005), (w * 0.35, 0.018, 0.018), steel, yaw=0.0))
            parts.append(obox((cx - w * 0.3, yy, zz - 0.02), (w * 0.12, 0.03, 0.06), gun, yaw=0.0, pitch=-20.0, outline=OL))
            for hx in (cx - w * 0.2, cx + w * 0.2):
                parts.append(box(hx, yy, 0.02, 0.03, hb, zz, frame))
    return parts


def pool_table(ctx, name, x0, y0, x1, y1, h=0.7, felt=(40, 110, 60), wood=(90, 60, 40), seed=0):
    """Billardtisch (Airship Lounge): Korpus, Filzplatte, Holzbande rundum, sechs Taschen, Kugeln, Queue."""
    rnd = random.Random(seed)
    wd = _mat(ctx, name + "_wood", wood)
    fl = _mat(ctx, name + "_felt", felt)
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, 0.0, h - 0.08, wd, bevel=0.02, outline=OL),
             box(cx, cy, w - 0.16, d - 0.16, h - 0.08, h - 0.03, fl)]
    for fx in (x0 + 0.08, x1 - 0.08):
        for fy in (y0 + 0.08, y1 - 0.08):
            parts.append(box(fx, fy, 0.09, 0.09, 0.0, 0.04, wd))
    parts.append(box(cx, y0 + 0.04, w, 0.08, h - 0.08, h, wd, bevel=0.01, outline=OL))
    parts.append(box(cx, y1 - 0.04, w, 0.08, h - 0.08, h, wd, bevel=0.01, outline=OL))
    parts.append(box(x0 + 0.04, cy, 0.08, d, h - 0.08, h, wd, bevel=0.01, outline=OL))
    parts.append(box(x1 - 0.04, cy, 0.08, d, h - 0.08, h, wd, bevel=0.01, outline=OL))
    pocket = _mat(ctx, name + "_pocket", (20, 20, 24))
    xs = (x0 + 0.09, cx, x1 - 0.09) if w >= d else (x0 + 0.09, x1 - 0.09)
    ys = (y0 + 0.09, y1 - 0.09) if w >= d else (y0 + 0.09, cy, y1 - 0.09)
    for px in xs:
        for py in ys:
            parts.append(cyl(px, py, 0.045, h - 0.1, h - 0.029, pocket, seg=12))
    cols = ((230, 230, 230), (220, 50, 50), (240, 200, 50), (60, 80, 200), (40, 40, 40))
    for i in range(4):
        bx = x0 + 0.2 + rnd.random() * (w - 0.4)
        by = y0 + 0.2 + rnd.random() * (d - 0.4)
        bm = _mat(ctx, f"{name}_ball{i}", cols[i % len(cols)])
        parts.append(lathe(bx, by, [(0.0, h - 0.03), (0.02, h - 0.02), (0.028, h), (0.02, h + 0.02), (0.0, h + 0.03)], bm, seg=12))
    cue = _mat(ctx, name + "_cue", (190, 150, 90))
    parts.append(tube([(x0 + 0.15, y0 + 0.25, h + 0.02), (x1 - 0.2, y1 - 0.3, h + 0.02)], 0.012, cue, seg=6))
    return parts


def exhaust_bowl(ctx, name, cx, cy, r, h, z0=0.0, rgb=(73, 84, 97), rim=(118, 139, 156)):
    """Abgasschale (Airship Gap Room): sich weitende Schale mit hellem Rand und dunklem Inneren."""
    body = _mat(ctx, name + "_body", rgb)
    rm = _mat(ctx, name + "_rim", rim)
    dark = _mat(ctx, name + "_inner", (28, 32, 38))
    return [lathe(cx, cy, [(0.0, z0), (r * 0.7, z0), (r * 0.72, z0 + 0.04), (r * 0.95, z0 + h * 0.9), (r, z0 + h)], body, seg=32, outline=OL),
            lathe(cx, cy, [(r * 0.8, z0 + h - 0.001), (r * 1.02, z0 + h - 0.001), (r * 1.02, z0 + h + 0.03), (r * 0.8, z0 + h + 0.03)], rm,
                  seg=32, outline=OL),
            lathe(cx, cy, [(0.0, z0 + h * 0.4), (r * 0.8, z0 + h * 0.4), (r * 0.8, z0 + h * 0.4 + 0.001), (0.0, z0 + h * 0.4 + 0.001)], dark,
                  seg=32)]


def scale_device(ctx, name, cx, cy, yaw=0.0, rgb=(189, 184, 176), dark=(36, 39, 41)):
    """Personenwaage mit Saeule (Airship Medbay): Trittplatte, Saeule, geneigter Anzeigekopf mit Skala."""
    body = _mat(ctx, name + "_body", rgb)
    dk = _mat(ctx, name + "_dark", dark)
    f = _fx(yaw)
    parts = [obox((cx, cy, 0.04), (0.5, 0.42, 0.08), dk, yaw=yaw, outline=OL),
             obox((cx, cy, 0.09), (0.46, 0.38, 0.02), body, yaw=yaw, outline=OL)]
    o = f(0, 0.17)
    parts.append(obox((cx + o[0], cy + o[1], 0.55), (0.05, 0.05, 0.9), body, yaw=yaw, outline=OL))
    o = f(0, 0.14)
    parts.append(obox((cx + o[0], cy + o[1], 1.03), (0.22, 0.1, 0.14), dk, yaw=yaw, roll=-25.0, outline=OL))
    o = f(0, 0.09)
    parts.append(obox((cx + o[0], cy + o[1], 1.04), (0.16, 0.012, 0.09), ctx.glow(name + "_dial", (220, 225, 230), 0.8), yaw=yaw, roll=-25.0))
    return parts


def weapon_stand(ctx, name, cx, cy, kind="sword", ped_rgb=(185, 192, 200), yaw=0.0, z0=0.0):
    """Waffe auf Staender (Airship Vault): Sockelblock, Haltearm, darauf Schwert (Klinge, Parierstange, Griff) oder
    Pistole (Lauf, Griff, Abzug) in Gold."""
    ped = _mat(ctx, name + "_ped", ped_rgb)
    arm = _mat(ctx, name + "_arm", (90, 94, 104))
    parts = [obox((cx, cy, z0 + 0.17), (0.34, 0.26, 0.34), ped, yaw=yaw, outline=OL),
             obox((cx, cy, z0 + 0.35), (0.38, 0.3, 0.02), _mat(ctx, name + "_cap", _shade(ped_rgb, 0.8)), yaw=yaw, outline=OL)]
    if kind == "sword":
        blade = ctx.glow(name + "_blade", (214, 72, 110), 1.1)
        edge = _mat(ctx, name + "_edge", (120, 20, 50))
        grip = _mat(ctx, name + "_grip", (60, 60, 70))
        parts.append(obox((cx, cy, z0 + 0.42), (0.04, 0.06, 0.14), arm, yaw=yaw))
        parts.append(obox((cx, cy, z0 + 0.8), (0.09, 0.025, 0.6), blade, yaw=yaw, outline=OL))
        parts.append(obox((cx, cy, z0 + 1.18), (0.07, 0.02, 0.16), edge, yaw=yaw, outline=OL))
        parts.append(obox((cx, cy, z0 + 0.5), (0.22, 0.04, 0.03), grip, yaw=yaw, outline=OL))
        parts.append(obox((cx, cy, z0 + 0.42), (0.035, 0.035, 0.14), grip, yaw=yaw))
    else:
        gold = _mat(ctx, name + "_gold", (236, 190, 40))
        goldd = _mat(ctx, name + "_golddark", (190, 140, 30))
        parts.append(obox((cx, cy, z0 + 0.42), (0.04, 0.06, 0.14), arm, yaw=yaw))
        parts.append(obox((cx, cy, z0 + 0.62), (0.32, 0.04, 0.07), gold, yaw=yaw, outline=OL))
        parts.append(obox((cx - 0.08, cy, z0 + 0.52), (0.07, 0.035, 0.16), goldd, yaw=yaw, pitch=15.0, outline=OL))
        parts.append(obox((cx + 0.02, cy, z0 + 0.55), (0.06, 0.012, 0.04), goldd, yaw=yaw))
    return parts


def hatch_platform(ctx, name, x0, y0, x1, y1, z0, z1, rgb=(73, 84, 97), frame=(190, 150, 90), plate=(150, 160, 170)):
    """Plattform mit Luke (Airship Gap Room): Block, Holzrahmen, Riffelplatte mit Diagonalstreifen, Griffmulde."""
    body = _mat(ctx, name + "_body", rgb)
    fr = _mat(ctx, name + "_frame", frame)
    pl = _mat(ctx, name + "_plate", plate)
    st = _mat(ctx, name + "_stripe", _shade(plate, 0.8))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, z0, z1, body, outline=OL),
             box(cx, cy, w - 0.04, d - 0.04, z1, z1 + 0.02, fr, bevel=0.005, outline=OL),
             box(cx, cy, w - 0.24, d - 0.24, z1 + 0.02, z1 + 0.035, pl, outline=OL)]
    n = 6
    for i in range(1, n):
        parts.append(obox((x0 + 0.12 + (w - 0.24) * i / n, cy, z1 + 0.037), (0.012, (d - 0.3) * 1.2, 0.004), st, yaw=45.0))
    parts.append(box(cx, y0 + 0.08, 0.16, 0.03, z1 + 0.035, z1 + 0.045, _mat(ctx, name + "_grip", (60, 64, 70))))
    return parts


# ------------------------------------------------------------------------------------------- Fungle (19.10.)

def lift(parts, dz):
    """Alle Teile um dz in der Hoehe verschieben (Hochebenen): Prismen z0/z1, Drehkoerper-Profile, Rohre, Netze."""
    if not dz:
        return parts
    out = []
    for q in parts:
        q = dict(q)
        t = q.get("type")
        if t == "prism":
            q["z0"], q["z1"] = q["z0"] + dz, q["z1"] + dz
        elif t == "lathe":
            q["prof"] = [[r, z + dz] for r, z in q["prof"]]
            if q.get("tilt"):
                q["tilt"] = [q["tilt"][0], q["tilt"][1], q["tilt"][2] + dz]
        elif t == "tube":
            q["pts"] = [[p[0], p[1], p[2] + dz] for p in q["pts"]]
        elif t == "mesh":
            q["verts"] = [[v[0], v[1], v[2] + dz] for v in q["verts"]]
        out.append(q)
    return out


def campfire(ctx, name, cx, cy, r=0.75, stone_rgb=(222, 170, 110), seed=0):
    """Lagerfeuer (Fungle Strand): Steinring aus Felsbrocken, verkohlte Scheite als Rohre, Flammen als leuchtende
    Drehkoerper, Glutboden."""
    from bm_spec import boulder
    rnd = random.Random(seed)
    stone = (_mat(ctx, name + "_stone", stone_rgb), _mat(ctx, name + "_stone_dark", _shade(stone_rgb, 0.78)), None)
    parts = []
    n = 10
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.15, 0.15)
        sx, sy = cx + r * math.cos(a), cy + r * 0.8 * math.sin(a)
        rr = r * rnd.uniform(0.2, 0.3)
        parts.append(boulder(sx, sy, rr, rr * 0.85, rr * 1.1, stone, seed=seed * 10 + i, seg=10, rings=4, outline=OL))
    ash = _mat(ctx, name + "_ash", (40, 34, 32))
    parts.append(cyl(cx, cy, r * 0.62, 0.0, 0.03, ash, ry=r * 0.5, seg=24))
    log_ = _mat(ctx, name + "_log", (52, 40, 34))
    for i in range(4):
        a = math.pi * i / 4 + 0.3
        parts.append(tube([(cx - r * 0.45 * math.cos(a), cy - r * 0.36 * math.sin(a), 0.05),
                           (cx + r * 0.45 * math.cos(a), cy + r * 0.36 * math.sin(a), 0.09 + i * 0.03)], 0.045, log_, seg=8, outline=OL))
    for i, (fr, fh, col, g) in enumerate(((0.3, 0.55, (250, 170, 40), 2.2), (0.2, 0.75, (255, 220, 90), 2.6), (0.12, 0.9, (255, 245, 180), 2.8))):
        fm = ctx.glow(f"{name}_flame{i}", col, g)
        parts.append(lathe(cx, cy, [(0.0, 0.06), (fr * r, 0.1), (fr * r * 0.8, fh * 0.5), (fr * r * 0.3, fh * 0.85), (0.0, fh)], fm, seg=10))
    return parts


def camp_chair(ctx, name, cx, cy, yaw=0.0, rgb=(70, 110, 160), frame_rgb=(200, 205, 210), w=0.42):
    """Campingstuhl (Fungle): Stoffsitz und Rueckenlehne, gekreuzte Rohrbeine, Lehne auf der +y-Seite (yaw 0)."""
    cloth = _mat(ctx, name + "_cloth", rgb)
    fr = _mat(ctx, name + "_frame", frame_rgb)
    from bm_spec import rot3
    parts = [obox((cx, cy, 0.4), (w, w * 0.9, 0.03), cloth, yaw=yaw, outline=OL)]
    o = rot3((0.0, w * 0.42, 0.0), yaw, 0.0)
    parts.append(obox((cx + o[0], cy + o[1], 0.4 + 0.22), (w, 0.03, 0.44), cloth, yaw=yaw, roll=12.0, outline=OL))
    for sx in (-1, 1):
        a = rot3((sx * w * 0.45, -w * 0.4, 0.0), yaw, 0.0)
        b = rot3((sx * w * 0.45, w * 0.4, 0.0), yaw, 0.0)
        parts.append(tube([(cx + a[0], cy + a[1], 0.0), (cx + b[0], cy + b[1], 0.4)], 0.012, fr, seg=6))
        parts.append(tube([(cx + b[0], cy + b[1], 0.0), (cx + a[0], cy + a[1], 0.4)], 0.012, fr, seg=6))
    return parts


def sand_mound(ctx, name, cx, cy, rx, ry, h, rgb=(222, 170, 110), seed=0):
    """Sandhuegel (Fungle Meeting Room): abgeflachter Ballen in Sandfarbe mit hellerer Kuppe."""
    from bm_spec import blob
    mats = (_mat(ctx, name + "_top", rgb), _mat(ctx, name + "_side", _shade(rgb, 0.85)))
    return [blob(cx, cy, 0.0, rx, ry, h, mats, seed=seed, seg=16, rings=6, outline=(120, 90, 60))]


def lab_pedestal(ctx, name, cx, cy, r=0.42, h=0.75, rgb=(96, 112, 100), glass=(170, 220, 230), glow_rgb=(90, 170, 240)):
    """Laborkonsole (Fungle Laboratory): runder Sockel mit Ring, Deckplatte, Glasglocke mit leuchtender Probe."""
    body = _mat(ctx, name + "_body", rgb)
    ring = _mat(ctx, name + "_ring", _shade(rgb, 0.7))
    top = _mat(ctx, name + "_top", _shade(rgb, 1.2))
    gl = ctx.glow(name + "_glass", glass, 0.7)
    pr = ctx.glow(name + "_probe", glow_rgb, 2.2)
    parts = [cyl(cx, cy, r, 0.0, h * 0.85, body, seg=28, outline=OL),
             cyl(cx, cy, r + 0.02, h * 0.3, h * 0.36, ring, seg=28),
             cyl(cx, cy, r, h * 0.85, h, top, seg=28, bevel=0.015, outline=OL),
             lathe(cx, cy, [(0.0, h), (r * 0.45, h), (r * 0.45, h + 0.25), (r * 0.3, h + 0.36), (0.0, h + 0.4)], gl, seg=20, outline=OL),
             lathe(cx, cy, [(0.0, h + 0.02), (r * 0.18, h + 0.02), (r * 0.22, h + 0.14), (r * 0.1, h + 0.24), (0.0, h + 0.26)], pr, seg=12)]
    return parts



# ----------------------------------------------------------------------------------------- Fehlerrunde 19.10. (Polus)
# User-Meldungen #247..#284: glatte Quader, flache Kreise und Platten durch gegliederte Koerper ersetzen.

def bookcase(ctx, name, x0, y0, x1, y1, h, facing="S", rgb=(70, 50, 40), shelves=4, seed=0,
             book_colors=((180, 60, 60), (60, 90, 170), (210, 190, 120), (90, 140, 90), (230, 230, 225), (120, 70, 140))):
    """Buecherregal: Korpus mit Seitenwangen, Deckel, Sockel und Rueckwand, Boeden, darauf viele schmale Buecher
    (Breite 0,025..0,06, Hoehe 62..90 % des Fachs), dazwischen Luecken und liegende Stapel."""
    body = _mat(ctx, name + "_body", rgb)
    back = _mat(ctx, name + "_back", _shade(rgb, 0.7))
    along_x = facing in ("S", "N")
    a0, a1, b0, b1 = (x0, x1, y0, y1) if along_x else (y0, y1, x0, x1)
    L, D = a1 - a0, b1 - b0
    front_lo = facing in ("S", "W")                       # Front liegt auf der kleinen Koordinate der Tiefe
    bf = b0 if front_lo else b1
    sgn = 1.0 if front_lo else -1.0                       # von der Front nach hinten

    def B(a, b, sa, sb, z0, z1, m, **kw):
        return box(a, b, sa, sb, z0, z1, m, **kw) if along_x else box(b, a, sb, sa, z0, z1, m, **kw)
    ca, cb = (a0 + a1) / 2, (b0 + b1) / 2
    t = 0.035
    parts = [B(a0 + t / 2, cb, t, D, 0.0, h, body, outline=OL), B(a1 - t / 2, cb, t, D, 0.0, h, body, outline=OL),
             B(ca, cb, L, D, h - t, h, body, outline=OL), B(ca, cb, L - 2 * t, D, 0.0, 0.07, body),
             B(ca, bf + sgn * (D - 0.012), L - 2 * t, 0.02, 0.0, h, back)]
    rnd = random.Random(seed)
    gap = (h - 0.07 - t) / shelves
    for i in range(shelves):
        zb = 0.07 + gap * i
        if i > 0:
            parts.append(B(ca, cb, L - 2 * t, D - 0.02, zb - 0.02, zb, body))
        a = a0 + t + 0.01
        while a < a1 - t - 0.03:
            r = rnd.random()
            if r < 0.08:                                    # Luecke
                a += rnd.uniform(0.05, 0.12)
                continue
            col = rnd.choice(book_colors)
            m = _mat(ctx, f"{name}_book{col[0]}_{col[1]}_{col[2]}", col)
            if r < 0.16 and a < a1 - t - 0.2:              # liegender Stapel
                n = rnd.randint(2, 4)
                bw = rnd.uniform(0.14, 0.2)
                for k in range(n):
                    c2 = rnd.choice(book_colors)
                    m2 = _mat(ctx, f"{name}_book{c2[0]}_{c2[1]}_{c2[2]}", c2)
                    parts.append(B(a + bw / 2, bf + sgn * (D * 0.45), bw, D * 0.7, zb + k * 0.035, zb + (k + 1) * 0.035 - 0.003, m2))
                a += bw + 0.01
                continue
            bw = rnd.uniform(0.025, 0.06)
            bh = gap * rnd.uniform(0.62, 0.9)
            bd = D * rnd.uniform(0.6, 0.8)
            parts.append(B(a + bw / 2, bf + sgn * (0.02 + bd / 2), bw, bd, zb, zb + bh, m))
            a += bw + rnd.uniform(0.0, 0.006)
    return parts


def au_crate(ctx, name, cx, cy, s, rot, h, z0=0.0, rgb=(63, 97, 90), top_rgb=(90, 130, 112), line=(24, 36, 33)):
    """Among-Us-Kiste als Koerper: Kasten, ueberstehender Deckel, dunkle Kantenleisten an den senkrechten Kanten, je
    Seite eine eingelassene U-foermige Griffmulde (wie in der Zeichnung)."""
    body = _mat(ctx, name + "_body", rgb)
    top = _mat(ctx, name + "_lid", top_rgb)
    dark = _mat(ctx, name + "_edge", _shade(rgb, 0.62))
    hole = _mat(ctx, name + "_grip", line)
    from bm_spec import rot3
    parts = [obox((cx, cy, z0 + (h - 0.05) / 2), (s, s, h - 0.05), body, yaw=rot, outline=line)]
    parts.append(obox((cx, cy, z0 + h - 0.025), (s + 0.03, s + 0.03, 0.05), top, yaw=rot, outline=line))
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        o = rot3((sx * (s / 2 - 0.02), sy * (s / 2 - 0.02), 0.0), rot, 0.0)
        parts.append(obox((cx + o[0], cy + o[1], z0 + (h - 0.05) / 2), (0.06, 0.06, h - 0.06), dark, yaw=rot))
    gz = z0 + h * 0.66
    for k in range(4):
        yaw = rot + 90 * k
        o = rot3((0.0, -(s / 2 + 0.004), 0.0), yaw, 0.0)
        parts.append(obox((cx + o[0], cy + o[1], gz), (s * 0.34, 0.01, 0.07), hole, yaw=yaw))
        for dxs in (-1, 1):
            o2 = rot3((dxs * s * 0.17, -(s / 2 + 0.004), 0.0), yaw, 0.0)
            parts.append(obox((cx + o2[0], cy + o2[1], gz + 0.06), (0.03, 0.01, 0.12), hole, yaw=yaw))
    return parts


def transformer(ctx, name, x0, y0, x1, y1, rgb=(120, 140, 152)):
    """Transformator (Polus-Generatorhof), Front nach Sueden: Hauptkessel mit Kuehlrippen an beiden Seiten,
    Schaltschrank vorn mit Tuer und Blitzschild, Gitterkaefig (X-Streben), Manometer, zwei gespreizte
    Isolatorstapel (rote Scheiben, weisse Kappen)."""
    light = _mat(ctx, name + "_body", rgb)
    mid = _mat(ctx, name + "_mid", _shade(rgb, 0.72))
    dark = _mat(ctx, name + "_dark", _shade(rgb, 0.45))
    disc = _mat(ctx, name + "_disc", (150, 80, 68))
    capm = _mat(ctx, name + "_cap", (206, 227, 239))
    sign = ctx.glow(name + "_sign", (240, 160, 50), 1.4)
    w, d = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    yf = y0
    parts = []
    kd = d * 0.55
    ky = y1 - kd / 2
    parts.append(box(cx, ky, w * 0.62, kd, 0.0, 1.0, light, bevel=0.02, outline=OL))
    parts.append(box(cx, ky, w * 0.66, kd + 0.04, 1.0, 1.06, mid, outline=OL))
    for side in (-1, 1):
        rx = cx + side * (w * 0.31 + 0.09)
        parts.append(box(rx, ky, 0.18, kd * 0.9, 0.08, 0.86, mid, outline=OL))
        for k in range(6):
            yy = ky - kd * 0.4 + kd * 0.8 * k / 5
            parts.append(box(rx + side * 0.1, yy, 0.03, 0.025, 0.12, 0.82, dark))
    sd = d - kd
    sy = yf + sd / 2
    parts.append(box(cx - w * 0.18, sy, w * 0.36, sd - 0.02, 0.0, 0.62, light, bevel=0.015, outline=OL))
    parts.append(box(cx - w * 0.18, yf - 0.006, w * 0.3, 0.012, 0.08, 0.56, mid))
    parts.append(box(cx - w * 0.18 + w * 0.11, yf - 0.014, 0.025, 0.012, 0.28, 0.38, dark))
    parts.append(box(cx - w * 0.18, yf - 0.014, 0.12, 0.008, 0.42, 0.52, sign))
    parts.append(cyl(cx - w * 0.3, sy, 0.05, 0.62, 0.78, _mat(ctx, name + "_gauge", (120, 84, 60)), seg=12, outline=OL))
    gx0, gx1 = cx + 0.02, cx + w * 0.42
    gm = (gx0 + gx1) / 2
    for gx in (gx0, gx1):
        parts.append(box(gx, sy, 0.03, sd - 0.04, 0.0, 0.62, dark))
    parts.append(box(gm, yf + 0.01, gx1 - gx0, 0.025, 0.59, 0.62, dark))
    parts.append(box(gm, yf + 0.01, gx1 - gx0, 0.025, 0.0, 0.04, dark))
    for za, zb in ((0.04, 0.59), (0.59, 0.04)):
        parts.append(tube([(gx0, yf + 0.01, za), (gx1, yf + 0.01, zb)], 0.012, dark, seg=6))
    parts.append(box(gm, sy + 0.02, gx1 - gx0 - 0.06, sd - 0.12, 0.0, 0.5, mid))
    for side in (-1, 1):
        a = (cx + side * w * 0.18, ky, 1.06)
        b = (cx + side * w * 0.42, ky, 1.85)
        parts.append(tube([a, b], 0.03, dark, seg=8))
        ang = math.degrees(math.atan2(b[0] - a[0], b[2] - a[2]))
        for i in range(7):
            t = (i + 0.5) / 7
            c = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
            r = 0.085 if i % 2 == 0 else 0.07
            parts.append(lathe(c[0], c[1], [(0.0, c[2] - 0.028), (r, c[2] - 0.02), (r, c[2] + 0.02), (0.0, c[2] + 0.028)],
                               capm if i == 6 else disc, seg=14, tilt=(abs(ang), 0.0 if side > 0 else 180.0, c[2])))
    return parts


def fan_housing(ctx, name, cx, cy, zc, r, rgb=(60, 90, 100), blade_rgb=(24, 50, 60), depth=0.22, facing="S"):
    """Luefter mit Gehaeuse (Triebwerksblock): Rahmenplatte, Mantelring nach vorn, sechs angestellte Fluegel, Nabe
    mit Kegel, Schutzgitter aus drei Streben. Achse senkrecht zur Front facing (S/N)."""
    frame = _mat(ctx, name + "_frame", rgb)
    shroud = _mat(ctx, name + "_shroud", _shade(rgb, 0.75))
    blade = _mat(ctx, name + "_blade", blade_rgb)
    hub = _mat(ctx, name + "_hub", _shade(rgb, 1.3))
    sgn = -1.0 if facing == "S" else 1.0
    parts = [box(cx, cy, 2.2 * r, 0.06, zc - 1.1 * r, zc + 1.1 * r, frame, bevel=0.02, outline=OL)]
    n = 20
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        x, z = cx + r * math.cos(a), zc + r * math.sin(a)
        parts.append(obox((x, cy + sgn * depth / 2, z), (2 * math.pi * r / n + 0.01, depth, 0.05), shroud,
                          pitch=math.degrees(a) + 90.0))
    yb = cy + sgn * depth * 0.55
    for i in range(6):
        a = 60 * i + 15
        o = (0.55 * r * math.cos(math.radians(a)), 0.55 * r * math.sin(math.radians(a)))
        parts.append(obox((cx + o[0], yb, zc + o[1]), (0.8 * r, 0.02, 0.26 * r), blade, pitch=a, roll=25.0))
    parts.append(lathe(cx, yb, [(0.0, zc), (0.18 * r, zc), (0.12 * r, zc + 0.12), (0.0, zc + 0.16)], hub, seg=16,
                       tilt=(90.0, 270.0 if facing == "S" else 90.0, zc)))
    yg = cy + sgn * (depth + 0.01)
    for a in (0, 60, 120):
        parts.append(obox((cx, yg, zc), (2 * r, 0.02, 0.03), frame, pitch=a))
    return parts


def sawhorse(ctx, name, cx, cy, L=0.7, yaw=0.0, h=0.55):
    """Absperrbock: Balken mit rot-weissen Streifen auf zwei A-Boecken."""
    red = _mat(ctx, name + "_red", (190, 50, 60))
    white = _mat(ctx, name + "_white", (235, 235, 230))
    leg = _mat(ctx, name + "_leg", (40, 44, 50))
    from bm_spec import rot3
    n = 6
    parts = []
    for i in range(n):
        o = rot3((-L / 2 + L * (i + 0.5) / n, 0.0, 0.0), yaw, 0.0)
        parts.append(obox((cx + o[0], cy + o[1], h - 0.06), (L / n, 0.04, 0.12), red if i % 2 == 0 else white, yaw=yaw, outline=OL))
    for s in (-1, 1):
        top = rot3((s * L * 0.4, 0.0, 0.0), yaw, 0.0)
        for f in (-1, 1):
            foot = rot3((s * L * 0.44, f * 0.16, 0.0), yaw, 0.0)
            parts.append(tube([(cx + top[0], cy + top[1], h - 0.12), (cx + foot[0], cy + foot[1], 0.0)], 0.018, leg, seg=6))
    return parts


def workbench(ctx, name, x0, y0, x1, y1, h=0.62, rgb=(175, 90, 72), top_rgb=(120, 70, 56), seed=0):
    """Werkbank: Platte, vier Beine, Ablage unten, Schubladenblock vorn rechts, darauf Werkzeug (Schluessel, Hammer,
    kleine Kiste)."""
    body = _mat(ctx, name + "_body", rgb)
    top = _mat(ctx, name + "_top", top_rgb)
    dark = _mat(ctx, name + "_dark", _shade(rgb, 0.55))
    steel = _mat(ctx, name + "_steel", (150, 156, 162))
    wood = _mat(ctx, name + "_wood", (150, 110, 70))
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    parts = [box(cx, cy, w, d, h - 0.05, h, top, bevel=0.01, outline=OL)]
    for fx in (x0 + 0.05, x1 - 0.05):
        for fy in (y0 + 0.05, y1 - 0.05):
            parts.append(box(fx, fy, 0.05, 0.05, 0.0, h - 0.05, body))
    parts.append(box(cx, cy, w - 0.06, d - 0.06, 0.12, 0.15, body))
    dx0 = x1 - w * 0.35
    parts.append(box((dx0 + x1 - 0.03) / 2, cy, x1 - 0.03 - dx0, d - 0.06, 0.2, h - 0.05, body, outline=OL))
    for k in range(3):
        z = 0.24 + (h - 0.32) * (k + 0.5) / 3
        parts.append(box((dx0 + x1 - 0.03) / 2, y0 + 0.024, x1 - 0.06 - dx0, 0.01, z - 0.06, z + 0.06, dark))
        parts.append(box((dx0 + x1 - 0.03) / 2, y0 + 0.016, 0.08, 0.012, z - 0.01, z + 0.01, steel))
    rnd = random.Random(seed)
    parts.append(obox((x0 + w * 0.25, cy, h + 0.01), (0.25, 0.04, 0.015), steel, yaw=rnd.uniform(-30, 30)))
    hx = x0 + w * 0.5
    parts.append(obox((hx, cy - 0.03, h + 0.015), (0.03, 0.26, 0.03), wood, yaw=20.0))
    parts.append(obox((hx + 0.04, cy + 0.1, h + 0.025), (0.12, 0.04, 0.05), steel, yaw=20.0))
    parts.append(box(x1 - w * 0.2, cy + 0.02, 0.22, 0.14, h, h + 0.1, _mat(ctx, name + "_box", (200, 60, 50)), bevel=0.01, outline=OL))
    return parts


def ground_hole(ctx, name, poly, seed=0):
    """Bohrloch im Gelaende (Polus Science/Hole): dunkle Grubenflaeche knapp ueber dem Boden, schwarzer Kern, Ring
    aus Geroellbrocken am Rand."""
    from bm_spec import boulder
    pit = _mat(ctx, name + "_pit", (34, 28, 40))
    core = _mat(ctx, name + "_core", (12, 10, 16))
    rl, rs = _mat(ctx, name + "_rock", (98, 82, 110)), _mat(ctx, name + "_rock_dark", (70, 58, 82))
    parts = [prism(poly.buffer(-0.02), 0.0, 0.012, pit), prism(poly.buffer(-0.18), 0.0, 0.016, core)]
    rnd = random.Random(seed)
    ring = poly.exterior
    n = max(6, int(ring.length / 0.28))
    for i in range(n):
        p = ring.interpolate(i / n, normalized=True)
        r = rnd.uniform(0.07, 0.14)
        parts.append(boulder(p.x, p.y, r, r * 0.8, r * 0.9, (rl, rs, rl), seed=seed * 50 + i, seg=8, rings=4))
    return parts


def stalls(ctx, name, x0, y0, x1, n=3, depth=0.6, h=1.15, rgb=(40, 120, 80), wall_rgb=(60, 80, 160)):
    """Toilettenkabinen an einer Nordwand (Front Sueden, y0 = Tuerlinie): Trennwaende, geschlossene Tueren mit Spalt
    unten, Griff, je ein WC (Becken, Spuelkasten) dahinter."""
    door = _mat(ctx, name + "_door", rgb)
    part = _mat(ctx, name + "_wall", _shade(rgb, 0.8))
    steel = _mat(ctx, name + "_steel", (190, 195, 200))
    porc = _mat(ctx, name + "_wc", (232, 236, 240))
    w = (x1 - x0) / n
    parts = []
    for i in range(n + 1):
        x = x0 + w * i
        parts.append(box(x, y0 + depth / 2, 0.04, depth, 0.1, h, part, outline=OL))
    for i in range(n):
        cx = x0 + w * (i + 0.5)
        parts.append(box(cx, y0, w - 0.06, 0.035, 0.12, h - 0.04, door, outline=OL))
        parts.append(box(cx + w * 0.3, y0 - 0.025, 0.02, 0.02, 0.5, 0.6, steel))
        parts.append(lathe(cx, y0 + depth - 0.22, [(0.0, 0.0), (0.12, 0.0), (0.14, 0.32), (0.16, 0.38), (0.0, 0.38)], porc, seg=16, outline=OL))
        parts.append(box(cx, y0 + depth - 0.07, 0.3, 0.12, 0.38, 0.7, porc, bevel=0.02, outline=OL))
    parts.append(box((x0 + x1) / 2, y0 + depth / 2, x1 - x0, depth, h, h + 0.03, part))
    return parts
