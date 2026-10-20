# bm_pick.py - laeuft IN Blender: was sieht die Spielkamera einer Nightfall-Meldung wo? Strahlen durch ein Raster
# von Bildpunkten (oder einzelne Punkte) in das Modell, je Treffer Objekt + Material.
#   blender -b <karte>.blend -P blender/bm_pick.py -- <picks.json> <out.json>
#   picks.json: [{"name": .., "pos": [x, y, z], "yaw": grad, "pitch": grad, "vfov": grad, "aspect": w/h,
#                 "grid": [nx, ny]} | ... "points": [[u, v], ...]}]   (u, v = 0..1, v von oben)
# Kamera wie Nightfall (GpuWorld): Blick (cos h cos p, sin h cos p, sin p), senkrechtes Sichtfeld vfov.
import bpy, json, math, sys
from mathutils import Vector

a = sys.argv[sys.argv.index("--") + 1:]
views = json.load(open(a[0], encoding="utf-8"))
deps = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene


def ray(v, u, w):
    h, p = math.radians(v["yaw"]), math.radians(v["pitch"])
    f = Vector((math.cos(h) * math.cos(p), math.sin(h) * math.cos(p), math.sin(p)))
    r = Vector((math.sin(h), -math.cos(h), 0.0))
    up = r.cross(f)
    tv = math.tan(math.radians(v["vfov"]) / 2)
    th = tv * v["aspect"]
    return (f + r * ((u * 2 - 1) * th) + up * ((1 - w * 2) * tv)).normalized()


def material_at(ob, idx):
    try:
        me = ob.evaluated_get(deps).data
        if idx < len(me.polygons):
            mi = me.polygons[idx].material_index
            if mi < len(ob.material_slots) and ob.material_slots[mi].material:
                return ob.material_slots[mi].material.name
    except Exception:
        pass
    return None


def hit(v, u, w):
    """Erster Treffer, Konturhuellen (outline_*, umgestuelpte Huelle um jedes Teil) werden durchschritten."""
    o0 = Vector(v["pos"])
    d = ray(v, u, w)
    o = o0
    for _ in range(8):
        ok, loc, nrm, idx, ob, _m = sc.ray_cast(deps, o, d, distance=40.0)
        if not ok:
            return None
        mat = material_at(ob, idx)
        if mat and mat.startswith("outline_"):
            o = loc + d * 0.002
            continue
        return {"obj": ob.name, "mat": mat, "at": [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)],
                "n": [round(nrm.x, 2), round(nrm.y, 2), round(nrm.z, 2)], "d": round((loc - o0).length, 2)}
    return None


out = []
for v in views:
    res = {"name": v["name"], "hits": []}
    pts = v.get("points")
    if not pts:
        nx, ny = v.get("grid", [32, 18])
        pts = [((i + 0.5) / nx, (j + 0.5) / ny) for j in range(ny) for i in range(nx)]
    for u, w in pts:
        hh = hit(v, u, w)
        res["hits"].append({"u": round(u, 3), "v": round(w, 3), **(hh or {"obj": None})})
    out.append(res)
json.dump(out, open(a[1], "w", encoding="utf-8"), indent=1)
print("BM pick", len(out))
