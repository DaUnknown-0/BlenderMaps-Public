# bm_plan.py: Grundriss einer Karte aus der Spielgeometrie.
#
# Begehbar ist, was man vom Spawn aus erreicht, ohne eine Ship-Collider-Linie (Wandfuss) zu kreuzen; Tueren
# zaehlen als offen. Das Raster (RES Pixel pro Einheit) wird danach wieder zu Polygonen und nach den
# Raum-Triggern (AreaCollider) aufgeteilt. Alles, was innerhalb der Huelle nicht begehbar ist, wird Wandmasse.

import cv2
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

from bm_ref import Ref, zone_name

RES = 40                  # Rasterpunkte pro Einheit (0,025)
SIMPLIFY = 0.02           # Toleranz beim Vereinfachen der Umrisse


class Plan:
    """layers: Collider-Ebenen, die als Wand gelten. Tuer-Schatten (Objects/tall unter .../xxxDoor) bleiben offen.
    Lueckenschliesser: solange der Spawn den Kartenrand erreicht, wird der engste Punkt des Weges dorthin mit
    einem Pfropfen verschlossen (Protokoll in self.closed); max_gap begrenzt, was als Luecke gelten darf."""

    def __init__(self, ref: Ref, layers=("Ship",), extra_barriers=(), extra_seeds=(), max_gap=0.6, max_fix=40,
                 hull_color=None):
        self.ref = ref
        mn, mx = ref.mn, ref.mx
        self.ox, self.oy = mn[0], mx[1]
        self.gw = int((mx[0] - mn[0]) * RES) + 1
        self.gh = int((mx[1] - mn[1]) * RES) + 1
        bar = np.zeros((self.gh, self.gw), np.uint8)
        for w, pts in ref.colliders(layers):
            if "Door" in w["path"].split("/")[-2 if w["path"].count("/") >= 2 else -1]:
                continue
            cv2.polylines(bar, [self._px(pts)], False, 255, thickness=2)
        for pts in extra_barriers:
            cv2.polylines(bar, [self._px(pts)], False, 255, thickness=2)
        seeds = [tuple(ref.world["spawn"])] + list(extra_seeds)
        # Ziele, die der Spawn NICHT erreichen darf: der Kartenrand und jede groessere Flaeche in Huellenfarbe
        targets = [(1, 1)] + self._hull_seeds(hull_color) if hull_color else [(1, 1)]
        self.closed = []
        for _ in range(max_fix):
            free = (bar == 0).astype(np.uint8)
            n, lab = cv2.connectedComponents(free, connectivity=4)
            sl = {int(lab[self._p(s)[1], self._p(s)[0]]) for s in seeds} - {0}
            leak = next((t for t in targets if int(lab[t[1], t[0]]) in sl), None)
            if leak is None:
                break
            gap = self._narrowest(free, self._p(seeds[0]), leak)
            if gap is None or gap[2] > max_gap * RES:
                raise RuntimeError(f"Grundriss undicht zu {self._w(*leak)}, engste Stelle {gap} zu breit")
            x, y, c = gap
            cv2.circle(bar, (x, y), int(c) + 2, 255, -1)
            self.closed.append((round(self.ox + x / RES, 3), round(self.oy - y / RES, 3), round(c / RES, 3)))
        free = (bar == 0).astype(np.uint8)
        n, lab = cv2.connectedComponents(free, connectivity=4)
        keep = {int(lab[self._p(s)[1], self._p(s)[0]]) for s in seeds} - {0}
        walk = np.isin(lab, list(keep)).astype(np.uint8)
        # Linien selbst gehoeren zur Haelfte zum Boden: einmal aufweiten schliesst die 2-px-Fuge am Wandfuss
        walk = cv2.dilate(walk, np.ones((3, 3), np.uint8))
        self.walk_mask = walk
        self.walk = self._polys(walk)

    def _hull_seeds(self, color, tol=6, min_area=0.4):
        """Je groesserer Flaeche in Huellenfarbe ein innerer Punkt (Rasterkoordinaten)."""
        img = self.ref.img.astype(np.int16)
        m = (np.abs(img - np.array(color, np.int16)).sum(-1) <= tol).astype(np.uint8)
        # Atlaspixel -> Plan-Raster (beide nordbuendig ab mn/mx)
        m = cv2.resize(m, (int(round(self.ref.W * RES / self.ref.ppu)), int(round(self.ref.H * RES / self.ref.ppu))),
                       interpolation=cv2.INTER_NEAREST)
        g = np.zeros((self.gh, self.gw), np.uint8)
        h, w = min(g.shape[0], m.shape[0]), min(g.shape[1], m.shape[1])
        g[:h, :w] = m[:h, :w]
        g = cv2.erode(g, np.ones((3, 3), np.uint8), iterations=2)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(g, connectivity=4)
        out = []
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] < min_area * RES * RES:
                continue
            blob = (lab == i).astype(np.uint8)
            d = cv2.distanceTransform(blob, cv2.DIST_L2, 3)
            y, x = np.unravel_index(int(d.argmax()), d.shape)
            out.append((int(x), int(y)))
        return out

    def _narrowest(self, free, s, t):
        """Engpass des BREITESTEN Weges s -> t (x, y, Freiraum in px): der groesste Freiraum c, bei dem s und t
        noch verbunden sind, und die Stelle, an der der Weg bei c+1 abreisst. Der kuerzeste Weg taugt dazu nicht,
        er schmiegt sich ueberall an Hindernisse."""
        clear = cv2.distanceTransform(free, cv2.DIST_L2, 5)

        def labels(th):
            return cv2.connectedComponents((clear >= th).astype(np.uint8), connectivity=4)[1]

        def joined(th):
            lab = labels(th)
            a, b = lab[s[1], s[0]], lab[t[1], t[0]]
            return a != 0 and a == b

        if not joined(0.5):
            return None
        lo, hi = 0.5, float(clear.max())
        for _ in range(24):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if joined(mid) else (lo, mid)
        c = lo
        up = labels(c + 1.0)
        mask = (clear >= c).astype(np.uint8)
        A = ((up == up[s[1], s[0]]) & (mask > 0)).astype(np.uint8)
        B = ((up == up[t[1], t[0]]) & (mask > 0)).astype(np.uint8)
        # Fronten von beiden Seiten im Freiraum >= c wachsen lassen; wo sie sich zuerst treffen, liegt die Luecke
        k = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        dA = np.where(A > 0, 0, 10 ** 6).astype(np.int32)
        dB = np.where(B > 0, 0, 10 ** 6).astype(np.int32)
        fa, fb = A.copy(), B.copy()
        for step in range(1, 4000):
            na = cv2.dilate(fa, k) & mask
            nb = cv2.dilate(fb, k) & mask
            dA[(na > 0) & (fa == 0)] = step
            dB[(nb > 0) & (fb == 0)] = step
            if ((na > 0) & (nb > 0)).any():
                tot = dA.astype(np.int64) + dB
                y, x = np.unravel_index(int(tot.argmin()), tot.shape)
                return int(x), int(y), c
            if (na == fa).all() and (nb == fb).all():
                return None
            fa, fb = na, nb
        return None

    def _p(self, p):
        return int(round((p[0] - self.ox) * RES)), int(round((self.oy - p[1]) * RES))

    def _px(self, pts):
        return np.array([self._p(p) for p in pts], np.int32).reshape(-1, 1, 2)

    def _w(self, px, py):
        return self.ox + px / RES, self.oy - py / RES

    def _polys(self, mask):
        cs, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hier is None:
            return MultiPolygon()
        hier = hier[0]
        polys = []
        for i, c in enumerate(cs):
            if hier[i][3] != -1:
                continue                                              # Loch, wird beim Elternteil verarbeitet
            shell = [self._w(p[0][0], p[0][1]) for p in c]
            holes = []
            j = hier[i][2]
            while j != -1:
                holes.append([self._w(p[0][0], p[0][1]) for p in cs[j]])
                j = hier[j][0]
            if len(shell) >= 3:
                pg = Polygon(shell, [h for h in holes if len(h) >= 3]).buffer(0)
                if pg.area > 0.01:
                    polys.append(pg.simplify(SIMPLIFY))
        return unary_union(polys)

    def rooms(self, priority=(), rest_name=None, overrides=()):
        """Begehbare Flaeche je Raum: Schnitt mit den AreaCollidern, Rest an den naechsten Raum.
        overrides: [(name, polygon)] vor allen Zonen (z. B. Freiflaechen innerhalb einer Zone); rest_name: groessere
        Restflaechen ausserhalb aller Zonen (Gelaende) bekommen diesen Namen statt des naechsten Raums."""
        zs = self.ref.zones()
        order = sorted(zs, key=lambda z: (0 if zone_name(z) in priority else 1, Polygon(z["paths"][0]).area))
        taken = Polygon()
        out = {}
        for name, pts in overrides:
            zp = Polygon(pts).buffer(0)
            part = self.walk.intersection(zp).difference(taken)
            out[name] = unary_union([out[name], part]) if name in out else part
            taken = unary_union([taken, zp])
        for z in order:
            zp = unary_union([Polygon(p) for p in z["paths"]]).buffer(0)
            part = self.walk.intersection(zp).difference(taken)
            name = zone_name(z)
            out[name] = unary_union([out[name], part]) if name in out else part
            taken = unary_union([taken, zp])
        rest = self.walk.difference(taken)
        for g in getattr(rest, "geoms", [rest]):
            if g.is_empty or g.area < 1e-4:
                continue
            if rest_name and g.area > 3.0:
                out[rest_name] = unary_union([out[rest_name], g]) if rest_name in out else g
                continue
            best = min(out, key=lambda n: out[n].distance(g))
            out[best] = unary_union([out[best], g])
        return {n: g.buffer(0) for n, g in out.items() if not g.is_empty}
