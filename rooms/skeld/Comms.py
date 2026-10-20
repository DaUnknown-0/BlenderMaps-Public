# Skeld / Comms - am Kartenfoto gemessen.
# Funktisch an der Nordwand (107,85,66), Seitentische (123,117,96) mit gruenen Bildschirmen, Arbeitsplatz unten
# (Sprite comms_deskbot): Tisch, schwarzer Monitor (33,40,46), Stuhl (63,134,135) mit Blick nach Sueden.

# Ich-Sicht (Meldungen 18.10.: einfarbige Kloetze): Funktisch mit gezeichneter Front zur Raummitte (art_container),
# Lautsprecher-Seitengeraete mit ihrer Zeichnung auf der Innenseite (face_e/face_w), Monitor mit Bildschirm zum Stuhl.

from shapely.geometry import box as sbox

import bm_tex as T
from bm_spec import art_block, art_container, art_floor, box, office_chair, screen_tex


def floor(ctx):
    holes = [sbox(2.95, -14.6, 4.2, -13.95), sbox(1.45, -16.8, 2.15, -15.25), sbox(5.9, -16.8, 6.6, -15.25), sbox(2.85, -17.6, 5.45, -16.15)]
    return art_floor(ctx, "floor_Comms", holes)


def props(ctx):
    k = ctx.k
    r = ctx.ref
    from bm_models import console_block, table, tv_unit, tape_machine, shelf_unit
    # Funkgestell an der Nordwand (Meldung 19.10. "noch nicht 3D"): zwei Bandgeraete im Gestell, Pult davor mit Schirmen
    parts = tape_machine(ctx, "com_tape_l", 3.3, -14.42, 0.55, 0.26, h=1.1, rgb=(87, 83, 76), light=(130, 124, 112))
    parts += tape_machine(ctx, "com_tape_r", 3.9, -14.42, 0.55, 0.26, h=1.1, rgb=(87, 83, 76), light=(130, 124, 112))
    parts += console_block(ctx, "com_radio", 3.02, -14.95, 4.18, -14.56, 0.5, rgb=(107, 85, 66), screens=2, seed=5)
    parts += tv_unit(ctx, "com_tv_l", 1.80, -16.05 - k * 0.48, 1.1, 0.7, facing="E", rgb=(123, 117, 96))
    parts += tv_unit(ctx, "com_tv_r", 6.27, -16.06 - k * 0.48, 1.1, 0.7, facing="W", rgb=(123, 117, 96))
    parts += table(ctx, "com_desk", 3.05, -17.52 - k * 0.48, 5.30, -16.95 - k * 0.48, h=0.48, top_rgb=(107, 85, 66), leg_rgb=(70, 56, 44))
    mon = ctx.color("com_monitor", (33, 40, 46))
    m = box(4.65, -17.30, 0.85, 0.12, 0.48, 1.05, mon, rot=-12, bevel=0.02, outline=(0, 0, 0))
    m["face_n"] = screen_tex(ctx, "com_monitor_screen", (33, 40, 46), (40, 96, 92), aspect=0.85 / 0.57)
    parts.append(m)
    parts += office_chair(ctx, "com_chair", 3.80, -16.55 - k * 0.4, (63, 134, 135), (46, 94, 107), (0, 0, 0), back="N", w=0.46,
                          back_top=0.82)
    # DivertPowerConsole in der Nische der Shields-Ecke (Boden x 5,86..7,05 / y -13,62..-14,9, zur Schildgrube offen):
    # Kasten mit Anzeige und Blitzschild nach Westen (bedient von x < 5,86), Kabelrohr oben zur Decke. 0,1 nach Osten
    # gerueckt; die Rueckseite (vom Schildpult aus sichtbar) ist ein geschlossenes Blech mit Lueftungsschlitzen.
    dx = 0.10
    parts += console_block(ctx, "com_divert", 5.92 + dx, -14.44, 6.62 + dx, -13.68, 0.9, rgb=(150, 160, 152), screens=1,
                           facing="W", seed=11, screen_rgbs=[(110, 180, 150)])
    sign = ctx.glow("com_divert_sign", (250, 210, 60), 1.2)
    parts.append(box(5.905 + dx, -14.06, 0.012, 0.16, 0.28, 0.42, sign))
    parts.append(box(5.90 + dx, -14.06, 0.008, 0.06, 0.30, 0.40, ctx.color("com_divert_bolt", (40, 36, 30))))
    back = ctx.color("com_divert_back", (118, 126, 120))
    slot = ctx.color("com_divert_slot", (52, 58, 56))
    parts.append(box(6.626 + dx, -14.06, 0.012, 0.62, 0.12, 0.82, back))
    for i in range(5):
        parts.append(box(6.634 + dx, -14.06, 0.006, 0.44, 0.52 + i * 0.05, 0.535 + i * 0.05, slot))
    pipe = ctx.color("com_divert_pipe", (110, 96, 72))
    from bm_spec import tube
    parts.append(tube([(6.25 + dx, -13.9, 0.9), (6.25 + dx, -13.9, 1.39)], 0.04, pipe, seg=10))
    return parts
