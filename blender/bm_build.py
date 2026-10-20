# bm_build.py - laeuft IN Blender (5.2):
#   blender -b --factory-startup -P blender/bm_build.py -- <out/karte> model            -> <karte>.blend + <karte>.glb
#   blender -b --factory-startup -P blender/bm_build.py -- <out/karte> compare [raum..] -> cmp/<raum>_bl.png
#
# Liest scene.json (bm_scene.py). Einheiten = AU-Einheiten, z = Hoehe. Jedes Material hat eine Bildtextur
# (auch Flaechenfarben als 4x4-Bild), damit Workbench im Modus TEXTURE exakt die Texturfarben zeigt und der
# glTF-Export alles mitnimmt.
#
# Vergleich: nur Boden, Nordwaende und Huellengrund; die Nordwaende werden wie in Among Us geschert
# (y' = y + k*z), Rueckseiten ausgeblendet. So entsteht dieselbe Ansicht wie das Kartenfoto.

import json
import math
import os
import sys
import functools
import builtins

import bpy

print = functools.partial(builtins.print, flush=True)

args = sys.argv[sys.argv.index("--") + 1:]
OUT = os.path.abspath(args[0])
MODE = args[1] if len(args) > 1 else "model"
ONLY = set(args[2:])
DOC = json.load(open(os.path.join(OUT, "scene.json"), encoding="utf-8"))
TEX = os.path.join(OUT, "tex")
K = DOC["k"]


def srgb2lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def make_material(name, spec):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = spec.get("rough", 0.8)
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(os.path.join(TEX, spec["image"]), check_existing=True)
    img.colorspace_settings.name = "sRGB"
    tex.image = img
    tex.interpolation = spec.get("interp", "Linear")
    tex.extension = "REPEAT" if spec.get("uv") == "world" else "EXTEND"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if spec.get("alpha"):                                                     # Zaun, Glas: Durchsicht aus dem Bild
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            m.blend_method = "BLEND"
        m.use_backface_culling = False
    if spec.get("emit"):
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = spec["emit"] * 0.35     # mit Licht im Raum sonst ueberstrahlt
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    nt.nodes.active = tex
    if "color" in spec:
        m.diffuse_color = [srgb2lin(v) for v in spec["color"]] + [1.0]
    return m


def tri_uv(spec, x, y):
    uv = spec.get("uv")
    if uv == "bbox":
        x0, y0, x1, y1 = spec["bbox"]
        return ((x - x0) / max(1e-6, x1 - x0), (y - y0) / max(1e-6, y1 - y0))
    if uv == "world":
        s = spec.get("scale", 1.0)
        sx, sy = (s, s) if not isinstance(s, (list, tuple)) else s
        ox, oy = spec.get("offset", (0.0, 0.0))
        return ((x - ox) / sx, (y - oy) / sy)
    return (0.5, 0.5)


OUTLINE_W = 0.022


def outline_material(rgb):
    name = "outline_%02x%02x%02x" % tuple(rgb)
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = [srgb2lin(v) for v in rgb] + [1.0]
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    m.diffuse_color = [srgb2lin(v) for v in rgb] + [1.0]
    m.use_backface_culling = True
    return m


def build_parts(m, mats, shear=0.0):
    """Einrichtung, je Konturfarbe ein Objekt; Kontur als umgestuelpte Huelle (Solidify, Normalen gedreht)."""
    groups = {}
    for p in m["parts"]:
        groups.setdefault(tuple(p.get("outline") or ()), []).append(p)
    obs = []
    for i, (oc, parts) in enumerate(groups.items()):
        ob = _build_parts(dict(m, name=m["name"] + (f"_{i}" if i else ""), parts=parts), mats, shear)
        if oc:
            me = ob.data
            me.materials.append(outline_material(oc))
            mod = ob.modifiers.new("Kontur", "SOLIDIFY")
            mod.thickness = OUTLINE_W
            mod.offset = 1.0
            mod.use_flip_normals = True
            mod.use_even_offset = True
            mod.use_rim = False
            mod.material_offset = len(me.materials) - 1
            mod.material_offset_rim = len(me.materials) - 1
        obs.append(ob)
    return obs


