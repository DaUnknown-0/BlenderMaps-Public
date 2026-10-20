# bm_views.py - laeuft IN Blender: viele Perspektivansichten eines Modells in einem Lauf.
#   blender -b <karte>.blend -P blender/bm_views.py -- <views.json> <outdir>
#   views.json: [{"name": .., "pos": [x, y, z], "yaw": grad, "pitch": grad, "fov": grad}]
import bpy, json, math, os, sys
a = sys.argv[sys.argv.index("--") + 1:]
views = json.load(open(a[0]))
out = a[1]
sc = bpy.context.scene
cam = bpy.data.cameras.new("V"); cam.lens_unit = "FOV"; cam.clip_start = 0.02
co = bpy.data.objects.new("V", cam); sc.collection.objects.link(co); sc.camera = co
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sh.show_cavity = True; sh.show_shadows = False; sh.show_backface_culling = True
sc.display.render_aa = "8"
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 640, 360
for v in views:
    sc.render.resolution_x, sc.render.resolution_y = v.get("res", [640, 360])
    cam.angle = math.radians(v.get("fov", 90))
    co.location = tuple(v["pos"])
    co.rotation_euler = (math.radians(90 + v.get("pitch", 0)), 0, math.radians(v.get("yaw", 90) - 90))
    sc.render.filepath = os.path.join(out, v["name"] + ".png")
    bpy.ops.render.render(write_still=True)
print("BM views", len(views))
