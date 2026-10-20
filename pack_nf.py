# pack_nf.py <karte> [max_tex]: out/<karte>/nf (bm_export_nf.py) -> out/<karte>/<karte>.nfm, die eine Datei, die
# Nightfall im GPU-Modus laedt. Texturen werden auf max_tex^2 Pixel Flaeche (Standard 1448, ~2,1 MPx) und 4096 Pixel
# Seitenlaenge begrenzt, Kantenlaengen auf Vielfache von 4 (DXT-Kompression im Spiel) und als PNG eingebettet.
# ACHTUNG: Neu packen aendert die SHA-256 der Atlas-Pakete; die oeffentlichen (museum/wald/park) dann ueber
# publish_nf.py samt Katalog neu veroeffentlichen, sonst lehnt Nightfall sie ab.
#
# Format NFM2 (little endian):
#   "NFM2" u32 version=2 | str map | f32 H | u8 r,g,b Welt | u8 draussen | f32 Kachel
#   u32 nTex  { str name | u8 wrap(0 clamp,1 repeat) | u8 point | u32 len | PNG }
#   u32 nMat  { u8 kind(0 tex,1 color,2 alpha,3 outline) | i32 tex | u8 r,g,b | u8 emit }
#   u32 nChunk { u32 mat | i16 tileX,tileY | u32 nVert | u32 nIdx | f32 xyz*nVert | f32 uv*nVert | i8 nxyz*nVert
#                | u8 licht*nVert | u32 idx*nIdx }
#   Raster: u8 da | f32 x0,y0,cell | u32 w,h | i16 cm*w*h (-32768 = kein Boden)
# Koordinaten wie Among Us: x Ost, y Nord, z Hoehe.
import io
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent


def s(b, t):
    d = t.encode("utf-8")
    b += struct.pack("<H", len(d)) + d


def main():
    key = sys.argv[1]
    # Grenze als FLAECHE (max_tex^2), laengste Seite hoechstens 4096: die Wandbilder sind hohe Streifen (eine Zeile je
    # Wandkante, z. B. 199 x 3222), die Seitengrenze 1024 hatte sie auf ein Drittel verkleinert (unscharfe Waende in
    # den Meldungen 18.10.).
    max_tex = int(sys.argv[2]) if len(sys.argv) > 2 else 1448
    out = ROOT / "out" / key
    nf = out / "nf"
    meta = json.loads((nf / "meta.json").read_text(encoding="utf-8"))
    geo = np.load(nf / "geo.npz")
    texs, tex_index = [], {}
    for m in meta["materials"]:
        if m["kind"] in ("tex", "alpha"):
            img = m["image"]
            if img not in tex_index:
                tex_index[img] = len(texs)
                texs.append({"name": img, "wrap": m["wrap"] == "repeat", "point": bool(m.get("point"))})
            else:
                t = texs[tex_index[img]]
                t["wrap"] = t["wrap"] or m["wrap"] == "repeat"
    b = bytearray(b"NFM2")
    b += struct.pack("<I", 2)
    s(b, meta["map"])
    world = meta.get("world") or [20, 20, 30]
    b += struct.pack("<f3BBf", float(meta["H"]), *[int(v) for v in world[:3]], 1 if meta.get("sun") else 0,
                     float(meta.get("tile", 8.0)))
    b += struct.pack("<I", len(texs))
    raw_total = 0
    for t in texs:
        im = Image.open(out / "tex" / t["name"])
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        w, h = im.size
        f = min(1.0, max_tex / (w * h) ** 0.5, 4096 / max(w, h))
        nw, nh = max(4, int(round(w * f / 4)) * 4), max(4, int(round(h * f / 4)) * 4)
        if (nw, nh) != (w, h):
            im = im.resize((nw, nh), Image.NEAREST if t["point"] else Image.LANCZOS)
        bio = io.BytesIO()
        im.save(bio, "PNG", optimize=True)
        data = bio.getvalue()
        raw_total += nw * nh
        s(b, t["name"])
        b += struct.pack("<BBI", 1 if t["wrap"] else 0, 1 if t["point"] else 0, len(data)) + data
    kinds = {"tex": 0, "color": 1, "alpha": 2, "outline": 3}
    b += struct.pack("<I", len(meta["materials"]))
    for m in meta["materials"]:
        col = m.get("color") or [255, 255, 255]
        ti = tex_index.get(m.get("image"), -1) if m["kind"] in ("tex", "alpha") else -1
        b += struct.pack("<Bi3BB", kinds[m["kind"]], ti, *[int(v) for v in col[:3]], 1 if m.get("emit") else 0)
    b += struct.pack("<I", len(meta["chunks"]))
    nv_total = ni_total = 0
    for i, c in enumerate(meta["chunks"]):
        P = geo[f"p{i}"].astype("<f4"); U = geo[f"u{i}"].astype("<f4"); N = geo[f"n{i}"].astype(np.int8)
        L = geo[f"l{i}"].astype(np.uint8); I = geo[f"i{i}"].astype("<u4")
        b += struct.pack("<IhhII", c["mat"], c["tx"], c["ty"], len(P), len(I))
        b += P.tobytes() + U.tobytes() + N.tobytes() + L.tobytes() + I.tobytes()
        nv_total += len(P); ni_total += len(I)
    g = meta.get("grid")
    if g:
        Hh = np.load(nf / "height.npy").astype("<i2")
        b += struct.pack("<BfffII", 1, g["x0"], g["y0"], g["cell"], g["w"], g["h"]) + Hh.tobytes()
    else:
        b += struct.pack("<B", 0)
    f = out / f"{key}.nfm"
    f.write_bytes(bytes(b))
    print(f"{f.name}: {len(b) / 1048576:.1f} MB, {len(texs)} Texturen ({raw_total / 1e6:.1f} MPx), "
          f"{len(meta['materials'])} Materialien, {len(meta['chunks'])} Teile, {nv_total} Ecken, {ni_total // 3} Dreiecke")


if __name__ == "__main__":
    main()
