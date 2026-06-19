#!/bin/bash
set -e

BASE="/opt/station-blanche"
MOUNT="$BASE/mount"
LOGS="$BASE/logs"
BIN="$BASE/bin"

USB_DEV="$1"

# Vérification argument
if [ -z "$USB_DEV" ]; then
    echo "[-] Usage: $0 /dev/sdX1"
    exit 1
fi

# Vérification que c'est bien un périphérique bloc
if [ ! -b "$USB_DEV" ]; then
    echo "[-] $USB_DEV n'est pas un périphérique bloc valide"
    exit 1
fi

mkdir -p "$LOGS" "$MOUNT"

# Nettoyage des logs précédents
rm -f "$LOGS"/*.json "$LOGS"/*.log

echo "[+] Montage de $USB_DEV en lecture seule"
mount -o ro,nosuid,nodev,noexec "$USB_DEV" "$MOUNT" || {
    echo "[-] Échec du montage"
    exit 1
}

# Démontage garanti à la fin (même en cas d'erreur)
cleanup() {
    if mountpoint -q "$MOUNT"; then
        echo "[+] Démontage de $MOUNT"
        umount "$MOUNT" || echo "[!] Avertissement : démontage échoué"
    fi
}
trap cleanup EXIT

echo "[+] Inventaire des fichiers"
python3 "$BIN/list_files.py"

echo "[+] Scan ClamAV"
clamscan -r "$MOUNT" --log="$LOGS/clamav.log" || true

echo "[+] Scan YARA"
yara -r "$BASE/yara_rules"/*.yar "$MOUNT" > "$LOGS/yara.log" 2>&1 || true

echo "[+] Parsing ClamAV"
python3 "$BIN/parse_clamav.py"

echo "[+] Parsing YARA"
python3 "$BIN/parse_yara.py"

echo "[+] Corrélation"
python3 "$BIN/correlate.py"

echo "[+] Quarantaine"
python3 "$BIN/quarantine.py"

echo "[+] Génération du rapport"
python3 "$BIN/generate_report.py"

echo ""
echo "[✓] Scan terminé – rapport disponible dans $BASE/reports/"
