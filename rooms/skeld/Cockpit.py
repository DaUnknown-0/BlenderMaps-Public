# Skeld / Navigation (Cockpit) - am Kartenfoto gemessen.
# Drei Pilotensessel (41,56,66) mit Blick nach Osten (Sprites nav_chair*), Kurskonsole (80,98,134) schraeg
# Richtung Nordost, Steuerkonsole (132,143,159) entlang der Kanzel, beide mit der Zeichnung als Oberseite. Zwei Vents.

from shapely import affinity
from shapely.geometry import Polygon, box as sbox

from bm_spec import art_block, art_box, art_floor, office_chair, vent


def floor(ctx):
    return art_floor(ctx, "floor_Cockpit", [sbox(17.2, -6.7, 18.5, -3.1), sbox(17.5, -3.8, 18.6, -2.75), sbox(18.3, -5.7, 19.2, -3.8)])


def props(ctx):
    k = ctx.k
    parts = []
    for (x0, y0, x1, y1) in ((17.24, -3.96, 18.03, -3.17), (17.65, -4.99, 18.47, -4.05), (17.41, -6.63, 18.09, -5.75)):
        parts += office_chair(ctx, "nav_chair", (x0 + x1) / 2, (y0 + y1) / 2 - k * 0.4, (41, 56, 66), (27, 40, 49), (0, 0, 0),
                              back="W", w=0.50, back_top=0.56)   # unter Augenhoehe: Sessel liegen im Laufbereich (19.10.)
    # Kartentisch (gedreht): Korpus, Rand, leuchtende Kartenscheibe, Holo-Linien; Steuerpult mit Schraege und Schirm,
    # Front nach Westen (zum Fenster), auf seinem Collider
    from bm_models import floor_console
    from bm_spec import obox
    tcx, tcy = 18.06, -3.28 - k * 0.62
    tbody = ctx.color("nav_chart_body", (80, 98, 134))
    trim = ctx.color("nav_chart_rim", (110, 128, 164))
    holo = ctx.glow("nav_chart_holo", (120, 200, 240), 2.0)
    parts.append(obox((tcx, tcy, 0.29), (0.88, 0.40, 0.58), tbody, yaw=38.0, outline=(0, 0, 0)))
    parts.append(obox((tcx, tcy, 0.60), (0.92, 0.44, 0.04), trim, yaw=38.0, outline=(0, 0, 0)))
    parts.append(obox((tcx, tcy, 0.625), (0.76, 0.30, 0.01), holo, yaw=38.0))
    for i in range(3):
        parts.append(obox((tcx, tcy, 0.66 + i * 0.05), (0.5 - i * 0.1, 0.012, 0.006), holo, yaw=38.0))
    parts += floor_console(ctx, "nav_steer", 18.76, -4.75, 1.2, 0.72, 0.70, body_rgb=(132, 143, 159), yaw=-90.0, screen_rgb=(90, 170, 220))
    parts += vent(ctx, "Cockpit/NavVentNorth") + vent(ctx, "Cockpit/NavVentSouth")
    return parts
