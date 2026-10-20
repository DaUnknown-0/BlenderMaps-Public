# bm_export_nf.py - laeuft IN Blender: gebautes Kartenmodell -> Laufzeitdaten fuer Nightfall (GPU-Modus).
#   blender -b out/<karte>/<karte>.blend -P blender/bm_export_nf.py -- out/<karte>
# Schreibt out/<karte>/nf/geo.npz (Dreiecke je Material, Ecken zusammengefasst) und meta.json (Materialien, Welt,
# Hoehenraster). pack_nf.py macht daraus die eine Datei <karte>.nfm mit eingebetteten Texturen.
#
# Licht: Nightfall rendert ungeleuchtet (Spielshader ohne Licht), deshalb wird das Licht des Modells in die
# Eckfarben gebacken: Grundhelligkeit + Leuchten des eigenen Raums (Abstand, Einfallswinkel), draussen Mondlicht.
# Grosse Dreiecke (Boeden, Waende) werden vorher bis auf 0,75 Kantenlaenge geteilt: Nightfall rechnet die Taschenlampe
# je Ecke (gleiche Formel wie der CPU-Renderer), das braucht Ecken in Lampenkegel-Aufloesung. Gruppen je Material und
# 8-m-Kachel, damit pro Bild nur die nahen Kacheln neu beleuchtet werden.
import bpy, json, math, os, sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(args[0])
DOC = json.load(open(os.path.join(OUT, "scene.json"), encoding="utf-8"))
MATS = DOC["materials"]
KIND = {m["name"]: m["kind"] for m in DOC["meshes"]}
ROOMS = set(DOC.get("rooms", {}))
LIGHTS = DOC.get("lights") or []
LP = np.array([l["pos"] for l in LIGHTS], np.float64).reshape(-1, 3)
LROOM = np.array([l.get("room") or "" for l in LIGHTS], object)
SUN = DOC.get("sun")
MAX_EDGE = 0.75
# Groebere Unterteilung fuer Flaechen, die man nur von weitem sieht (20.10.: Airship-Huelle 0,9 von 1,27 Mio. Dreiecken,
# Fungle-Gelaende 0,68 von 0,88 Mio.). Innenraeume bleiben bei MAX_EDGE: dort traegt die Eckendichte die Sichtkante.
EDGE_BY_COLL = {"Hull": 1.5, "Sky": 4.0, "Terrain": 1.0}
TILE = 8.0
AMBIENT_IN, AMBIENT_OUT = 0.40, 0.52
LAMP, LAMP_R = 0.62, 2.3
NF = os.path.join(OUT, "nf")
os.makedirs(NF, exist_ok=True)


def base_name(n):
    return n.rsplit(".", 1)[0] if len(n) > 4 and n[-4] == "." and n[-3:].isdigit() else n


def material_info(m):
    """(Schluessel, Beschreibung) eines Blender-Materials."""
    if m is None:
        return "none", {"kind": "color", "color": [128, 128, 128]}
    n = base_name(m.name)
    if n.startswith("outline_"):
        h = n[len("outline_"):]
        return n, {"kind": "outline", "color": [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]}
    if n == "lamp_panel":
        return n, {"kind": "color", "color": [255, 246, 228], "emit": True}
    spec = MATS.get(n)
    if spec is None:
        c = [int(round(max(0.0, min(1.0, v)) ** (1 / 2.2) * 255)) for v in m.diffuse_color[:3]]
        return n, {"kind": "color", "color": c}
    d = {"emit": bool(spec.get("emit"))}
    if "color" in spec:                                                   # Volltonfarbe (4x4-Bild)
        d.update(kind="color", color=[int(v) for v in spec["color"]])
    else:
        d.update(kind="alpha" if spec.get("alpha") else "tex", image=spec["image"],
                 wrap="repeat" if spec.get("uv") == "world" else "clamp",
                 point=spec.get("interp") == "Closest")
    return n, d


def subdivide(P, U, N, max_e=MAX_EDGE):
    """Dreiecke mit langer Kante in vier teilen (Mittelpunkte), bis alle Kanten <= max_e."""
    outP, outU, outN = [], [], []
    stack = [(P[i], U[i], N[i]) for i in range(len(P))]
    while stack:
        p, u, n = stack.pop()
        e = max(np.linalg.norm(p[0] - p[1]), np.linalg.norm(p[1] - p[2]), np.linalg.norm(p[2] - p[0]))
        if e <= max_e or len(outP) > 400000:
            outP.append(p); outU.append(u); outN.append(n)
            continue
        m01, m12, m20 = (p[0] + p[1]) / 2, (p[1] + p[2]) / 2, (p[2] + p[0]) / 2
        u01, u12, u20 = (u[0] + u[1]) / 2, (u[1] + u[2]) / 2, (u[2] + u[0]) / 2
        for q, w in (((p[0], m01, m20), (u[0], u01, u20)), ((m01, p[1], m12), (u01, u[1], u12)),
                     ((m20, m12, p[2]), (u20, u12, u[2])), ((m01, m12, m20), (u01, u12, u20))):
            stack.append((np.array(q), np.array(w), n))
    return np.array(outP), np.array(outU), np.array(outN)


