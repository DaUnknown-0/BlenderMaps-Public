# Mira HQ / Decontamination (Laufband-Korridor, keine Einrichtung).
PROCEDURAL = True      # zeichnet Boden/Waende selbst (keine Spieltextur), bleibt bei bm_style aktiv
# Glasseiten (Meldung 18.10. #86: einfarbige graue Wand neben dem Laufband): halbdurchsichtige blaue Scheibe mit Rahmen.


def side(ctx):
    from PIL import Image, ImageDraw
    # Glas (19.10., "Glas nicht erkennbar"): fast durchsichtig, Rahmen und zwei Lichtstreifen statt milchiger Scheibe
    im = Image.new("RGBA", (128, 128), (190, 220, 245, 40))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 127, 127], outline=(60, 70, 84, 240), width=5)
    d.line([(64, 0), (64, 127)], fill=(60, 70, 84, 220), width=3)
    d.line([(0, 110), (127, 110)], fill=(60, 70, 84, 240), width=6)
    d.line([(10, 100), (60, 10)], fill=(240, 250, 255, 110), width=4)
    d.line([(26, 100), (76, 10)], fill=(240, 250, 255, 70), width=2)
    t = ctx.tex("dc_glass", im, uv="world", scale=ctx.H)
    ctx.scene.mats[t]["alpha"] = True
    return t
