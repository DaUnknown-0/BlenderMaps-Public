# Skeld - kartenweite Eingriffe in den Grundriss.
#
# FLOOR_ADD_ROOMS: Einrichtung, die im Spiel die Kollisionskante bildet (Pulte vor der Wand): Among Us setzt den Collider
# an die Vorderkante der Moebel, der Grundriss stellte die Wand genau dorthin und die Moebel waren nur aufgemalt
# (Meldungen 18.10.). Hier bekommt der Raum den Streifen bis zur echten Wandflaeche dazu, die Raumdatei baut die
# Moebel hinein.

from shapely.geometry import Polygon
from shapely.ops import unary_union

FLOOR_ADD_ROOMS = {
    # Admin-Pultreihe: Wandflaeche 0,34 hinter der Kollisionskante (Oberkante des Wandbands -5,80 -> Fuss -6,62..-6,66)
    "Admin": [[(3.0, -7.05), (6.2, -7.05), (6.2, -6.66), (3.0, -6.66)]],
    # Security: Pult vor der Nordwand (Kante -2,95 = Pultfront, Wand -2,77, Schraegen verlaengert) und die Kerbe, die
    # der Stuhl-Collider in den Boden schnitt (der Stuhl stand in einem Wandblock)
    "Security": [[(-13.62, -2.99), (-13.39, -2.77), (-12.74, -2.77), (-12.54, -2.96)],
                 [(-13.56, -3.42), (-13.05, -3.42), (-13.05, -2.94), (-13.56, -2.94)],
                 # L-Tisch samt Hocker an der Ostwand (Collider-Linie bis zur Wand), stand sonst in einem Wandblock
                 [(-12.94, -4.66), (-11.70, -4.66), (-11.70, -6.05), (-12.38, -5.94), (-12.42, -5.67), (-12.75, -5.71),
                  (-12.94, -5.58)]],
    # Shields-Ecke: vom Flur aus steht der Querbalken (x 5,9..7,05 / y -12,88..-13,62) als Wand (User 19.10.: "echte
    # Wand, nicht dieses Gitter"), der senkrechte Balken des L zwischen Nische und Schildgrube gehoert NICHT hin (User
    # 19.10. abends, Blick vom Schildpult nach Westen: "Diese Wand gehoert da einfach nicht hin"). Die Nische ist bis zur
    # Grubenkante (x 7,05) und bis y -14,9 durchgehend Comms-Boden; suedlich davon bleibt die Wandmasse zum Comms-Raum,
    # oestlich unterhalb der Grube reicht der Boden bis an die Schildplattform (x 7,24), damit kein Wandsplitter bleibt.
    # Darin steht der DivertPowerConsole-Kasten (Comms.py), das Gelaender an der Grubenkante baut Shields.py.
    "Comms": [[(5.80, -13.62), (7.05, -13.62), (7.05, -13.97), (7.24, -13.97), (7.24, -14.90), (5.80, -14.90)]],
}


def adjust(sc):
    for name, polys in FLOOR_ADD_ROOMS.items():
        # Die Polygone reichen bewusst 0,1..0,2 in die Wandmasse dahinter (Security: Ostwand ist ~0,6 dick), damit
        # zwischen Moebel und Wand keine Wandsplitter stehen bleiben
        add = unary_union([Polygon(p) for p in polys]).buffer(0)
        sc.rooms[name] = unary_union([sc.rooms[name], add]).buffer(0)
        for n in sc.rooms:
            if n != name:
                sc.rooms[n] = sc.rooms[n].difference(add).buffer(0)
        sc.floor = unary_union([sc.floor, add]).buffer(0)
        sc.wall_holes = [h.difference(add).buffer(0) for h in sc.wall_holes if not h.difference(add).is_empty]
