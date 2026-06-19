#!/usr/bin/env python3
import json
import os

LOG = "/opt/station-blanche/logs/yara.log"
OUT = "/opt/station-blanche/logs/yara.json"
BASE = "/opt/station-blanche/mount/"

results = {}

with open(LOG) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        # Format YARA : "rule_name /chemin/vers/fichier"
        # On split sur le premier espace seulement pour gérer les espaces dans les chemins
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue

        rule, path = parts
        # Normalisation du chemin
        path = os.path.normpath(path)
        relative = path.replace(BASE, "") if path.startswith(BASE) else path
        results.setdefault(relative, []).append(rule)

with open(OUT, "w") as f:
    json.dump(results, f, indent=2)

total = sum(len(v) for v in results.values())
print(f"[+] YARA parsé : {total} match(es) sur {len(results)} fichier(s)")
