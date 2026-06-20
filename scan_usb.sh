#!/bin/bash

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

# Démontage garanti à la fin (même en cas d'erreur) — posé AVANT le mount
cleanup() {
    if mountpoint -q "$MOUNT" 2>/dev/null; then
        echo "[+] Démontage de $MOUNT"
        umount "$MOUNT" || echo "[!] Avertissement : démontage échoué"
    fi
}
trap cleanup EXIT

echo "[+] Montage de $USB_DEV en lecture seule"

# Démonter l'automount du système s'il existe déjà
EXISTING_MOUNT=$(findmnt -n -o TARGET --source "$USB_DEV" 2>/dev/null)
if [ -n "$EXISTING_MOUNT" ]; then
    echo "[~] Démontage de l'automount existant : $EXISTING_MOUNT"
    umount "$EXISTING_MOUNT" || {
        echo "[-] Impossible de démonter $EXISTING_MOUNT"
        exit 1
    }
fi

# Vérifier que le point de montage est vide
if [ -n "$(ls -A "$MOUNT" 2>/dev/null)" ]; then
    echo "[!] $MOUNT n'est pas vide, tentative de démontage..."
    umount "$MOUNT" 2>/dev/null || true
fi

mount -o ro,nosuid,nodev,noexec "$USB_DEV" "$MOUNT" || {
    echo "[-] Échec du montage"
    exit 1
}

echo "[+] Inventaire des fichiers"
python3 "$BIN/list_files.py" || { echo "[-] Erreur list_files.py"; exit 1; }

echo "[+] Scan ClamAV"
clamscan -r "$MOUNT" --log="$LOGS/clamav.log"
CLAM_EXIT=$?
# 0 = propre, 1 = virus trouvé, 2 = erreur
if [ $CLAM_EXIT -eq 2 ]; then
    echo "[-] ClamAV a rencontré une erreur (code 2)"
    exit 1
fi

echo "[+] Scan YARA"
yara -r "$BASE/yara_rules"/*.yar "$MOUNT" > "$LOGS/yara.log" 2>&1
YARA_EXIT=$?
# 0 = ok, 1 = match trouvé, autre = erreur
if [ $YARA_EXIT -gt 1 ]; then
    echo "[-] YARA a rencontré une erreur (code $YARA_EXIT)"
    exit 1
fi

echo "[+] Parsing ClamAV"
python3 "$BIN/parse_clamav.py" || { echo "[-] Erreur parse_clamav.py"; exit 1; }

echo "[+] Parsing YARA"
python3 "$BIN/parse_yara.py" || { echo "[-] Erreur parse_yara.py"; exit 1; }

echo "[+] Corrélation"
python3 "$BIN/correlate.py" || { echo "[-] Erreur correlate.py"; exit 1; }

echo "[+] Quarantaine"
python3 "$BIN/quarantine.py" || { echo "[-] Erreur quarantine.py"; exit 1; }

echo "[+] Génération du rapport"
python3 "$BIN/generate_report.py" || { echo "[-] Erreur generate_report.py"; exit 1; }

echo ""
echo "[✓] Scan terminé – rapport disponible dans $BASE/reports/"
