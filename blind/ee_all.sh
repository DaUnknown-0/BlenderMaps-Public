#!/bin/bash
# alle Vanilla-Karten exportieren, bauen und die Blindvergleichs-Standpunkte mit EEVEE rendern
cd "/d/programmieren/2025/Amogus/Tracker V2/Tracker/Mod stuff/TOR Mod/Assets/BlenderMaps"
B="/c/Users/moritz/AppData/Local/Programs/Blender Foundation/blender-5.2.2-windows-x64/blender.exe"
D="D:/programmieren/2025/Amogus/Tracker V2/Tracker/Mod stuff/TOR Mod/Assets/BlenderMaps/blind"
for k in ${MAPS:-skeld mira polus airship fungle}; do
  [ -z "$NOEXPORT" ] && python bm_scene.py $k > /dev/null 2>&1 || [ -n "$NOEXPORT" ] || echo "FEHLER export $k"
  "$B" -b --factory-startup -P blender/bm_build.py -- out/$k model 2>&1 | grep -i "Traceback" && echo "FEHLER build $k"
  python -c "
import json; v=json.load(open('blind/new_$k.json'))
for x in v: x['res']=[1280,800]
json.dump(v, open('blind/ee_$k.json','w'))"
  "$B" -b out/$k/$k.blend -P blender/bm_eevee.py -- "$D/ee_$k.json" "$D/ee" ${SAMPLES:-48} 2>&1 | grep "BM eevee"
done
