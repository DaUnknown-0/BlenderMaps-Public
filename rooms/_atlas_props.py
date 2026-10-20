# Gemeinsamer Requisitenbau fuer die eigenen Karten (Unknown's Atlas und optionale Erweiterungen).
#
# Die Karten zeichnen jedes Objekt mit museum_art.Prop: schraege Aufsicht K = 0,55 (Hoehe h steht h*K nach oben),
# Oberseite in voller Tiefe, Leinwand ringsum 0,3 m Rand (PROP_PAD). Daraus: Grundriss = Glas-/Hindernis-Collider,
# dessen Suedkante auf der Standlinie liegt (sonst Fussstreifen), Hoehe h = (Sprite-Oberkante - Rand - Nordkante) / K.
# Front = Sprite-Streifen [Suedkante, Suedkante + h*K], Oberseite = [Suedkante + h*K, Nordkante + h*K], jeweils nur
# in der Breite des Grundrisses. Hohe schlanke Dinge (Lampen, Baeume, Skelett) als senkrechte Tafel mit Durchsicht.

import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box as sbox

import bm_tex as T
from bm_spec import box, prism
import _atlas_models as AM

K = 0.55
PAD = 0.3


def _footprints(ref):
    out = []
    for w in ref.world["walls"]:
        if "/Glass" in w["path"] or "/Opaque" in w["path"]:
            for p in w["paths"]:
                if len(p) >= 3:
                    out.append(Polygon(p).buffer(0))
    return out


def _clip(spr, thr=160):
    """Lichthof-Schimmer (halbdurchsichtig) weg: Alpha hart an der Schwelle."""
    a = np.asarray(spr).copy()
    a[..., 3] = np.where(a[..., 3] >= thr, 255, 0)
    return Image.fromarray(a)


def _flat(spr, rgb):
    bg = Image.new("RGBA", spr.size, tuple(rgb) + (255,))
    bg.alpha_composite(spr)
    return bg.convert("RGB")


