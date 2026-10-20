# bm_eevee.py - laeuft IN Blender: Ansichten eines gebauten Modells mit echtem Licht (EEVEE).
#   blender -b <karte>.blend -P blender/bm_eevee.py -- <views.json> <outdir> [samples]
#   views.json wie bm_views.py: [{"name", "pos": [x, y, z], "yaw", "pitch", "fov", "res": [w, h]}]
# Das Modell bringt Lampen, Deckenleuchten und Himmel selbst mit (bm_build.py, "lights"/"world" in scene.json).
import bpy, json, math, os, sys
a = sys.argv[sys.argv.index("--") + 1:]
views = json.load(open(a[0]))
out = a[1]
samples = int(a[2]) if len(a) > 2 else 32
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
ee = sc.eevee
for attr, val in (("taa_render_samples", samples), ("use_shadows", True), ("use_raytracing", True),
                  ("ray_tracing_method", "SCREEN"), ("fast_gi_method", "GLOBAL_ILLUMINATION"),
                  ("use_fast_gi", True), ("fast_gi_distance", 3.0), ("shadow_ray_count", 2), ("shadow_step_count", 8)):
    try:
        setattr(ee, attr, val)
    except Exception:
        pass
try:
    ee.ray_tracing_options.use_denoise = True
    ee.ray_tracing_options.resolution_scale = "2"
except Exception:
    pass
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.view_settings.exposure = float(os.environ.get("BM_EXPOSURE", "0"))
sc.render.film_transparent = False
cam = bpy.data.cameras.new("V"); cam.lens_unit = "FOV"; cam.clip_start = 0.02; cam.clip_end = 400
co = bpy.data.objects.new("V", cam); sc.collection.objects.link(co); sc.camera = co
for v in views:
    sc.render.resolution_x, sc.render.resolution_y = v.get("res", [960, 540])
    cam.angle = math.radians(v.get("fov", 90))
    co.location = tuple(v["pos"])
    co.rotation_euler = (math.radians(90 + v.get("pitch", 0)), 0, math.radians(v.get("yaw", 90) - 90))
    sc.render.filepath = os.path.join(out, v["name"] + ".png")
    bpy.ops.render.render(write_still=True)
print("BM eevee", len(views))