def light(P, N, room, sky):
    """Helligkeit 0..1 je Ecke (P: (n,3), N: (n,3) Flaechennormale je Ecke)."""
    if sky:
        L = np.full(len(P), AMBIENT_OUT)
        if SUN:
            rx, ry, rz = [math.radians(v) for v in SUN.get("rot", [52, 0, 35])]
            d = np.array([math.sin(rx) * math.sin(rz), -math.sin(rx) * math.cos(rz), math.cos(rx)])
            L += 0.38 * np.clip(N @ d, 0, 1)
        L += 0.08 * np.clip(N[:, 2], 0, 1)
    else:
        L = np.full(len(P), AMBIENT_IN) + 0.05 * N[:, 2]
    if len(LP):
        sel = (LROOM == room) if room in ROOMS else np.ones(len(LP), bool)
        idx = np.nonzero(sel)[0]
        if room not in ROOMS and len(idx):
            c = P.mean(0)
            idx = idx[np.linalg.norm(LP[idx] - c, axis=1) < 12.0]
        for j in idx:
            v = LP[j] - P
            d = np.linalg.norm(v, axis=1) + 1e-6
            cosv = np.clip((v * N).sum(1) / d, 0, 1) * 0.75 + 0.25 * (np.abs(N[:, 2]) < 0.5)
            L += LAMP * cosv / (1.0 + (d / LAMP_R) ** 2)
    return np.clip(L, 0.0, 1.0)


def room_of(ob):
    for c in ob.users_collection:
        if c.name in ROOMS:
            return c.name
    return None