def outline_guard(slack=0.5):
    """"Even offset" der Kontur teilt den Versatz durch den Winkel-Kosinus und schoss an einer konkaven Fasen-Ecke
    (Polus-Weapons-Pult) bis (620|-786) hinaus; der Nightfall-Export unterteilte die 977-m-Dreiecke dann bis zu seiner
    400000er-Sicherung (20.10.). Ragt eine Kontur ueber den Rahmen ihres Objekts hinaus, fuer dieses Objekt aus."""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.data.objects:
        mod = ob.modifiers.get("Kontur") if ob.type == "MESH" else None
        if mod is None or not mod.use_even_offset or not ob.data.vertices:
            continue
        co = [v.co for v in ob.data.vertices]
        lo = [min(c[i] for c in co) - slack for i in range(3)]
        hi = [max(c[i] for c in co) + slack for i in range(3)]
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        bad = any(not (lo[i] <= v.co[i] <= hi[i]) for v in me.vertices for i in range(3))
        ev.to_mesh_clear()
        if bad:
            mod.use_even_offset = False
            print(f"[outline] {ob.name}: Kontur ragte ueber den Rahmen, even offset aus")


def _build_parts(m, mats, shear=0.0):
    import bmesh
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    names = []

    def mi(n):
        if n not in names:
            names.append(n)
        return names.index(n)

    def V(x, y, z):
        return bm.verts.new((x, y + shear * z, z))

    for p in m["parts"]:
        if p["type"] == "prism":
            pts = p["pts"]
            area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
            if area < 0:
                pts = pts[::-1]
            z0, z1 = p["z0"], p["z1"]
            bot = [V(x, y, z0) for x, y in pts]
            top = [V(x, y, z1) for x, y in pts]
            ft = bm.faces.new(top)
            fb = bm.faces.new(bot[::-1])
            tm = p.get("top", p["mat"])
            ft.material_index = mi(tm)
            fb.material_index = mi(p["mat"])
            tspec = DOC["materials"][tm]
            xs, ys = [q[0] for q in pts], [q[1] for q in pts]
            bb = (min(xs), min(ys), max(xs), max(ys))
            for lp in ft.loops:
                x, y = lp.vert.co.x, lp.vert.co.y - shear * z1
                if tspec.get("uv") == "part":
                    lp[uvl].uv = ((x - bb[0]) / max(1e-6, bb[2] - bb[0]), (y - bb[1]) / max(1e-6, bb[3] - bb[1]))
                else:
                    lp[uvl].uv = tri_uv(tspec, x, y)
            per = 0.0
            sides = []
            for i in range(len(pts)):
                j = (i + 1) % len(pts)
                f = bm.faces.new((bot[i], bot[j], top[j], top[i]))
                L = ((pts[j][0] - pts[i][0]) ** 2 + (pts[j][1] - pts[i][1]) ** 2) ** 0.5
                dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
                south = L > 1e-6 and (dx / L) > 0.7                  # CCW-Umlauf: Kante nach Osten = Suedseite
                north = L > 1e-6 and (dx / L) < -0.7
                east = L > 1e-6 and (dy / L) > 0.7
                west = L > 1e-6 and (dy / L) < -0.7
                # Eigenes Bild je Seite (Ich-Sicht: Bildschirme zur Raummitte), u von links nach rechts fuer den
                # Betrachter vor der Seite
                fx = (north and p.get("face_n")) or (east and p.get("face_e")) or (west and p.get("face_w"))
                if fx:
                    f.material_index = mi(fx)
                    if north:
                        ua, ub = [(bb[2] - pts[q][0]) / max(1e-6, bb[2] - bb[0]) for q in (i, j)]
                    elif east:
                        ua, ub = [(pts[q][1] - bb[1]) / max(1e-6, bb[3] - bb[1]) for q in (i, j)]
                    else:
                        ua, ub = [(bb[3] - pts[q][1]) / max(1e-6, bb[3] - bb[1]) for q in (i, j)]
                    uvs4 = [(ua, 0.0), (ub, 0.0), (ub, 1.0), (ua, 1.0)]
                elif north and p.get("front") and p.get("front_both"):  # Zaun: Rueckseite zeigt dieselbe Zeichnung
                    f.material_index = mi(p["front"])
                    uvs4 = [((pts[i][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 0.0), ((pts[j][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 0.0),
                            ((pts[j][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 1.0), ((pts[i][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 1.0)]
                elif south and p.get("front"):
                    f.material_index = mi(p["front"])
                    uvs4 = [((pts[i][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 0.0), ((pts[j][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 0.0),
                            ((pts[j][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 1.0), ((pts[i][0] - bb[0]) / max(1e-6, bb[2] - bb[0]), 1.0)]
                elif p.get("side_uv") == "face":                       # Textur je Seitenflaeche (Kistenseite)
                    f.material_index = mi(p["mat"])
                    uvs4 = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
                else:
                    f.material_index = mi(p["mat"])
                    uvs4 = ((per, z0), (per + L, z0), (per + L, z1), (per, z1))
                for lp, uv in zip(f.loops, uvs4):
                    lp[uvl].uv = uv
                per += L
                sides.append(f)
            if p.get("bevel", 0) > 0:
                edges = [e for e in ft.edges]
                bmesh.ops.bevel(bm, geom=edges, offset=p["bevel"], segments=2, affect="EDGES", clamp_overlap=True)
        elif p["type"] == "mesh":
            vs = [V(*q) for q in p["verts"]]
            for fi, fc in enumerate(p["faces"]):
                try:
                    f = bm.faces.new([vs[i] for i in fc])
                except ValueError:                                   # doppelte Flaeche
                    continue
                f.material_index = mi(p["mats"][fi] if p.get("mats") else p["mat"])
                if p.get("uvs"):                                     # UV je Ecke (Scheiben mit Bild)
                    for lp, uv in zip(f.loops, p["uvs"][fi]):
                        lp[uvl].uv = uv
        elif p["type"] == "tube":
            import math
            from mathutils import Vector
            pts = [Vector(q) for q in p["pts"]]
            r, seg = p["r"], p["seg"]
            # Ringe an jedem Punkt, senkrecht zur gemittelten Laufrichtung
            rings = []
            for i, c in enumerate(pts):
                d0 = (c - pts[i - 1]) if i > 0 else (pts[1] - c)
                d1 = (pts[i + 1] - c) if i + 1 < len(pts) else (c - pts[i - 1])
                t = (d0.normalized() + d1.normalized())
                t = t.normalized() if t.length > 1e-6 else d1.normalized()
                up = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
                a_ = t.cross(up).normalized()
                b_ = t.cross(a_).normalized()
                rings.append([V(c.x + r * (math.cos(2 * math.pi * k / seg) * a_.x + math.sin(2 * math.pi * k / seg) * b_.x),
                                c.y + r * (math.cos(2 * math.pi * k / seg) * a_.y + math.sin(2 * math.pi * k / seg) * b_.y),
                                c.z + r * (math.cos(2 * math.pi * k / seg) * a_.z + math.sin(2 * math.pi * k / seg) * b_.z))
                              for k in range(seg)])
            for ra, rb in zip(rings, rings[1:]):
                for k in range(seg):
                    f = bm.faces.new((ra[k], ra[(k + 1) % seg], rb[(k + 1) % seg], rb[k]))
                    f.material_index = mi(p["mat"])
            for ring_, rev in ((rings[0], True), (rings[-1], False)):
                f = bm.faces.new(ring_[::-1] if rev else ring_)
                f.material_index = mi(p["mat"])
        elif p["type"] == "lathe":
            import math
            cx, cy = p["c"]
            prof, seg = p["prof"], p["seg"]
            tilt = p.get("tilt")

            def LV(x, y, z):
                if tilt:                                                   # Neigung um eine waagrechte Achse
                    ang, dirn, pz = math.radians(tilt[0]), math.radians(tilt[1]), tilt[2]
                    ax, ay = -math.sin(dirn), math.cos(dirn)               # Achse senkrecht zur Neigerichtung
                    from mathutils import Matrix, Vector
                    v = Vector((x - cx, y - cy, z - pz))
                    v = Matrix.Rotation(ang, 3, Vector((ax, ay, 0.0))) @ v
                    x, y, z = v.x + cx, v.y + cy, v.z + pz
                return V(x, y, z)
            rings = []
            for r, z in prof:
                if r <= 1e-6:
                    rings.append([LV(cx, cy, z)])
                else:
                    rings.append([LV(cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg), z) for i in range(seg)])
            for a, b in zip(rings, rings[1:]):
                if len(a) == 1 and len(b) == 1:
                    continue
                for i in range(seg):
                    j = (i + 1) % seg
                    if len(a) == 1:
                        f = bm.faces.new((a[0], b[i], b[j]))
                    elif len(b) == 1:
                        f = bm.faces.new((a[i], b[0], a[j]) if False else (a[j], a[i], b[0]))
                    else:
                        f = bm.faces.new((a[i], a[j], b[j], b[i]))
                    f.material_index = mi(p["mat"])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(m["name"])
    bm.to_mesh(me)
    bm.free()
    for n in names:
        me.materials.append(mats[n])
    return bpy.data.objects.new(m["name"], me)


def build_mesh(m, mats, shear=0.0, zoff=None):
    spec = DOC["materials"][m["mat"]]
    verts, faces, uvs = [], [], []
    if "verts" in m:                                                         # Hoehenfeld (Gelaende)
        vs = m["verts"]
        for f in m["faces"]:
            i = len(verts)
            for q in f:
                x, y, z = vs[q]
                verts.append((x, y, z))
                uvs.append(tri_uv(spec, x, y))
            faces.append(tuple(range(i, i + len(f))))
    elif "strips" in m:
        z = m["z"] if zoff is None else zoff
        for st in m["strips"]:
            i = len(verts)
            a, b, bo, ao = st["pts"]
            for (x, y), t in zip((a, b, bo, ao), ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))):
                verts.append((x, y + shear * z, z))
                uvs.append(t)
            # Flaeche nach oben: a->b->bo->ao ist je nach Umlauf links- oder rechtsherum
            (x0, y0), (x1, y1), (x2, y2) = a, b, bo
            if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0:
                faces.append((i, i + 3, i + 2, i + 1))
            else:
                faces.append((i, i + 1, i + 2, i + 3))
    elif "tris" in m:
        z = m["z"] if zoff is None else zoff
        for t in m["tris"]:
            i = len(verts)
            for (x, y) in t:
                verts.append((x, y + shear * z, z))
                uvs.append(tri_uv(spec, x, y))
            faces.append((i, i + 1, i + 2))
    else:
        h = m["h"]
        zb = m.get("z0", 0.0)
        for q in m["quads"]:
            (ax, ay), (bx, by) = q["a"], q["b"]
            nx, ny = q.get("n", (0, 0))
            rx, ry = (by - ay), -(bx - ax)                                  # rechte Seite von a->b
            u0, v0, u1, v1 = q["uv"]
            if spec.get("uv") != "quad":
                L = math.hypot(bx - ax, by - ay)
                s = spec.get("scale", 1.0)
                su, sv = (s, s) if not isinstance(s, (list, tuple)) else s
                u0, u1, v0, v1 = 0.0, L / su, zb / sv, h / sv
            pa = [(ax, ay, zb), (bx, by, zb), (bx, by, h), (ax, ay, h)]
            uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            if rx * nx + ry * ny < 0:                                        # Normale muss in den Raum zeigen
                pa = [pa[1], pa[0], pa[3], pa[2]]
                uv = [uv[1], uv[0], uv[3], uv[2]]
            i = len(verts)
            for (x, y, z), t in zip(pa, uv):
                verts.append((x, y + shear * z, z))
                uvs.append(t)
            faces.append((i, i + 1, i + 2, i + 3))
    me = bpy.data.meshes.new(m["name"])
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    me.materials.append(mats[m["mat"]])
    me.validate()
    if "tris" in m or "verts" in m:                                          # Dreiecke teilen ihre Ecken
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.to_mesh(me)
        bm.free()
    ob = bpy.data.objects.new(m["name"], me)
    return ob


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def setup_render(scene):
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.dither_intensity = 0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "TEXTURE"
    sh.show_cavity = False
    sh.show_shadows = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    sh.show_backface_culling = True
    scene.display.render_aa = "OFF"
    w = scene.world or bpy.data.worlds.new("W")
    scene.world = w
    w.color = [srgb2lin(v) for v in (41, 23, 56)]


LAMP_W, LAMP_D = 0.62, 0.26          # Deckenleuchte (Leuchtstoffpanel)
LAMP_POWER = float(os.environ.get("BM_LAMP_W", "28"))
WORLD_STRENGTH = float(os.environ.get("BM_WORLD", "0.55"))


def build_lighting(scene, root):
    """Leuchten (Panel mit Emission + Flaechenlicht nach unten), Himmelsfarbe als Umgebungslicht, Mondlicht draussen."""
    coll = collection("Lights", root)
    lights = DOC.get("lights") or []
    if lights:
        m = bpy.data.materials.new("lamp_panel")
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        outn = nt.nodes.new("ShaderNodeOutputMaterial")
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (1.0, 0.96, 0.88, 1.0)
        em.inputs["Strength"].default_value = 6.0
        nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
        m.diffuse_color = (1.0, 0.96, 0.88, 1.0)
        verts, faces = [], []
        zl = DOC.get("zlift_rooms", {})
        for L in lights:
            x, y, z = L["pos"]
            z -= 0.004
            i = len(verts)
            verts += [(x - LAMP_W / 2, y - LAMP_D / 2, z), (x - LAMP_W / 2, y + LAMP_D / 2, z),
                      (x + LAMP_W / 2, y + LAMP_D / 2, z), (x + LAMP_W / 2, y - LAMP_D / 2, z)]
            faces.append((i, i + 1, i + 2, i + 3))                       # Normale nach unten
            ld = bpy.data.lights.new("lamp", "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = LAMP_W, LAMP_D
            ld.energy = LAMP_POWER
            ld.color = (1.0, 0.95, 0.86)
            try:
                ld.use_soft_falloff = True
            except Exception:
                pass
            lo = bpy.data.objects.new("lamp", ld)
            lo.location = (x, y, z - 0.01)
            coll.objects.link(lo)
        me = bpy.data.meshes.new("lamp_panels")
        me.from_pydata(verts, [], faces)
        me.materials.append(m)
        ob = bpy.data.objects.new("lamp_panels", me)
        coll.objects.link(ob)
    w = scene.world or bpy.data.worlds.new("W")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    col = [srgb2lin(v) for v in DOC.get("world", (41, 23, 56))] + [1.0]
    amb = [srgb2lin(v) for v in DOC.get("ambient", (176, 180, 190))] + [1.0]
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    outn = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    bg_cam = nt.nodes.new("ShaderNodeBackground")                    # was die Kamera sieht: Weltraum/Himmel
    bg_cam.inputs["Color"].default_value = col
    bg_cam.inputs["Strength"].default_value = 1.0
    bg_amb = nt.nodes.new("ShaderNodeBackground")                    # Umgebungslicht: neutral, gedaempft
    bg_amb.inputs["Color"].default_value = amb
    bg_amb.inputs["Strength"].default_value = WORLD_STRENGTH
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_amb.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], outn.inputs["Surface"])
    w.color = col[:3]
    sun = DOC.get("sun")
    if sun:
        sd = bpy.data.lights.new("Mond", "SUN")
        sd.energy = sun.get("strength", 1.6)
        sd.color = [v / 255 for v in sun.get("color", (190, 200, 255))]
        sd.angle = math.radians(3)
        so = bpy.data.objects.new("Mond", sd)
        rx, ry, rz = sun.get("rot", (52, 0, 35))
        so.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
        coll.objects.link(so)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    mats = {n: make_material(n, s) for n, s in DOC["materials"].items()}
    root = collection(DOC["map"])
    if MODE == "model":
        for m in DOC["meshes"]:
            if m["kind"] == "ground":
                continue
            obs = build_parts(m, mats) if m["kind"] == "parts" else [build_mesh(m, mats)]
            for ob in obs:
                ob.location.z += m.get("zlift", 0.0)                       # Raum auf eigener Ebene
                collection(m["coll"], root).objects.link(ob)
        build_lighting(scene, root)
        outline_guard()
        blend = os.path.join(OUT, DOC["map"] + ".blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        print("BM saved", blend)
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, DOC["map"] + ".glb"), export_format="GLB",
                                  export_apply=True)
        print("BM glb", os.path.join(OUT, DOC["map"] + ".glb"))
        return
    # ---- Vergleich
    for m in DOC["meshes"]:
        if m["kind"] in ("floor", "terrain"):
            ob = build_mesh(m, mats)
        elif m["kind"] == "wall_north":
            ob = build_mesh(m, mats, shear=K)
        elif m["kind"] == "ground":
            ob = build_mesh(m, mats, zoff=-0.002)
        elif m["kind"] == "rim_north":
            ob = build_mesh(m, mats, shear=K, zoff=DOC["H"])
        elif m["kind"] == "rim_side":
            ob = build_mesh(m, mats, zoff=0.001)
        elif m["kind"] == "parts":
            for ob in build_parts(m, mats, shear=K):
                collection(m["coll"], root).objects.link(ob)
            continue
        else:
            continue
        collection(m["coll"], root).objects.link(ob)
    setup_render(scene)
    cam = bpy.data.cameras.new("Cmp")
    cam.type = "ORTHO"
    co = bpy.data.objects.new("Cmp", cam)
    scene.collection.objects.link(co)
    scene.camera = co
    ppu = DOC["ppu"]
    os.makedirs(os.path.join(OUT, "cmp"), exist_ok=True)
    for name, r in sorted(DOC["rooms"].items()):
        if ONLY and name not in ONLY:
            continue
        x0, y0, x1, y1 = r["bbox"]
        x0 -= 0.5; y0 -= 0.5; x1 += 0.5; y1 += 0.5 + K * DOC["H"]
        w, h = x1 - x0, y1 - y0
        scene.render.resolution_x = max(4, round(w * ppu))
        scene.render.resolution_y = max(4, round(h * ppu))
        cam.ortho_scale = max(w, h)
        co.location = ((x0 + x1) / 2, (y0 + y1) / 2, 50.0)
        cam.clip_end = 100
        scene.render.filepath = os.path.join(OUT, "cmp", f"{name}_bl.png")
        bpy.ops.render.render(write_still=True)
        with open(os.path.join(OUT, "cmp", f"{name}_bl.json"), "w") as f:
            json.dump({"bbox": [x0, y0, x1, y1]}, f)
        print("BM cmp", name, scene.render.resolution_x, scene.render.resolution_y)


main()
