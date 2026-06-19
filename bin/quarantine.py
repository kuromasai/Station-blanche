#!/usr/bin/env python3
import json
import os
import shutil

BASE = "/opt/station-blanche"
MOUNT = f"{BASE}/mount"
QUAR = f"{BASE}/quarantine"

os.makedirs(QUAR, exist_ok=True)

with open(f"{BASE}/logs/correlation.json") as f:
    data = json.load(f)

quarantined = 0
warned = 0

for filepath, info in data.items():
    src = os.path.join(MOUNT, filepath)

    if not os.path.exists(src):
        continue

    if info["verdict"] == "INFECTED":
        dst = os.path.join(QUAR, filepath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        os.remove(src)  # Suppression de la clé USB
        quarantined += 1
        print(f"  [!] INFECTÉ mis en quarantaine : {filepath}")

    elif info["verdict"] == "SUSPICIOUS":
        warned += 1
        print(f"  [?] SUSPECT (YARA) : {filepath} — règles : {', '.join(info['yara'])}")

print(f"[+] Quarantaine : {quarantined} fichier(s) déplacé(s), {warned} fichier(s) suspect(s) à vérifier manuellement")