def main():
    deps = bpy.context.evaluated_depsgraph_get()
    groups = {}                                                         # Materialschluessel -> Listen
    infos = {}
    floor_objs = []
    ntri = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        kind = KIND.get(base_name(ob.name))
        room = room_of(ob)
        sky = kind in ("terrain",) or (room is None and kind in ("floor", "under", "ground"))
        max_e = min([EDGE_BY_COLL.get(c.name, MAX_EDGE) for c in ob.users_collection] or [MAX_EDGE])
        ev = ob.evaluated_get(deps)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        if not len(me.loop_triangles):
            ev.to_mesh_clear()
            continue
        mw = ob.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        co = np.array([tuple(mw @ v.co) for v in me.vertices], np.float64)
        uvl = me.uv_layers.active
        uvd = np.array([tuple(l.uv) for l in uvl.data], np.float64) if uvl else None
        tris = me.loop_triangles
        vi = np.array([tuple(t.vertices) for t in tris], np.int64)
        li = np.array([tuple(t.loops) for t in tris], np.int64)
        mi = np.array([t.material_index for t in tris], np.int64)
        fn = np.array([tuple((nm @ t.normal).normalized()) for t in tris], np.float64)
        # Gruben (pit_*) nicht ins Hoehenraster: niemand steht darin, sie liegen hinter Gelaendern unter einer
        # Plattform. Am Rand beruehrt der Spieler sie aber, und das Raster liess die Kamera dann 0,6 tief in die Grube
        # fallen (Meldungen Weapons 18.10.). Ohne Boden haelt Nightfall die letzte echte Hoehe.
        if kind in ("floor", "terrain") and not base_name(ob.name).startswith("pit_"):
            floor_objs.append(ob)
        for m_i in np.unique(mi):
            mat = ob.material_slots[m_i].material if m_i < len(ob.material_slots) else None
            key, info = material_info(mat)
            infos[key] = info
            sel = mi == m_i
            P = co[vi[sel]]                                              # (t,3,3)
            U = uvd[li[sel]] if uvd is not None else np.zeros((sel.sum(), 3, 2))
            N = fn[sel]
            big = np.max(np.stack([np.linalg.norm(P[:, 0] - P[:, 1], axis=1), np.linalg.norm(P[:, 1] - P[:, 2], axis=1),
                                   np.linalg.norm(P[:, 2] - P[:, 0], axis=1)]), axis=0) > max_e
            if big.any() and info["kind"] != "outline":
                p2, u2, n2 = subdivide(P[big], U[big], N[big], max_e)
                P = np.concatenate([P[~big], p2]); U = np.concatenate([U[~big], u2]); N = np.concatenate([N[~big], n2])
            Pf = P.reshape(-1, 3); Uf = U.reshape(-1, 2); Nf = np.repeat(N, 3, axis=0)
            if info["kind"] == "outline" or info.get("emit"):
                Lf = np.ones(len(Pf))
            else:
                Lf = light(Pf, Nf, room, sky)
            cen = P.mean(axis=1)
            tiles = np.floor(cen[:, :2] / TILE).astype(np.int64)
            for tx, ty in np.unique(tiles, axis=0):
                ts = (tiles[:, 0] == tx) & (tiles[:, 1] == ty)
                t3 = np.repeat(ts, 3)
                g = groups.setdefault((key, int(tx), int(ty)), {"P": [], "U": [], "L": [], "N": []})
                g["P"].append(Pf[t3].astype(np.float32)); g["U"].append(Uf[t3].astype(np.float32))
                g["L"].append(Lf[t3].astype(np.float32)); g["N"].append(Nf[t3].astype(np.float32))
            ntri += len(P)
        ev.to_mesh_clear()
    # Ecken zusammenfassen (gleiche Lage, UV, Normale, Helligkeit); Teilstuecke je Material und Kachel
    arrays, chunks = {}, []
    mkeys = sorted(infos)
    mats = [dict(infos[k], key=k) for k in mkeys]
    midx = {k: i for i, k in enumerate(mkeys)}
    for i, ((key, tx, ty), g) in enumerate(sorted(groups.items())):
        P = np.concatenate(g["P"]); U = np.concatenate(g["U"]); L = np.concatenate(g["L"]); N = np.concatenate(g["N"])
        q = np.concatenate([np.round(P * 2000), np.round(U * 4096), np.round(N * 100), np.round(L[:, None] * 255)],
                           axis=1).astype(np.int64)
        uq, inv = np.unique(q, axis=0, return_inverse=True)
        first = np.zeros(len(uq), np.int64)
        first[inv[::-1]] = np.arange(len(inv))[::-1]
        arrays[f"p{i}"] = P[first]
        arrays[f"u{i}"] = U[first]
        arrays[f"n{i}"] = np.clip(np.round(N[first] * 127), -127, 127).astype(np.int8)
        arrays[f"l{i}"] = (L[first] * 255).round().astype(np.uint8)
        arrays[f"i{i}"] = inv.reshape(-1).astype(np.uint32)
        chunks.append({"mat": midx[key], "tx": tx, "ty": ty})
    np.savez_compressed(os.path.join(NF, "geo.npz"), **arrays)
    # Hoehenraster: oberster Boden je Zelle (0,125), cm, -32768 = kein Boden
    grid = None
    if floor_objs:
        bvs = []
        lo = np.array([1e9, 1e9]); hi = np.array([-1e9, -1e9])
        for ob in floor_objs:
            ev = ob.evaluated_get(deps)
            bv = BVHTree.FromObject(ev, deps)
            bvs.append((bv, ob.matrix_world.copy()))
            for c in ob.bound_box:
                w = ob.matrix_world @ Vector(c)
                lo = np.minimum(lo, [w.x, w.y]); hi = np.maximum(hi, [w.x, w.y])
        cell = 0.125
        gw, gh = int(math.ceil((hi[0] - lo[0]) / cell)) + 1, int(math.ceil((hi[1] - lo[1]) / cell)) + 1
        H = np.full((gh, gw), -32768, np.int32)
        down = Vector((0, 0, -1))
        for j in range(gh):
            y = lo[1] + (j + 0.5) * cell
            for i in range(gw):
                x = lo[0] + (i + 0.5) * cell
                best = None
                for bv, mw in bvs:
                    hit = bv.ray_cast(Vector((x - mw.translation.x, y - mw.translation.y, 80.0 - mw.translation.z)), down)
                    if hit[0] is not None:
                        z = hit[0].z + mw.translation.z
                        if best is None or z > best:
                            best = z
                if best is not None:
                    H[j, i] = int(round(best * 100))
        grid = {"x0": float(lo[0]), "y0": float(lo[1]), "cell": cell, "w": gw, "h": gh}
        np.save(os.path.join(NF, "height.npy"), np.clip(H, -32768, 32767).astype(np.int16))
    meta = {"map": DOC["map"], "H": DOC["H"], "world": DOC.get("world"), "sun": SUN is not None, "materials": mats,
            "chunks": chunks, "tile": TILE, "grid": grid, "triangles": int(ntri)}
    json.dump(meta, open(os.path.join(NF, "meta.json"), "w", encoding="utf-8"))
    print("BM nf", DOC["map"], "Dreiecke", ntri, "Materialien", len(mats), "Teile", len(chunks), "Raster",
          grid and (grid["w"], grid["h"]))


main()
