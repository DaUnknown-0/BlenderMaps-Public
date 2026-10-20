# bm_tex.py - Texturen fuer den Nachbau (laeuft ausserhalb von Blender, PIL/numpy/cv2).
#
# Aufloesung TPPU Pixel pro AU-Einheit. Alle Farben werden am Kartenfoto gemessen (bm_analyze.py) und exakt
# uebernommen; Kantenglaettung entsteht nur durch Supersampling an Farbgrenzen.

import cv2
import numpy as np
from PIL import Image

TPPU = 128
SS = 4                      # Supersampling fuer prozedurale Muster


def diamond_tile(S, half, bg, light, sites, n=6, ppu=TPPU):
    """Rautenkachel n x n Gitterplaetze (Abstand S): Plaetze (i, j) mit (i+j) ungerade tragen eine Raute, hell wenn
    sites[(i%n, j%n)]. Rueckgabe (Bild, Kachelgroesse in Einheiten). Kachelursprung = Platz (0,0) - (S/2, S/2)."""
    T = n * S
    px = int(round(T * ppu))
    N = px * SS
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    lx = (xx + 0.5) / N * T                       # lokale Weltkoordinate in der Kachel
    ly = T - (yy + 0.5) / N * T                   # Zeile 0 = oben
    out = np.zeros((N, N, 3), np.float64) + np.array(bg, np.float64)
    for (i, j), on in sites.items():
        if not on:
            continue
        cx, cy = (i + 0.5) * S, (j + 0.5) * S
        for ox in (-T, 0, T):
            for oy in (-T, 0, T):
                m = (np.abs(lx - cx - ox) + np.abs(ly - cy - oy)) <= half
                out[m] = light
    img = cv2.resize(out.astype(np.float32), (px, px), interpolation=cv2.INTER_AREA)
    return Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8)), T


def palette_of(img, tol=10, min_frac=0.0015, min_px=6, max_cols=64):
    """Farben einer Zeichnung: haeufige exakte Farben (ab max(min_px, min_frac * Flaeche) Pixeln), Mischpixel der
    Kantenglaettung werden so nicht zu eigenen Farben, seltene echte Farben (kleines Pizzastueck) bleiben."""
    a = np.asarray(img).reshape(-1, 3)
    cols, cnt = np.unique(a, axis=0, return_counts=True)
    order = np.argsort(-cnt)
    thr = max(min_px, min(min_frac * len(a), 60))            # duenne Linien (Kabel) behalten ihre Farbe
    pal = []
    for i in order:
        if (cnt[i] < thr and pal) or len(pal) >= max_cols:
            break
        c = cols[i].astype(int)
        if all(np.abs(c - p).sum() > tol for p in pal):
            pal.append(c)
    return np.array(pal).reshape(-1, 3)


SMOOTH = False      # zusammengesetzte Vorlagen (Fungle): Farben sind schon gemischt, Palette wuerde Details schlucken


def label_upscale(img, scale, pal=None, blur=0.6):
    """Zeichnung hochskalieren, ohne neue Farben zu erfinden: jedes Pixel bekommt die naechste Palettenfarbe,
    jede Farbmaske wird weich hochskaliert (nur in ihrem eigenen Rechteck), dann gewinnt die staerkste Maske."""
    if SMOOTH:
        sx, sy = scale if isinstance(scale, (tuple, list)) else (scale, scale)
        w, h = img.size
        from PIL import ImageFilter
        up = img.convert("RGB").resize((max(2, int(round(w * sx))), max(2, int(round(h * sy)))), Image.LANCZOS)
        if max(sx, sy) > 1.3:                                  # Hochskaliertes nachschaerfen (Konturen der Zeichnung)
            up = up.filter(ImageFilter.UnsharpMask(radius=max(1.0, 0.6 * max(sx, sy)), percent=90, threshold=2))
        return up
    a = np.asarray(img).astype(np.int16)
    if pal is None:
        pal = palette_of(img)
    lab = np.empty(a.shape[:2], np.int32)
    step = max(1, 4_000_000 // max(1, a.shape[1] * len(pal) * 3))     # Zeilenbloecke: Speicher begrenzt
    for r0 in range(0, a.shape[0], step):
        d = np.abs(a[r0:r0 + step, :, None, :] - pal[None, None, :, :]).sum(-1)
        lab[r0:r0 + step] = d.argmin(-1)
    h, w = lab.shape
    sx, sy = scale if isinstance(scale, (tuple, list)) else (scale, scale)
    W, H = max(2, int(round(w * sx))), max(2, int(round(h * sy)))
    W2, H2 = W * 2, H * 2                                  # doppelt rechnen, dann flaechig verkleinern = Kantenglaettung
    fx, fy = W2 / w, H2 / h
    best = np.full((H2, W2), -1.0, np.float32)
    idx = np.zeros((H2, W2), np.int32)
    for k in range(len(pal)):
        m = (lab == k)
        if not m.any():
            continue
        ys, xs = np.nonzero(m)
        y0, y1 = max(0, ys.min() - 3), min(h, ys.max() + 4)
        x0, x1 = max(0, xs.min() - 3), min(w, xs.max() + 4)
        sub = m[y0:y1, x0:x1].astype(np.float32)
        ty0, ty1 = int(round(y0 * fy)), int(round(y1 * fy))
        tx0, tx1 = int(round(x0 * fx)), int(round(x1 * fx))
        up = cv2.resize(sub, (tx1 - tx0, ty1 - ty0), interpolation=cv2.INTER_CUBIC)
        if blur:
            up = cv2.GaussianBlur(up, (0, 0), sigmaX=blur * sx, sigmaY=blur * sy)
        bv = best[ty0:ty1, tx0:tx1]
        sel = up > bv
        bv[sel] = up[sel]
        idx[ty0:ty1, tx0:tx1][sel] = k
    out = pal[idx].astype(np.float32)
    return Image.fromarray(np.round(cv2.resize(out, (W, H), interpolation=cv2.INTER_AREA)).astype(np.uint8))


def solid(rgb, size=4):
    return Image.new("RGB", (size, size), tuple(int(v) for v in rgb))
