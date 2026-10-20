# shots.py <karte> <out.jpg> name:x,y,z,yaw,pitch[,fov] ... : gezielte Ansichten mit Licht (EEVEE) als Kontaktbogen.
#   yaw 90 = nach Norden, 0 = Osten; pitch negativ = nach unten. Optional BM_WB=1 fuer Workbench (schneller).
import json, os, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw
from bm_ref import ROOT

key, out = sys.argv[1], sys.argv[2]
views = []
for a in sys.argv[3:]:
    nm, rest = a.split(":")
    v = [float(t) for t in rest.split(",")]
    views.append({"name": nm, "pos": v[:3], "yaw": v[3], "pitch": v[4], "fov": v[5] if len(v) > 5 else 90,
                  "res": [960, 600]})
tmp = Path(tempfile.mkdtemp())
(tmp / "v.json").write_text(json.dumps(views))
B = r"C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe"
wb = bool(os.environ.get("BM_WB"))
subprocess.run([B, "-b", str(ROOT / "out" / key / f"{key}.blend"), "-P",
                str(ROOT / "blender" / ("bm_views.py" if wb else "bm_eevee.py")), "--", str(tmp / "v.json"), str(tmp)]
               + ([] if wb else ["24"]), capture_output=True)
TW, TH = 640, 400
ims = []
for v in views:
    f = tmp / f"{v['name']}.png"
    if f.exists():
        im = Image.open(f).convert("RGB").resize((TW, TH))
        ImageDraw.Draw(im).text((4, 4), v["name"], fill=(255, 255, 0))
        ims.append(im)
cols = 2 if len(ims) > 1 else 1
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * TW, max(1, rows) * TH))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * TW, (i // cols) * TH))
sheet.save(out, quality=88)
print(len(ims), "Ansichten")
