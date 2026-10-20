# report_review.py <reports-ordner> <karte> <ausgabeordner> [nummern]: Nightfall-Meldungen (F6, lokaler Melde-Knopf)
# gegen das Original. Je Meldung: Spiel-Screenshot | Kartenfoto um den Standpunkt (8 x 8 Einheiten) mit Standpunkt,
# Blickkegel (horizontales Sichtfeld) und den Ship-Collidern (Laufgrenzen). Blaetter mit je 6 Meldungen,
# Beschriftung = Nummer, Raum, Blick, Neigung, Augenhoehe.
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bm_ref import Ref

src, key, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
per = 6


def numbers(spec):
    """'52-69' oder '3,5,8' -> Menge der Meldungsnummern (Index in der sortierten Liste aller Meldungen)."""
    out_ = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out_ |= set(range(int(a), int(b) + 1)) if b else {int(a)}
    return out_


only = numbers(sys.argv[4]) if len(sys.argv) > 4 else None
out.mkdir(parents=True, exist_ok=True)
ref = Ref(key, full=True)
cols = ref.colliders()
font = ImageFont.truetype("arial.ttf", 20)
GW, GH, CS, R = 640, 360, 360, 4.0

reps = []
for n, f in enumerate(sorted(src.glob("*.json"))):
    d = json.loads(f.read_text(encoding="utf-8"))
    if d.get("map") == key and (only is None or n in only):
        reps.append((n, f, d))


def cell(i, f, d):
    im = Image.new("RGB", (GW + CS, GH), (20, 20, 20))
    g = Image.open(f.with_suffix(".png")).convert("RGB").resize((GW, GH), Image.LANCZOS)
    im.paste(g, (0, 0))
    x, y = d["position"]["x"], d["position"]["y"]
    c = ref.crop(x - R, y - R, x + R, y + R).resize((CS, CS), Image.LANCZOS)
    dr = ImageDraw.Draw(c)
    s = CS / (2 * R)
    w2c = lambda wx, wy: ((wx - x + R) * s, (y + R - wy) * s)
    for _, path in cols:
        pts = [w2c(*p) for p in path]
        if len(pts) > 1:
            dr.line(pts, fill=(0, 255, 255), width=1)
    h = math.radians(d["headingDeg"])
    half = math.radians(d.get("fovHorizontalDeg") or 105) / 2
    L = 3.0
    p0 = w2c(x, y)
    for a in (h - half, h + half):
        dr.line([p0, w2c(x + L * math.cos(a), y + L * math.sin(a))], fill=(255, 255, 0), width=2)
    dr.line([p0, w2c(x + L * math.cos(h), y + L * math.sin(h))], fill=(255, 80, 80), width=2)
    dr.ellipse((p0[0] - 5, p0[1] - 5, p0[0] + 5, p0[1] + 5), fill=(255, 0, 0), outline=(0, 0, 0))
    im.paste(c, (GW, 0))
    t = f"#{i} {d['room'] or '-'} h{d['headingDeg']:.0f} p{d['pitchDeg']:.0f} z{d['eyeZ']} ({x:.2f}|{y:.2f})"
    ImageDraw.Draw(im).rectangle((0, GH - 26, 560, GH), fill=(0, 0, 0))
    ImageDraw.Draw(im).text((4, GH - 24), t, fill=(255, 255, 0), font=font)
    return im


for s in range(0, len(reps), per):
    chunk = reps[s:s + per]
    sheet = Image.new("RGB", (2 * (GW + CS), GH * ((len(chunk) + 1) // 2)), (255, 0, 255))
    for k, (n, f, d) in enumerate(chunk):
        sheet.paste(cell(n, f, d), ((k % 2) * (GW + CS), (k // 2) * GH))
    sheet.save(out / f"review_{s // per:02d}.jpg", quality=82)
print("report_review", key, len(reps), "Meldungen")
