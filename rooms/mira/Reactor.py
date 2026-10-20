# Mira HQ / Reactor - am Kartenfoto gemessen (k 0,53).
# Kern: leuchtende Kugel r 0,62 in drei Greifarmen; davor das Energiepult (Schraege mit Schirm, Tastatur); an der West-
# und Ostwand Stufenpulte (Reactor-Borders) mit Anzeigen; Elektro-Pult; Raum 2,4 hoch; Vent als Gitter.

import math

from shapely.geometry import box as sbox

from bm_models import console_block, floor_console, stepped_desk, vent_grate
from bm_spec import art_floor, lathe, sprite, tube

H = 2.4
K = 0.53


def floor(ctx):
    return art_floor(ctx, "floor_Reactor", [sbox(1.5, 11.7, 3.5, 13.3), sbox(0.05, 11.05, 1.1, 13.55)])


def props(ctx):
    p = []
    glow = ctx.glow("mrea_core", (255, 238, 170), 4.0)
    claw = ctx.color("mrea_claw", (70, 76, 90))
    cx, cy, zc, r = 2.47, 13.55, 1.05, 0.62
    prof = [(0.0, zc - r)] + [(r * math.sin(a / 14 * math.pi), zc - r * math.cos(a / 14 * math.pi)) for a in range(1, 14)] + [(0.0, zc + r)]
    p.append(lathe(cx, cy, prof, glow, seg=36))
    for dx in (-0.85, 0.0, 0.85):
        p.append(tube([(cx + dx * 1.1, cy + 0.6, 2.2), (cx + dx, cy + 0.2, 1.75), (cx + dx * 0.75, cy - 0.15, 1.2)], 0.09, claw, seg=10,
                      outline=(20, 22, 30)))
    p += floor_console(ctx, "mrea_panel", 2.485, 12.25, 1.9, 1.0, (12.20 - 11.75) / K, body_rgb=(90, 96, 112), screen_rgb=(255, 200, 120))
    # Westwand: Stufenpulte (Reactor-Borders, Stufe nach Osten), Elektro-Pult; Ostwand: drei Stufenpulte nach Westen
    for i, ya in enumerate((13.25, 12.39, 11.39, 9.87)):
        # Randpulte liegen im Laufweg (kein Collider, Meldung 19.10.): unter Augenhoehe halten
        p += stepped_desk(ctx, f"mrea_border_w{i}", 0.08, ya - K * 1.0, 0.71, ya - K * 1.0 + 0.74, h_front=0.28, h_back=0.55, facing="E",
                          rgb=(90, 96, 112))
    for i, ya in enumerate((13.34, 12.51, 11.47)):
        p += stepped_desk(ctx, f"mrea_border_e{i}", 4.25, ya - K * 1.0, 4.88, ya - K * 1.0 + 0.64, h_front=0.28, h_back=0.55, facing="W",
                          rgb=(90, 96, 112))
    p += console_block(ctx, "mrea_desk_e", 0.20, 11.11, 1.02, 11.47, (11.30 - 11.11) / K, rgb=(90, 96, 112), screens=2, facing="S", seed=3)
    _, (vx0, vy0, vx1, vy1) = sprite(ctx, "Reactor/ReactorVent")
    p += vent_grate(ctx, "mrea_vent", vx0, vy0, vx1, vy1)
    return p
