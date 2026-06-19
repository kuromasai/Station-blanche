#!/usr/bin/env python3
import json

LOG = "/opt/station-blanche/logs/clamav.log"
OUT = "/opt/station-blanche/logs/clamav.json"
BASE = "/opt/station-blanche/mount/"

results = {}

with open(LOG) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        if line.endswith("OK"):
            # On split sur ": OK" pour éviter les problèmes avec les ":" dans les chemins
            path = line[:-3].rstrip(":")
            results[path.replace(BASE, "")] = "OK"
        elif "FOUND" in line:
            # Split sur le dernier ": " pour isoler chemin et signature
            idx = line.rfind(": ")
            if idx != -1:
                path = line[:idx]
                sig = line[idx + 2:].replace(" FOUND", "")
                results[path.replace(BASE, "")] = sig

with open(OUT, "w") as f:
    json.dump(results, f, indent=2)

infected = sum(1 for v in results.values() if v != "OK")
print(f"[+] ClamAV parsé : {infected} détection(s)")
