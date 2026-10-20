# report_views.py <reports-ordner> <karte> <ausgabeordner> [nummern]: das Modell aus der Kamera jeder Nightfall-Meldung
# rendern (blender/bm_views.py, Workbench) und neben den Spiel-Screenshot stellen: links Spiel (Stand der Meldung),
# rechts Modell jetzt. Blaetter mit je 4 Paaren, 960 x 540 je Bild.
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BLENDER = r"C:\Users\moritz\AppData\Local\Programs\Blender Foundation\blender-5.2.2-windows-x64\blender.exe"
src, key, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
only = {int(n) for n in sys.argv[4].split(",")} if len(sys.argv) > 4 else None
out.mkdir(parents=True, exist_ok=True)
reps = [(f, json.loads(f.read_text(encoding="utf-8"))) for f in sorted(src.glob("*.json"))]
reps = [(i, f, d) for i, (f, d) in enumerate(reps) if d.get("map") == key and d.get("eyeZ") is not None]
if only:
    reps = [r for r in reps if r[0] in only]
W, H = 960, 540
views = [{"name": f"r{i:03d}", "pos": [d["position"]["x"], d["position"]["y"], max(d["eyeZ"], (d.get("ground") or 0) + 0.62)],
          "yaw": d["headingDeg"], "pitch": d["pitchDeg"], "fov": d["fovHorizontalDeg"], "res": [W, H]} for i, f, d in reps]
with tempfile.TemporaryDirectory() as td:
    vj = Path(td) / "views.json"
    vj.write_text(json.dumps(views), encoding="utf-8")
    subprocess.run([BLENDER, "-b", str(ROOT / "out" / key / f"{key}.blend"), "-P", str(ROOT / "blender" / "bm_views.py"),
                    "--", str(vj), td], check=True, capture_output=True)
    font = ImageFont.truetype("arial.ttf", 24)
    pairs = []
    for (i, f, d), v in zip(reps, views):
        g = Image.open(f.with_suffix(".png")).convert("RGB").resize((W, H), Image.LANCZOS)
        b = Image.open(Path(td) / (v["name"] + ".png")).convert("RGB")
        row = Image.new("RGB", (2 * W, H))
        row.paste(g, (0, 0))
        row.paste(b, (W, 0))
        dr = ImageDraw.Draw(row)
        dr.rectangle((0, H - 32, 520, H), fill=(0, 0, 0))
        dr.text((6, H - 30), f"#{i} {d['room']} h{d['headingDeg']:.0f} p{d['pitchDeg']:.0f}", fill=(255, 255, 0), font=font)
        pairs.append(row)
    for s in range(0, len(pairs), 4):
        chunk = pairs[s:s + 4]
        sheet = Image.new("RGB", (2 * W, H * len(chunk)))
        for k, r in enumerate(chunk):
            sheet.paste(r, (0, k * H))
        sheet.save(out / f"views_{s // 4:02d}.jpg", quality=82)
print("report_views", key, len(pairs))
