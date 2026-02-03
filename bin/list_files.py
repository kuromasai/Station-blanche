#!/usr/bin/env python3
import os, json

MOUNT = "/opt/station-blanche/mount"
OUT = "/opt/station-blanche/logs/files.json"

files = []

for root, _, filenames in os.walk(MOUNT):
    for f in filenames:
        full = os.path.join(root, f)
        files.append(full.replace(MOUNT + "/", ""))

with open(OUT, "w") as f:
    json.dump(files, f, indent=2)

print(f"[+] {len(files)} fichiers inventoriés")
