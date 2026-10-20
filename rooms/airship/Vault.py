# Airship / Vault - am Kartenfoto gemessen.
#
# Runder Raum, Boden blau (77,124,170), Wand mit Bildern (Zeichnung). Vier Ausstellungspodeste aus Holz (198,162,123)/
#   (181,134,107) = die Wand-Collider-Inseln im Raum, 0,2 hoch. Goldhaufen (255,203,44)/(236,163,41) (Sprite
#   vault_goldtop), Rubin (209,79,104) auf weissem Sockel (185,213,224) in der Mitte (RubyTask), drei Puppen mit Hut/
#   Jacke (vault_dummie 1-3), Schwert und Pistole auf Staendern (vault_sword, vault_gun) als Koerper (3D, 19.10.).

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, blob, box, crewmate_statue, cyl, lathe, prism, sprite, vent   # noqa: E402
from bm_models import weapon_stand                                                # noqa: E402

Z_P = 0.2


def podiums(ctx):
    room = ctx.scene.rooms["Vault"].buffer(0.3)
    return [h for h in ctx.scene.props_fp if room.contains(h.representative_point()) and h.area > 1.5]


def props(ctx):
    parts = []
    wood = ctx.color("vault_wood", (198, 162, 123))
    woodd = ctx.color("vault_wood_dark", (181, 134, 107))
    for h in podiums(ctx):
        parts.append(prism(h.buffer(-0.02).simplify(0.01), 0.0, Z_P, woodd, top=wood, outline=(55, 72, 137)))
    gold = (ctx.color("vault_gold", (255, 203, 44)), ctx.color("vault_gold_dark", (236, 163, 41)))
    for i, (cx, cy, rx, ry, rz) in enumerate(((-11.0, 10.2, 0.75, 0.9, 0.55), (-10.4, 9.7, 0.6, 0.6, 0.4),
                                               (-11.5, 10.9, 0.45, 0.5, 0.35))):
        parts.append(blob(cx, cy, Z_P, rx, ry, rz, gold, seed=70 + i, outline=(150, 90, 20)))
    # Rubin
    ped = ctx.color("vault_pedestal", (185, 213, 224))
    ruby = ctx.glow("vault_ruby", (209, 79, 104), 1.2)
    parts.append(cyl(-8.85, 8.9, 0.32, 0.0, 0.12, ped, seg=32, outline=(60, 70, 90)))
    parts.append(cyl(-8.85, 8.9, 0.12, 0.12, 0.55, ped, seg=16, outline=(60, 70, 90)))
    parts.append(lathe(-8.85, 8.9, [(0.0, 0.55), (0.14, 0.62), (0.16, 0.75), (0.08, 1.0), (0.0, 1.05)], ruby, seg=6,
                       outline=(90, 20, 40)))
    # Puppen
    mats = (ctx.color("vault_dummy", (226, 222, 212)), ctx.color("vault_dummy_mid", (180, 176, 166)),
            ctx.color("vault_dummy_dark", (120, 116, 108)))
    hats = {"(1)": (230, 190, 60), "(2)": (110, 60, 150), "(3)": (40, 40, 60)}
    for p in ctx.ref.world["props"]:
        import re
        mt = re.search(r"vault_dummie (\(\d\))$", p["path"])
        if mt:
            (x0, y0), (x1, y1) = p["min"], p["max"]
            cx, cy = (x0 + x1) / 2, y0 + 0.15
            parts += [dict(q) for q in crewmate_statue(cx, cy, mats, h=0.62, r=0.2, facing=270.0, outline=(60, 60, 60))]
            for q in parts[-5:]:
                for k_ in ("z0", "z1"):
                    if k_ in q:
                        q[k_] += Z_P
                if "prof" in q:
                    q["prof"] = [[a, b + Z_P] for a, b in q["prof"]]
            tag = mt.group(1)
            parts.append(box(cx, cy, 0.3, 0.3, Z_P + 0.62, Z_P + 0.74, ctx.color("vault_hat_" + tag.strip("()"), hats.get(tag, (90, 90, 90))),
                             bevel=0.03, outline=(30, 30, 30)))
    # Schwert und Pistole auf Staendern (auf dem Podest)
    for suf, kind in (("Vault/vault_sword", "sword"), ("Vault/vault_gun", "gun")):
        _, (x0, y0, x1, y1) = sprite(ctx, suf)
        parts += weapon_stand(ctx, "vault_" + kind, (x0 + x1) / 2, y0 + 0.16, kind=kind, z0=Z_P)
    parts += vent(ctx, "Vault/VaultVent")
    return parts
