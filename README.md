# BlenderMaps

Alle Among-Us-Karten (Skeld, Mira HQ, Polus, Airship, The Fungle) und die Unknown's-Atlas-Karten (Museum, Wald,
Park) als echte 3D-Modelle, Raum für Raum gegen die Originalgrafik nachgebaut. Grundlage für den GPU-Modus von
Nightfall.

## Inhalt

- `out/<karte>/<karte>.glb`: das fertige Modell (Blender/glTF, Texturen eingebettet).
- `out/<karte>/<karte>.nfm`: das Laufzeitpaket für Nightfall (Dreiecke je Material in 8-m-Kacheln, Normalen,
  eingebackene Schattierung, Bodenhöhen-Raster, Texturen bis 1024 px).
- Quellen: `bm_*.py` (Vorlage, Grundriss, Szene, Objekte, Bildreinigung), `rooms/<karte>/*.py` (Raumdateien),
  `blender/*.py` (Bau, Ansichten, Export), `atlasdata/` (aus den Atlas-Kartendaten, `atlas_import.py`).

Die Vanilla-Modelle sind seit dem 19.10. komplett selbst gezeichnet (`bm_style.py`); die Spielgrafik dient nur als
Maß- und Farbreferenz und liegt nicht in diesem Repo.
Museum, Wald und Park liegen zusätzlich öffentlich in `DaUnknown-0/Nightfall-Models` (eigene Grafik).

## Vanilla-Pakete lokal installieren

Die `.nfm`-Dateien nach `<Among Us>\BepInEx\nightfall-models\` kopieren (Ordner anlegen). Nightfall nutzt sie,
sobald `Look / GpuWorld` an ist (Standard). Auf Skeld, Mira und Polus gilt das nur für den eigenen Rechner (die
anderen sehen die Software-Ansicht mit denselben Licht- und Sichtregeln); Airship und Fungle schalten die
Ich-Sicht nur ein, wenn alle Spieler das Paket haben.

## Ablauf

```
python bm_scene.py <karte>                       # Szene -> out/<karte>/scene.json + tex/
blender -b --factory-startup -P blender/bm_build.py -- out/<karte> model   # -> .blend + .glb
blender -b out/<karte>/<karte>.blend -P blender/bm_export_nf.py -- out/<karte>
python pack_nf.py <karte>                        # -> out/<karte>/<karte>.nfm
python publish_nf.py v<n>                        # nur Atlas-Karten: Nightfall-Models + Katalog in Nightfall
```

Vorlage der Vanilla-Karten: `../NightfallWeb/data/<karte>ship/` (Survey-Aufnahme, nicht in diesem Repo).
Blender 5.2.2. Prüfwerkzeuge: `roomviews.py` (Ich-Perspektive je Raum), `shots.py` (gezielte Ansichten),
`zoomgrid.py`, `review.py`, `wallcheck.py` (Rundblicke je Raum, zählt Himmel/Löcher und Schwarzflächen, Kontaktbogen
der schlimmsten Ansichten).
