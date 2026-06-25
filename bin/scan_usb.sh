#!/bin/bash

BASE="/opt/station-blanche"
MOUNT="$BASE/mount"
LOGS="$BASE/logs"
BIN="$BASE/bin"

USB_DEV="$1"

# Récupération de l'utilisateur réel derrière sudo (pour ouvrir le rapport dans sa session)
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
REAL_DISPLAY=$(sudo -u "$REAL_USER" printenv DISPLAY 2>/dev/null || echo ":0")
REAL_XAUTHORITY="$REAL_HOME/.Xauthority"
export REAL_USER REAL_HOME REAL_DISPLAY REAL_XAUTHORITY

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

# FIX 5 : Vérification de la présence de tous les scripts Python avant de commencer
for script in list_files parse_clamav parse_yara correlate quarantine generate_report; do
    [ -f "$BIN/${script}.py" ] || { echo "[-] Script manquant : ${script}.py"; exit 1; }
done

# FIX 1 : mkdir -p avec vérification explicite avant le nettoyage des logs
mkdir -p "$LOGS" "$MOUNT" || { echo "[-] Impossible de créer les répertoires nécessaires"; exit 1; }

# Nettoyage des logs précédents (après mkdir garanti)
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

# FIX 4 : Vérifier que $MOUNT existe ET est non vide avant de tenter umount
if [ -d "$MOUNT" ] && [ -n "$(ls -A "$MOUNT" 2>/dev/null)" ]; then
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
# FIX 3 : --stdout pour forcer l'affichage des warnings ClamAV en temps réel
clamscan -r --stdout "$MOUNT" --log="$LOGS/clamav.log"
CLAM_EXIT=$?
# FIX 6 : Sauvegarde du code de sortie ClamAV pour generate_report.py
echo "$CLAM_EXIT" > "$LOGS/clamav.exitcode"
# 0 = propre, 1 = virus trouvé, 2 = erreur
if [ $CLAM_EXIT -eq 2 ]; then
    echo "[-] ClamAV a rencontré une erreur (code 2)"
    exit 1
fi

echo "[+] Scan YARA"
# FIX 7 : Vérification de la présence d'au moins une règle .yar avant d'appeler YARA
YARA_RULES=("$BASE/yara_rules"/*.yar)
if [ ! -f "${YARA_RULES[0]}" ]; then
    echo "[-] Aucune règle YARA trouvée dans $BASE/yara_rules/"
    exit 1
fi
yara -r "${YARA_RULES[@]}" "$MOUNT" > "$LOGS/yara.log" 2>&1
YARA_EXIT=$?
# FIX 6 : Sauvegarde du code de sortie YARA pour generate_report.py
echo "$YARA_EXIT" > "$LOGS/yara.exitcode"
# 0 = ok, 1 = match trouvé, autre = erreur
# FIX 2 : Log explicite si YARA a trouvé des matches (code 1), sans bloquer
if [ $YARA_EXIT -eq 1 ]; then
    echo "[!] YARA a trouvé des correspondances (code 1) — voir $LOGS/yara.log"
elif [ $YARA_EXIT -gt 1 ]; then
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
REAL_USER="$REAL_USER" REAL_HOME="$REAL_HOME" REAL_DISPLAY="$REAL_DISPLAY" REAL_XAUTHORITY="$REAL_XAUTHORITY" \
    python3 "$BIN/generate_report.py" || { echo "[-] Erreur generate_report.py"; exit 1; }

echo ""
echo "[✓] Scan terminé – rapport disponible dans $BASE/reports/"
