#!/usr/bin/env python3
"""
quarantine.py — Copie les fichiers infectés/suspects en zone de quarantaine.
La clé USB est montée en lecture seule : aucune suppression n'est effectuée
sur la source. La suppression physique est à réaliser manuellement par
l'opérateur après validation du rapport.
"""
import json
import os
import shutil
from datetime import datetime

BASE = "/opt/station-blanche"
MOUNT = f"{BASE}/mount"
QUAR = f"{BASE}/quarantine"
LOGS = f"{BASE}/logs"

os.makedirs(QUAR, exist_ok=True)

with open(f"{LOGS}/correlation.json") as f:
    data = json.load(f)

quarantined = 0
warned = 0
errors = 0
summary = []

for filepath, info in data.items():
    src = os.path.join(MOUNT, filepath)

    if not os.path.exists(src):
        print(f"  [~] Fichier introuvable sur le point de montage : {filepath}")
        continue

    if info["verdict"] == "INFECTED":
        dst = os.path.join(QUAR, filepath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
            quarantined += 1
            print(f"  [!] INFECTÉ copié en quarantaine : {filepath}")
            summary.append({"file": filepath, "verdict": "INFECTED",
                            "clamav": info.get("clamav", []),
                            "yara": info.get("yara", []),
                            "quarantine_path": dst})
        except Exception as e:
            errors += 1
            print(f"  [-] Erreur copie quarantaine ({filepath}) : {e}")

    elif info["verdict"] == "SUSPICIOUS":
        dst = os.path.join(QUAR, filepath)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
            warned += 1
            print(f"  [?] SUSPECT copié en quarantaine : {filepath} — règles : {', '.join(info.get('yara', []))}")
            summary.append({"file": filepath, "verdict": "SUSPICIOUS",
                            "clamav": info.get("clamav", []),
                            "yara": info.get("yara", []),
                            "quarantine_path": dst})
        except Exception as e:
            errors += 1
            print(f"  [-] Erreur copie quarantaine ({filepath}) : {e}")

# Résumé quarantaine pour generate_report.py
with open(f"{LOGS}/quarantine.json", "w") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "quarantined": quarantined,
        "suspicious": warned,
        "errors": errors,
        "files": summary
    }, f, indent=2)

print(f"[+] Quarantaine : {quarantined} infecté(s), {warned} suspect(s) copiés — suppression manuelle requise sur la clé")
if errors:
    print(f"  [-] {errors} erreur(s) lors des copies")
