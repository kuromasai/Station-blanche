import json, os, subprocess
from datetime import datetime

BASE = "/opt/station-blanche"
LOGS = f"{BASE}/logs"
REPORTS = f"{BASE}/reports"

files = json.load(open(f"{LOGS}/files.json"))
correlation = json.load(open(f"{LOGS}/correlation.json"))

total_files = len(files)
infected = sum(1 for v in correlation.values() if v["verdict"] == "INFECTED")
status = "INFECTED" if infected else "CLEAN"

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
date_file = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

path = f"{REPORTS}/report_{date_file}.html"

html = f"""
<h1>Station Blanche Report</h1>
<p>Date : {now}</p>
<p>Verdict global : <b>{status}</b></p>
<p>Total fichiers : {total_files}</p>
<p>Fichiers infectés : {infected}</p>

<table border=1>
<tr><th>Fichier</th><th>ClamAV</th><th>YARA</th><th>Verdict</th></tr>
"""

for f, v in correlation.items():
    html += f"<tr><td>{f}</td><td>{v['clamav']}</td><td>{', '.join(v['yara'])}</td><td>{v['verdict']}</td></tr>"

html += "</table>"

with open(path, "w") as f:
    f.write(html)

# Affichage clair dans le terminal
print(f"[✓] Rapport généré : {path}")

# Ouverture automatique dans le navigateur
subprocess.run(["xdg-open", path])
