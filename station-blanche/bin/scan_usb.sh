#!/bin/bash

BASE="/opt/station-blanche"
MOUNT="$BASE/mount"
LOGS="$BASE/logs"
BIN="$BASE/bin"

USB_DEV="$1"

if [ -z "$USB_DEV" ]; then
    echo "Usage: $0 /dev/sdX1"
    exit 1
fi

mkdir -p "$LOGS" "$MOUNT"

echo "[+] Montage de $USB_DEV"
mount -o ro,nosuid,nodev,noexec "$USB_DEV" "$MOUNT" || exit 1

echo "[+] Inventaire des fichiers"
python3 "$BIN/list_files.py"

echo "[+] Scan ClamAV"
clamscan -r "$MOUNT" --log="$LOGS/clamav.log"

echo "[+] Scan YARA"
yara -r "$BASE/yara_rules"/*.yar "$MOUNT" > "$LOGS/yara.log" 2>&1 || true

echo "[+] Parsing"
python3 "$BIN/parse_clamav.py"
python3 "$BIN/parse_yara.py"

echo "[+] Corrélation"
python3 "$BIN/correlate.py"

echo "[+] Quarantaine"
python3 "$BIN/quarantine.py"

echo "[+] Rapport"
python3 "$BIN/generate_report.py"

echo "[+] Démontage"
umount "$MOUNT"

echo "[✓] Scan terminé"
