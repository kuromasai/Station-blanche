#!/usr/bin/env python3
import json

LOGS = "/opt/station-blanche/logs"

with open(f"{LOGS}/files.json") as f:
    files = json.load(f)

with open(f"{LOGS}/clamav.json") as f:
    clamav = json.load(f)

with open(f"{LOGS}/yara.json") as f:
    yara = json.load(f)

results = {}

for filepath in files:
    clam = clamav.get(filepath, "OK")
    yar = yara.get(filepath, [])

    if clam != "OK":
        verdict = "INFECTED"
    elif yar:
        verdict = "SUSPICIOUS"
    else:
        verdict = "CLEAN"

    results[filepath] = {
        "clamav": clam,
        "yara": yar,
        "verdict": verdict
    }

with open(f"{LOGS}/correlation.json", "w") as f:
    json.dump(results, f, indent=2)

infected = sum(1 for v in results.values() if v["verdict"] == "INFECTED")
suspicious = sum(1 for v in results.values() if v["verdict"] == "SUSPICIOUS")
print(f"[+] Corrélation terminée : {infected} infecté(s), {suspicious} suspect(s)")
