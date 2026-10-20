# publish_nf.py [tag]: die oeffentlichen Nightfall-Modellpakete (eigene Grafik: Unknown's Atlas) ins Repo
# TOR Mod/Nightfall-Models kopieren, dort catalog.json schreiben und Nightfall/GpuModelCatalog.g.cs erzeugen
# (Name, Groesse, SHA-256, Tag). Danach im Asset-Repo committen, Tag setzen und pushen; derselbe Tag steht dann im
# Katalog der Nightfall-DLL.
#
# Nicht in Nightfall-Models: die Vanilla-Pakete (sie liegen in diesem Repo unter out/ und werden lokal nach
# BepInEx/nightfall-models kopiert) und Karten aus optionalen Erweiterungen (bm_ext.py).
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOR = ROOT.parent.parent
REPO = TOR / "Nightfall-Models"
CS = TOR / "Nightfall" / "GpuModelCatalog.g.cs"
PUBLIC = ["museum", "wald", "park"]


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "v1"
    REPO.mkdir(parents=True, exist_ok=True)
    entries = []
    for key in PUBLIC:
        src = ROOT / "out" / key / f"{key}.nfm"
        data = src.read_bytes()
        entries.append({"name": src.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        dst = REPO / src.name
        if not dst.exists() or dst.read_bytes() != data:
            shutil.copyfile(src, dst)
    (REPO / "catalog.json").write_text(json.dumps({"tag": tag, "files": entries}, indent=1), encoding="utf-8")
    lines = ["// Nightfall - Copyright (C) 2026 DaUnknown-0",
             "// Licensed under GPL-3.0-or-later. See LICENSE for details.",
             "//",
             "// AUTOMATISCH ERZEUGT von Assets/BlenderMaps/publish_nf.py - NICHT VON HAND AENDERN.",
             "// Modellpakete, die Nightfall aus dem oeffentlichen Repo Nightfall-Models laedt (GpuModels).",
             "",
             "namespace Nightfall;",
             "",
             "internal static class GpuModelCatalog",
             "{",
             f"    public const string Tag = \"{tag}\";",
             "",
             "    public static readonly (string Name, long Size, string Sha256)[] Files =",
             "    {"]
    for e in entries:
        lines.append(f"        (\"{e['name']}\", {e['size']}L, \"{e['sha256']}\"),")
    lines += ["    };", "}", ""]
    CS.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(entries)} Pakete, {sum(e['size'] for e in entries) / 1048576:.1f} MB -> {REPO}; Katalog {tag} -> {CS.name}")


if __name__ == "__main__":
    main()
