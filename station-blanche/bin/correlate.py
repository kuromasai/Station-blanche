import json

files = json.load(open("/opt/station-blanche/logs/files.json"))
clamav = json.load(open("/opt/station-blanche/logs/clamav.json"))
yara = json.load(open("/opt/station-blanche/logs/yara.json"))

results = {}

for f in files:
    clam = clamav.get(f, "OK")
    yar = yara.get(f, [])

    if clam != "OK":
        verdict = "INFECTED"
    elif yar:
        verdict = "SUSPICIOUS"
    else:
        verdict = "CLEAN"

    results[f] = {
        "clamav": clam,
        "yara": yar,
        "verdict": verdict
    }

with open("/opt/station-blanche/logs/correlation.json", "w") as out:
    json.dump(results, out, indent=2)
