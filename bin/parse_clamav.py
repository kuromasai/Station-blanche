import json

LOG = "/opt/station-blanche/logs/clamav.log"
OUT = "/opt/station-blanche/logs/clamav.json"
BASE = "/opt/station-blanche/mount/"

results = {}

with open(LOG) as f:
    for line in f:
        line = line.strip()
        if line.endswith("OK"):
            path = line.split(":")[0]
            results[path.replace(BASE, "")] = "OK"
        elif "FOUND" in line:
            path, sig = line.split(": ", 1)
            results[path.replace(BASE, "")] = sig.replace(" FOUND", "")

with open(OUT, "w") as f:
    json.dump(results, f, indent=2)


