#!/usr/bin/env python3
import json
import os
import subprocess
import html as html_module
from datetime import datetime

BASE = "/opt/station-blanche"
LOGS = f"{BASE}/logs"
REPORTS = f"{BASE}/reports"

os.makedirs(REPORTS, exist_ok=True)

with open(f"{LOGS}/files.json") as f:
    files = json.load(f)

with open(f"{LOGS}/correlation.json") as f:
    correlation = json.load(f)

total_files = len(files)
infected = sum(1 for v in correlation.values() if v["verdict"] == "INFECTED")
suspicious = sum(1 for v in correlation.values() if v["verdict"] == "SUSPICIOUS")

if infected:
    status = "INFECTED"
    status_color = "#c0392b"
elif suspicious:
    status = "SUSPICIOUS"
    status_color = "#e67e22"
else:
    status = "CLEAN"
    status_color = "#27ae60"

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
date_file = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
path = f"{REPORTS}/report_{date_file}.html"

verdict_colors = {
    "INFECTED": "#c0392b",
    "SUSPICIOUS": "#e67e22",
    "CLEAN": "#27ae60"
}

rows = ""
for filepath, v in correlation.items():
    color = verdict_colors.get(v["verdict"], "#000")
    safe_path = html_module.escape(filepath)
    safe_clam = html_module.escape(v["clamav"])
    safe_yara = html_module.escape(", ".join(v["yara"]))
    safe_verdict = html_module.escape(v["verdict"])
    rows += f"""
    <tr>
        <td>{safe_path}</td>
        <td>{safe_clam}</td>
        <td>{safe_yara if safe_yara else "—"}</td>
        <td style="color:{color};font-weight:bold">{safe_verdict}</td>
    </tr>"""

# Hash recap pour traçabilité forensique
hash_section = ""
hash_file = f"{LOGS}/hashes.json"
if os.path.exists(hash_file):
    with open(hash_file) as f:
        hashes = json.load(f)
    hash_rows = "".join(
        f"<tr><td>{html_module.escape(fp)}</td><td><code>{html_module.escape(h)}</code></td></tr>"
        for fp, h in hashes.items()
    )
    hash_section = f"""
    <h2>Hashes SHA-256</h2>
    <table>
        <tr><th>Fichier</th><th>SHA-256</th></tr>
        {hash_rows}
    </table>"""

html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Station Blanche – Rapport {date_file}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 20px; }}
        h1 {{ color: #00d4ff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px; }}
        h2 {{ color: #00d4ff; margin-top: 30px; }}
        .summary {{ background: #16213e; border-radius: 8px; padding: 20px; margin: 20px 0; display: flex; gap: 20px; flex-wrap: wrap; }}
        .stat {{ background: #0f3460; border-radius: 6px; padding: 15px 25px; text-align: center; }}
        .stat .value {{ font-size: 2em; font-weight: bold; }}
        .stat .label {{ font-size: 0.85em; color: #aaa; }}
        .verdict-badge {{ font-size: 1.5em; font-weight: bold; color: {status_color}; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background: #0f3460; padding: 10px; text-align: left; }}
        td {{ padding: 8px 10px; border-bottom: 1px solid #2a2a4a; word-break: break-all; }}
        tr:hover td {{ background: #1e2a4a; }}
        code {{ font-size: 0.8em; color: #aaa; }}
    </style>
</head>
<body>
    <h1>🛡️ Station Blanche – Rapport d'analyse</h1>

    <div class="summary">
        <div class="stat">
            <div class="label">Date</div>
            <div style="font-size:1.1em">{now}</div>
        </div>
        <div class="stat">
            <div class="label">Verdict global</div>
            <div class="verdict-badge">{status}</div>
        </div>
        <div class="stat">
            <div class="value">{total_files}</div>
            <div class="label">Fichiers analysés</div>
        </div>
        <div class="stat">
            <div class="value" style="color:#c0392b">{infected}</div>
            <div class="label">Infectés</div>
        </div>
        <div class="stat">
            <div class="value" style="color:#e67e22">{suspicious}</div>
            <div class="label">Suspects</div>
        </div>
    </div>

    <h2>Détail des fichiers</h2>
    <table>
        <tr>
            <th>Fichier</th>
            <th>ClamAV</th>
            <th>YARA</th>
            <th>Verdict</th>
        </tr>
        {rows}
    </table>

    {hash_section}
</body>
</html>"""

with open(path, "w") as f:
    f.write(html_content)

print(f"[✓] Rapport généré : {path}")
subprocess.run(["xdg-open", path])
