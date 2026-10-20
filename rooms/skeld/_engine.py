# Skeld / Triebwerk (Upper Engine = LeftEngine, Lower Engine = RightEngine sind dieselbe Maschine, Versatz dy).
# Liegender Zylinder (153,102,93): Bildhoehe 1,63 = 2*r*sqrt(1+k^2) -> r 0,70, Achse auf 0,85, Achse von x -19,0 bis
# -16,3; Kuehlrippen obenauf (Zeichnung), leuchtender Ring am Ostende (214,250,250), Steuereinheit (71,96,93) im
# Westen (Geraetekonsole mit Anzeigen, 3D 19.10.), orange Gelaender (198,162,74) vorn und an der Ostseite, Abgasbogen (74,56,57) von der Wand.

from shapely.geometry import box as sbox

from bm_spec import art_block, railing, tube
from bm_models import console_block


def engine(ctx, tag, dy):
    k = ctx.k
    body = ctx.color("eng_body", (153, 102, 93))
    dark = ctx.color("eng_dark", (74, 56, 57))
    glow = ctx.glow("eng_ring", (214, 250, 250), 3.0)
    rail = ctx.color("eng_rail", (198, 162, 74))
    zc, r, yc = 0.85, 0.70, 0.73 + dy
    parts = [tube([(-19.0, yc, zc), (-16.35, yc, zc)], r, body, seg=36, outline=(40, 26, 26)),
             tube([(-16.35, yc, zc), (-16.18, yc, zc)], r + 0.06, glow, seg=36),
             tube([(-16.18, yc, zc), (-16.05, yc, zc)], r * 0.75, dark, seg=36)]
    for x in (-18.7, -17.0):                                          # Stuetzen
        parts.append(art_block(ctx, f"eng_foot{tag}{int(x)}", sbox(x - 0.18, yc - 0.45 + k * 0.2, x + 0.18, yc + 0.45 + k * 0.2),
                               0.0, 0.2, (74, 56, 57), tex=False, outline=(40, 26, 26)))
    parts.append(art_block(ctx, f"eng_fins{tag}", sbox(-18.75, 1.10 + dy, -17.60, 1.95 + dy), zc + r - 0.08, zc + r + 0.05,
                           (120, 112, 104), outline=(40, 26, 26)))
    # Steuereinheit auf ihrem Collider (ShortObjects -19,70..-18,64 / -0,95..0,12): der Zeichnungsblock lag 0,5 weiter
    # suedlich im Laufbereich, man stand mit der Kamera an seiner Seite (Meldungen 18.10.)
    # Anzeigen nach Osten: dort steht der Spieler (zwischen Gelaender und Triebwerk), die Suedseite liegt am Rand
    parts += console_block(ctx, f"eng_ctrl{tag}", -19.70, -0.95 + dy, -18.64, 0.12 + dy, 0.90, rgb=(71, 96, 93), screens=2,
                           facing="E", seed=3 if tag else 4)
    # Zapfsaeule (FuelEngineConsole) auf ihrem Collider -18,60..-18,08 / -0,68..-0,08, Front nach Sueden
    from bm_models import gas_pump
    parts += gas_pump(ctx, f"eng_fuel{tag}", -18.58, -0.66 + dy, -18.10, -0.10 + dy, h=0.95, rgb=(110, 120, 125))
    parts.append(tube([(-19.35, 2.75 + dy, 1.25), (-19.25, 2.0 + dy, 1.15), (-19.05, 1.45 + dy, 0.95)], 0.28, dark, seg=20,
                      outline=(40, 26, 26)))
    zr = 0.5
    parts += railing([(-18.38, -0.05 + dy - k * zr), (-15.80, -0.05 + dy - k * zr)], zr, rail, outline=(75, 50, 30))
    parts += railing([(-15.85, 0.12 + dy - k * zr), (-15.85, 1.90 + dy - k * zr)], zr, rail, outline=(75, 50, 30))
    return parts
