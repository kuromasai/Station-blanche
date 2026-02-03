import json

LOG = "/opt/station-blanche/logs/yara.log"
OUT = "/opt/station-blanche/logs/yara.json"
BASE = "/opt/station-blanche/mount/"

results = {}

with open(LOG) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        rule, path = line.split(" ", 1)
        results.setdefault(path.replace(BASE, ""), []).append(rule)

with open(OUT, "w") as f:
    json.dump(results, f, indent=2)


