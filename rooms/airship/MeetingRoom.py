# Airship / Meeting Room - erhoeht auf 4,147 (Leiterband ladder_meeting), am Kartenfoto gemessen (Zoom 2,8:
# x = 7,6 + px/145,6, y = 16,8 - py/145,6).
#
# Boden blaugrau (102,138,154), Rueckwand beige mit Boegen (Zeichnung). Tisch (162,146,120), Platte 8,62..13,37 /
#   14,60..15,53 mit Notfallknopf (roter Taster auf Sockel, 3D 19.10.); zwoelf Schalensessel (46,121,173)/(41,105,162) bei x 9,01 9,80 10,62 11,41 12,20
#   13,03, Reihe Nord (Lehne nach Norden) und Sued.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from shapely.geometry import box as sbox                                          # noqa: E402
from bm_spec import art_floor, box, cyl, lathe, office_chair                      # noqa: E402

Z = 4.147
CHAIR_X = [9.01, 9.80, 10.62, 11.41, 12.20, 13.03]
Z_TABLE = 0.45


def floor(ctx):
    return art_floor(ctx, "floor_MeetingRoom", holes=[sbox(8.55, 14.25, 13.45, 16.0)])


def props(ctx):
    parts = []
    k = ctx.k
    wood = ctx.color("meet_table", (162, 146, 120))
    woodd = ctx.color("meet_table_dark", (120, 106, 86))
    cy = (14.60 + 15.53) / 2 - k * Z_TABLE
    parts.append(box(10.995, cy, 4.75, 0.93, Z_TABLE - 0.06, Z_TABLE, wood, bevel=0.02, outline=(38, 49, 54)))
    parts.append(box(10.995, cy, 4.55, 0.73, Z_TABLE, Z_TABLE + 0.004, woodd))
    # Notfallknopf: Sockel, Taster, Haube offen
    base = ctx.color("meet_btn_base", (70, 74, 80))
    parts.append(cyl(10.995, cy, 0.16, Z_TABLE, Z_TABLE + 0.04, base, seg=24, outline=(30, 32, 36)))
    parts.append(cyl(10.995, cy, 0.1, Z_TABLE + 0.04, Z_TABLE + 0.09, ctx.glow("meet_btn", (220, 50, 50), 1.3), seg=20, outline=(90, 20, 20)))
    paper = ctx.color("meet_paper", (235, 238, 240))
    for px, rot in ((9.4, 12.0), (12.5, -8.0), (10.2, 25.0)):
        parts.append(box(px, cy + 0.1, 0.28, 0.2, Z_TABLE + 0.004, Z_TABLE + 0.012, paper, rot=rot, outline=(120, 120, 130)))
    for dx in (-1.9, 0.0, 1.9):
        parts.append(box(10.995 + dx, cy, 0.25, 0.4, 0.0, Z_TABLE - 0.06, woodd, outline=(38, 49, 54)))
    for x in CHAIR_X:
        parts += office_chair(ctx, "meet_chair", x, cy + 0.68, (46, 121, 173), (41, 105, 162), (20, 40, 60), back="N",
                              w=0.5, seat_z=0.34, back_top=0.78)
        parts += office_chair(ctx, "meet_chair", x, cy - 0.68, (46, 121, 173), (41, 105, 162), (20, 40, 60), back="S",
                              w=0.5, seat_z=0.34, back_top=0.78)
    return parts