def build(sc, ctx, pads=None, max_h=8.0, caps=None, skip=()):
    """caps: Hoehenobergrenze je Art (z. B. Sockel, deren Sprite Aufbauten zeigt, die eigene Objekte sind);
    skip: Arten, die die Kartendatei selbst baut."""
    caps = caps or {}
    ref = sc.ref
    sheet = ref.sheet
    feet = _footprints(ref)
    import json
    from bm_ref import ROOT
    hf = ROOT / "atlasdata" / sc.key / "heights.json"
    table = json.loads(hf.read_text(encoding="utf-8")) if hf.exists() else {"h": {}, "pad": {}}
    pads = dict(table.get("pad", {}), **(pads or {}))
    heights = table.get("h", {})
    parts = []
    stats = {"modell": {}, "rest": {}}
    for i, p in enumerate(ref.world["props"]):
        if p["name"] in skip:
            continue
        (x0, y0), (x1, y1) = p["min"], p["max"]
        pad = pads.get(p["name"], PAD)
        base = p.get("baseY", y0 + pad)
        fx0, fx1 = p.get("foot", [x0 + pad, x1 - pad])
        if fx1 - fx0 < 0.05:
            fx0, fx1 = x0 + pad, x1 - pad
        probe = sbox(fx0 + 0.02, base - 0.05, fx1 - 0.02, base + 0.25)
        cands = [f for f in feet if f.intersects(probe) and abs(f.bounds[1] - base) < 0.45]
        fp = max(cands, key=lambda f: f.intersection(probe).area) if cands else None
        if fp is None:
            # ohne Collider: Tiefe aus der Zeichnung (Spriteoberkante = Standlinie + Tiefe + h*K)
            hh0 = heights.get(p["name"])
            dep = (y1 - pad - base - hh0 * K) if hh0 else 0.3
            fp = sbox(fx0, base, fx1, base + min(3.0, max(0.15, dep)))
        bx0, by0, bx1, by1 = fp.bounds
        h = heights.get(p["name"]) or (y1 - pad - by1) / K                 # echte Hoehe aus der Zeichentabelle
        if h < 0.05:
            continue
        h = min(h, max_h, caps.get(p["name"], 99.0))
        a, b, w, hh = p["rect"]
        spr = sheet.crop((a, b, a + w, b + hh))
        arr = np.asarray(spr)
        cover = (arr[..., 3] > 100).mean()
        if cover < 0.003:
            continue
        ppm = w / (x1 - x0)
        if p["name"] in AM.MODELS:
            # echter 3D-Koerper (rooms/_atlas_models.py, 19.10.)
            try:
                ps = AM.build(AM.Prop(ctx, sc, i, p, fp, h, spr, pad, base))
            except Exception:
                import traceback
                traceback.print_exc()
                ps = None
            if ps:
                parts += ps
                stats["modell"][p["name"]] = stats["modell"].get(p["name"], 0) + 1
                continue
        stats["rest"][p["name"]] = stats["rest"].get(p["name"], 0) + 1

        def row(y):                                                        # Bild-y (Welt) -> Sprite-Zeile
            return int(round((y1 - y) * ppm))

        def col(x):
            return int(round((x - x0) * ppm))
        rgb = arr[..., :3][arr[..., 3] > 100]
        avg = tuple(int(v) for v in (rgb.mean(0) if len(rgb) else (120, 120, 120)))
        flat = _flat(spr, avg)
        nm = f"ap_{sc.key}_{i}"
        side = ctx.color(f"ap_{sc.key}_side_{i}", avg)
        if (y1 - y0 - 2 * pad) < 0.6 * h * K and h > 1.0:
            # schwebendes Teilstueck eines hohen Objekts (Kopf, Kiefer): Tafel in seiner gezeichneten Hoehe
            tex = ctx.tex(nm + "_card", _clip(spr), uv="part")
            ctx.scene.mats[tex]["alpha"] = True
            yc = (by0 + by1) / 2                                           # Tafel steht auf der Grundrissmitte:
            z0 = max(0.0, (y0 + pad - yc) / K)                             # Hoehe = (Bild-y - Tafel-y) / K
            c = box((x0 + x1) / 2, yc + 0.03, x1 - x0, 0.02, z0, z0 + (y1 - y0) / K, side)
            c["front"] = tex
            c["front_both"] = True
            parts.append(c)
            continue
        if (fp.area < 0.4 and h > 2.2) or (cover < 0.3 and h > 1.2):
            # schlank und hoch: Tafel mit Durchsicht an der Standlinie, zugeschnitten auf den sichtbaren Inhalt
            cs = _clip(spr)
            bbx = cs.getbbox()
            if not bbx:
                continue
            cs = cs.crop(bbx)
            cx0w, cx1w = x0 + bbx[0] / ppm, x0 + bbx[2] / ppm
            ytop, ybot = y1 - bbx[1] / ppm, y1 - bbx[3] / ppm
            yc = min(max(ybot, by0), by1)                                  # Fuss der Zeichnung, sonst Grundriss
            zc0, zc1 = max(0.0, (ybot - yc) / K), max(0.3, (ytop - yc) / K)
            tex = ctx.tex(nm + "_card", cs.resize((max(2, cs.width // 2), max(2, cs.height // 2)), Image.NEAREST), uv="part")
            ctx.scene.mats[tex]["alpha"] = True
            # massiver Umriss statt Papiertafel: Silhouette mit Durchbruechen, Dicke aus dem Grundriss; schlanke Dinge
            # als Kreuz aus zwei Scheiben (von allen Seiten sichtbar)
            from bm_spec import slab, sprite_outline
            outl = sprite_outline(cs, cx0w, ytop, ppm, lambda yd, yc=yc: max(0.0, (yd - yc) / K), min_px=20, tol=0.01)
            if outl.is_empty:
                continue
            thick = max(0.06, min(0.6, (by1 - by0) * 0.8, (cx1w - cx0w) * 0.5))
            bb = (cx0w, zc0, cx1w, zc1)
            rots = (0.0, 90.0) if (cx1w - cx0w) < 1.2 else (0.0,)
            for rot in rots:
                parts.append(slab(outl, yc, thick, side, face=tex, bbox=bb, rot=rot, cx=(cx0w + cx1w) / 2,
                                  outline=(20, 20, 24)))
            continue
        cx0, cx1 = max(0, col(bx0)), min(w, col(bx1))
        if cx1 - cx0 < 2:
            cx0, cx1 = 0, w
        r_front_top, r_base = max(0, row(by0 + h * K)), min(hh, row(by0))
        r_top_top = max(0, row(by1 + h * K))
        front = top = None
        def face_tex(tag, box_):
            sub = spr.crop(box_)
            al = np.asarray(sub)[..., 3]
            if (al < 100).mean() > 0.12:
                # viel Durchsicht: wie im Spiel ueber den gezeichneten Boden an derselben Bildstelle legen
                c0, r0, c1, r1 = box_
                bg = ref.crop(x0 + c0 / ppm, y1 - r1 / ppm, x0 + c1 / ppm, y1 - r0 / ppm).convert("RGBA").resize(sub.size)
                bg.alpha_composite(sub)
                return ctx.tex(nm + tag, T.label_upscale(bg.convert("RGB"), 1.0), uv="part")
            return ctx.tex(nm + tag, T.label_upscale(flat.crop(box_), 1.0), uv="part")
        if r_base - r_front_top > 2:
            front = face_tex("_front", (cx0, r_front_top, cx1, r_base))
        if r_front_top - r_top_top > 2:
            top = face_tex("_top", (cx0, r_top_top, cx1, r_front_top))
        parts.append(prism(fp.simplify(0.01), 0.0, h, side, top=top, front=front, outline=(20, 20, 24)))
    print(f"atlas_props {sc.key}: {sum(stats['modell'].values())} Modelle, Rest {stats['rest']}")
    return [{"name": "atlas_props", "coll": "Props", "kind": "parts", "parts": parts}]


def room_heights(sc, margin=0.6):
    """Raumhoehe je Raum: hoechstes Objekt (Hoehentabelle) + margin, mindestens die Wandhoehe (nur Innenkarten)."""
    if sc.cfg.get("sky_all"):
        sc.auto_h = {}
        return {}
    import json
    from shapely.geometry import Point
    from bm_ref import ROOT
    hf = ROOT / "atlasdata" / sc.key / "heights.json"
    heights = json.loads(hf.read_text(encoding="utf-8")).get("h", {}) if hf.exists() else {}
    out = {}
    for p in sc.ref.world["props"]:
        h = heights.get(p["name"])
        if not h:
            continue
        fx0, fx1 = p.get("foot", [p["min"][0], p["max"][0]])
        pt = Point((fx0 + fx1) / 2, p.get("baseY", p["min"][1]) + 0.2)
        room = min(sc.rooms, key=lambda n: sc.rooms[n].distance(pt))
        if sc.rooms[room].distance(pt) < 0.5 and h + margin > sc.H:
            out[room] = max(out.get(room, 0.0), h + margin)
    sc.auto_h = out
    return out
