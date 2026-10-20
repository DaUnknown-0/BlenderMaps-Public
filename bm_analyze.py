# bm_analyze.py - Messwerkzeuge fuer den Nachbau (nichts wird geraten, alles am Kartenfoto gemessen).
#
#   python bm_analyze.py colors <karte> x0 y0 x1 y1 [k]      haeufigste exakte Farben im Rechteck (Weltkoordinaten)
#   python bm_analyze.py lattice <karte> x0 y0 x1 y1          Gittervektoren eines Musters (Autokorrelation)
#   python bm_analyze.py profile <karte> x y dx dy n step     Farbfolge entlang eines Strahls

import sys

import numpy as np

from bm_ref import Ref


def colors(r, x0, y0, x1, y1, k=12):
    im = np.asarray(r.crop(x0, y0, x1, y1)).reshape(-1, 3)
    cols, cnt = np.unique(im, axis=0, return_counts=True)
    o = np.argsort(-cnt)
    tot = cnt.sum()
    return [(tuple(int(v) for v in cols[i]), round(cnt[i] / tot * 100, 2)) for i in o[:k]]


def lattice(r, x0, y0, x1, y1):
    """Zwei kuerzeste unabhaengige Gittervektoren (Einheiten) aus den Maxima der Autokorrelation."""
    im = np.asarray(r.crop(x0, y0, x1, y1)).astype(np.float64).mean(-1)
    im = im - im.mean()
    F = np.fft.fft2(im)
    ac = np.fft.ifft2(F * np.conj(F)).real
    ac = np.fft.fftshift(ac) / ac.max()
    h, w = ac.shape
    cy, cx = h // 2, w // 2
    # lokale Maxima
    pk = []
    R = min(h, w) // 2 - 2
    for y in range(cy - R, cy + R):
        for x in range(cx - R, cx + R):
            v = ac[y, x]
            if (x, y) == (cx, cy) or v < 0.25:
                continue
            if v == ac[y - 1:y + 2, x - 1:x + 2].max():
                pk.append((np.hypot(x - cx, y - cy), x - cx, cy - y, v))
    pk.sort()
    out = []
    for d, dx, dy, v in pk:
        if d < 3:
            continue
        if any(abs(dx * oy - dy * ox) < 1e-6 * d * d + 2 * d for _, ox, oy, _ in out) and out:
            # kolinear zu einem schon gefundenen Vektor
            if any(abs(dx * oy - dy * ox) < 0.15 * d * np.hypot(ox, oy) for _, ox, oy, _ in out):
                continue
        out.append((d, dx, dy, v))
        if len(out) == 2:
            break
    return [(round(dx / r.ppu, 4), round(dy / r.ppu, 4), round(v, 3)) for _, dx, dy, v in out]


def profile(r, x, y, dx, dy, n, step):
    res = []
    for i in range(n):
        px, py = r.w2p(x + dx * i * step, y + dy * i * step)
        res.append((round(x + dx * i * step, 3), round(y + dy * i * step, 3), tuple(int(v) for v in r.img[int(py), int(px)])))
    return res


if __name__ == "__main__":
    cmd, key = sys.argv[1], sys.argv[2]
    r = Ref(key)
    a = [float(v) for v in sys.argv[3:]]
    if cmd == "colors":
        for c, p in colors(r, *a[:4], k=int(a[4]) if len(a) > 4 else 12):
            print(f"  {c}  #{c[0]:02x}{c[1]:02x}{c[2]:02x}  {p} %")
    elif cmd == "lattice":
        print(lattice(r, *a[:4]))
    elif cmd == "profile":
        for row in profile(r, a[0], a[1], a[2], a[3], int(a[4]), a[5]):
            print(row)
