import json, os, shutil

BASE = "/opt/station-blanche"
MOUNT = f"{BASE}/mount"
QUAR = f"{BASE}/quarantine"

os.makedirs(QUAR, exist_ok=True)

data = json.load(open(f"{BASE}/logs/correlation.json"))

for f, info in data.items():
    if info["verdict"] == "INFECTED":
        src = os.path.join(MOUNT, f)
        dst = os.path.join(QUAR, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(src):
            shutil.copy2(src, dst)
