# bm_view.py - laeuft IN Blender: Perspektivansicht eines gebauten Modells.
#   blender -b <karte>.blend -P blender/bm_view.py -- <out.png> x y z yaw_grad pitch_grad [fov_grad] [--nodeckel]
import bpy, math, sys
a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]; x, y, z, yaw, pitch = map(float, a[1:6]); fov = float(a[6]) if len(a) > 6 and not a[6].startswith("--") else 80
sc = bpy.context.scene
if "--nodeckel" in a:
    for ob in sc.objects:
        if ob.name.startswith(("ceiling_", "cap")):
            ob.hide_render = True
cam = bpy.data.cameras.new("V"); cam.lens_unit = "FOV"; cam.angle = math.radians(fov); cam.clip_start = 0.02
co = bpy.data.objects.new("V", cam); sc.collection.objects.link(co); sc.camera = co
co.location = (x, y, z)
co.rotation_euler = (math.radians(90 + pitch), 0, math.radians(yaw - 90))
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"; sh.color_type = "TEXTURE"; sh.show_cavity = True; sh.show_shadows = False; sh.show_backface_culling = True
sc.display.render_aa = "8"
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("BM view", out)
