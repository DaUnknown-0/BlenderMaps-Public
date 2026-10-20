# bm_compare.py <karte> [raum ...] [--sheet datei]: Original | Blender | Abweichung je Raum.
#
# Liest out/<karte>/cmp/<raum>_bl.png (+ _bl.json mit dem Weltausschnitt), schneidet dasselbe Stueck aus dem
# Kartenfoto und schreibt out/<karte>/cmp/<raum>.png. Kennzahl: mittlere absolute RGB-Abweichung (0..255)
# und Anteil der Pixel mit Abweichung > 24 (deutlich sichtbar).

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from bm_ref import Ref, ROOT


def compare(ref, key, name):
    d = ROOT / "out" / key / "cmp"
    bl = Image.open(d / f"{name}_bl.png").convert("RGB")
    x0, y0, x1, y1 = json.load(open(d / f"{name}_bl.json"))["bbox"]
    orig = ref.crop(x0, y0, x1, y1).resize(bl.size, Image.LANCZOS)
    a, b = np.asarray(orig).astype(np.int16), np.asarray(bl).astype(np.int16)
    diff = np.abs(a - b).max(-1)
    # nur gebaute Flaeche bewerten: Hintergrund (Weltraum/Himmel) zaehlt nicht
    sel = np.abs(b - np.array([41, 23, 56])).sum(-1) > 6
    if not sel.any():
        sel = np.ones(diff.shape, bool)
    mean = float(np.abs(a - b)[sel].mean())
    import cv2
    ab, bb = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 2.0), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 2.0)
    soft = float(np.abs(ab - bb)[sel].mean())
    big = float((diff > 24)[sel].mean())
    heat = np.zeros_like(a, dtype=np.uint8)
    heat[..., 0] = np.clip(diff * 3, 0, 255)
    heat[..., 1] = np.clip(diff * 3 - 255, 0, 255)
    out = Image.new("RGB", (bl.width * 3 + 8, bl.height + 18), (20, 20, 20))
    out.paste(orig, (0, 18))
    out.paste(bl, (bl.width + 4, 18))
    out.paste(Image.fromarray(heat), (bl.width * 2 + 8, 18))
    ImageDraw.Draw(out).text((4, 3), f"{name}  Original | Blender | Abweichung   mittel {mean:.1f}  weich {soft:.1f}  >24: {big * 100:.1f} %",
                             fill=(255, 255, 0))
    out.save(d / f"{name}.png")
    return name, mean, big, out, soft


def sheet(images, path, width=1800):
    rows, cur, curw = [], [], 0
    for im in images:
        s = min(1.0, width / im.width)
        im = im.resize((int(im.width * s), int(im.height * s)))
        if curw + im.width > width and cur:
            rows.append(cur)
            cur, curw = [], 0
        cur.append(im)
        curw += im.width
    if cur:
        rows.append(cur)
    H = sum(max(i.height for i in r) for r in rows)
    out = Image.new("RGB", (width, H), (10, 10, 10))
    y = 0
    for r in rows:
        x = 0
        for im in r:
            out.paste(im, (x, y))
            x += im.width
        y += max(i.height for i in r)
    out.save(path, quality=88)


if __name__ == "__main__":
    argv = sys.argv[1:]
    sheet_path = None
    if "--sheet" in argv:
        i = argv.index("--sheet")
        sheet_path = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")]
    key = args[0]
    ref = Ref(key, full=True)
    d = ROOT / "out" / key / "cmp"
    names = args[1:] or sorted(p.stem[:-3] for p in d.glob("*_bl.png"))
    res = [compare(ref, key, n) for n in names]
    for n, m, b, _, so in res:
        print(f"  {n:14s} mittel {m:5.1f}   weich {so:5.1f}   >24: {b * 100:5.1f} %")
    print(f"  Summe weich {sum(r[4] for r in res):.1f}")
    if sheet_path:
        sheet([r[3] for r in res], sheet_path)
