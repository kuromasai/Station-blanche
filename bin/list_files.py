#!/usr/bin/env python3
import os
import json
import hashlib

MOUNT = "/opt/station-blanche/mount"
OUT_FILES = "/opt/station-blanche/logs/files.json"
OUT_HASHES = "/opt/station-blanche/logs/hashes.json"

files = []
hashes = {}

for root, _, filenames in os.walk(MOUNT):
    for filename in filenames:
        full_path = os.path.join(root, filename)
        relative = full_path.replace(MOUNT + "/", "")
        files.append(relative)

        # Hash SHA-256
        sha256 = hashlib.sha256()
        try:
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            hashes[relative] = sha256.hexdigest()
        except (PermissionError, OSError) as e:
            hashes[relative] = f"ERROR: {e}"

with open(OUT_FILES, "w") as f:
    json.dump(files, f, indent=2)

with open(OUT_HASHES, "w") as f:
    json.dump(hashes, f, indent=2)

print(f"[+] {len(files)} fichier(s) inventorié(s) et hashé(s)")
