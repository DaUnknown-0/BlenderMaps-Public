# Skeld / Storage - am Kartenfoto gemessen (zoomgrid.py, bm_analyze.py).
#
# Boden: Zeichnung (graue Platten, senkrechte Fugen exakt alle 1,52 bei -3,66/-2,14/-0,60, waagrechte 0,85-0,90);
#   unter Containern und Faessern periodisch in derselben Reihe fortgesetzt.
# Mitte (Hinweis User 17.10.: "Groesse der mittleren Container"): drei hohe Container. Among Us zeichnet Front (mit
#   Griffmulden) und Oberseite; Hoehe = Fronthoehe / k:
#   gruen  Front Bild -14,12..-12,70 -> 2,40, Oberseite bis hinter die grosse Kiste, die obendrauf steht;
#   blau   Front -13,52..-12,55 (Laengsstreifen) -> 1,64, Oberseite quer gestreift, Kiste obendrauf;
#   rot    Front -12,90..-11,82 -> 1,83, Kiste obendrauf.   Halle 3,6 hoch.
# Kisten (Rueckfrage User "blaue Flaschen und Boxen"): prozedural in exakten Farben statt Bildausschnitten:
#   Deckel (90,130,112), Seiten (63,97,90) mit Griffmulde (24,36,33), Kontur (24,36,33). Masse neu abgelesen
#   (Mitte der Oberseite im Bild, Kante, Drehung, Hoehe aus der senkrechten Frontkante / k).
# Faesser: drei hohe Faesser oben links (r 0,30, Hoehe 1,02-1,05, Fusspunkte gemessen) und eins rechts am
#   Container; Koerper (71,108,126), Deckel (66,78,87), heller Ring (107,158,173), Etikett (115,28,49), Kontur (8,12,16).

import numpy as np
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import box as sbox

import bm_tex as T
from bm_spec import art_container, art_floor, box, cyl, prism

H = 3.6
LINE = (24, 36, 33)
# Faesser: (Fuss x, Fuss y Welt, Radius, Hoehe)
BARRELS = [(-4.78, -10.72, 0.30, 1.03), (-4.31, -10.12, 0.30, 1.05), (-3.92, -9.77, 0.30, 1.02), (-0.58, -13.50, 0.27, 0.80)]


def floor(ctx):
    holes = [sbox(-4.4, -15.2, -0.35, -10.4), sbox(-5.2, -11.0, -2.9, -8.9), sbox(-0.95, -13.75, -0.3, -12.9)]
    return art_floor(ctx, "floor_Storage", holes, period_x=1.52)


def crate_tex(ctx):
    n = 128
    im = Image.new("RGB", (n, n), (63, 97, 90))
    d = ImageDraw.Draw(im)
    pts = [(0.08, 0.34), (0.36, 0.34), (0.40, 0.54), (0.60, 0.54), (0.64, 0.34), (0.92, 0.34)]      # Griffmulde
    d.line([(x * n, y * n) for x, y in pts], fill=LINE, width=5, joint="curve")
    return ctx.tex("sto_crate_side", im, uv="face")


def crate(ctx, cx, cy, s, rot, h, z0, side, top):
    sq = affinity.rotate(sbox(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), rot, origin=(cx, cy))
    d = prism(sq, z0, z0 + h, side, top=top, bevel=0.02, outline=LINE)
    d["side_uv"] = "face"
    return d


def props(ctx):
    k = ctx.k
    parts = []
    # Frachtcontainer als Koerper (Sicken, Eckbeschlaege, Tueren)
    from bm_models import container
    zg, zb, zr = (-12.70 + 14.12) / k, (-12.55 + 13.52) / k, (-11.82 + 12.90) / k
    parts += container(ctx, "sto_green", -2.48, -14.12, -0.72, -14.12 + (-11.33 + 12.70), zg, rgb=(52, 84, 74))
    parts += container(ctx, "sto_blue", -3.36, -13.52, -2.45, -13.52 + (-11.25 + 12.55), zb, rgb=(44, 64, 92))
    parts += container(ctx, "sto_red", -1.45, -12.90, -0.38, -12.90 + (-10.98 + 11.82), zr, rgb=(96, 60, 70))
    side = crate_tex(ctx)
    top = ctx.color("sto_crate_top", (90, 130, 112))
    # (Bildmitte Oberseite x, y, Kante, Drehung, Hoehe, Sockel) -> Welt: y - k * (Sockel + Hoehe)
    crates = [(-3.95, -12.40, 0.62, 25, 0.71, 0.0), (-2.85, -11.50, 0.55, 15, 0.68, zb), (-1.95, -11.15, 0.95, 15, 1.02, zg),
              (-1.08, -10.72, 0.50, -25, 0.61, zr), (-3.30, -9.00, 0.65, 0, 0.76, 0.0)]
    for x, y, s, rot, h, z0 in crates:
        parts.append(crate(ctx, x, y - k * (z0 + h), s, rot, h, z0, side, top))
    # vorn, direkt vor dem gruenen Container; auf den Collider gerueckt (Suedecke -14,84), vorher 0,2 im Laufbereich
    parts.append(crate(ctx, -1.68, -14.40, 0.78, 10, 0.88, 0.0, side, top))
    body = ctx.color("sto_barrel", (71, 108, 126))
    lid = ctx.color("sto_barrel_lid", (66, 78, 87))
    ring = ctx.color("sto_barrel_ring", (107, 158, 173))
    label = ctx.color("sto_barrel_label", (115, 28, 49))
    for bx, by, r, h in BARRELS:
        parts.append(cyl(bx, by, r, 0.0, h - 0.06, body, seg=40, outline=(8, 12, 16)))
        parts.append(cyl(bx, by, r * 0.97, h - 0.06, h - 0.02, ring, seg=40))
        parts.append(cyl(bx, by, r * 0.93, h - 0.02, h, lid, seg=40))
        parts.append(cyl(bx, by, r * 1.01, h * 0.45, h * 0.58, label, seg=40))
    can = ctx.color("sto_gascan", (198, 44, 78))
    parts.append(box(-2.85, -13.92 - k * 0.38, 0.30, 0.18, 0.0, 0.38, can, bevel=0.03, outline=(40, 12, 20)))
    return parts
