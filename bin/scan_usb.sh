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

# Vérification de la présence de tous les scripts Python avant de commencer
for script in list_files parse_clamav parse_yara correlate quarantine generate_report; do
    [ -f "$BIN/${script}.py" ] || { echo "[-] Script manquant : ${script}.py"; exit 1; }
done

# mkdir -p avec vérification explicite avant le nettoyage des logs
mkdir -p "$LOGS" "$MOUNT" || { echo "[-] Impossible de créer les répertoires nécessaires"; exit 1; }

# Nettoyage des logs précédents
rm -f "$LOGS"/*.json "$LOGS"/*.log

# Démontage garanti à la fin (même en cas d'erreur)
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

# Vérifier que $MOUNT est non vide avant de tenter umount
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
clamscan -r --stdout "$MOUNT" --log="$LOGS/clamav.log"
CLAM_EXIT=$?
echo "$CLAM_EXIT" > "$LOGS/clamav.exitcode"
if [ $CLAM_EXIT -eq 2 ]; then
    echo "[-] ClamAV a rencontré une erreur (code 2)"
    exit 1
fi

echo "[+] Scan YARA"

# Construire un fichier index incluant toutes les règles .yar
# en excluant les fichiers qui nécessitent des variables externes (LOKI/THOR)
RULES_DIR="$BASE/yara_rules"
EXCLUDED_LIST="$RULES_DIR/signature-base/yara/external-variable-rules.txt"
INDEX_FILE=$(mktemp /tmp/yara_index_XXXXXX.yar)

while IFS= read -r -d '' f; do
    fname=$(basename "$f")
    # Exclure les fichiers avec external variables si la liste existe
    if [ -f "$EXCLUDED_LIST" ] && grep -qxF "$fname" "$EXCLUDED_LIST" 2>/dev/null; then
        continue
    fi
    echo "include \"$f\"" >> "$INDEX_FILE"
done < <(find "$RULES_DIR" -name "*.yar" -print0)

RULES_COUNT=$(grep -c "include" "$INDEX_FILE" 2>/dev/null || echo 0)

if [ "$RULES_COUNT" -eq 0 ]; then
    echo "[-] Aucune règle YARA trouvée dans $RULES_DIR"
    rm -f "$INDEX_FILE"
    exit 1
fi

echo "[+] $RULES_COUNT règles YARA chargées"

yara "$INDEX_FILE" -r "$MOUNT" > "$LOGS/yara.log" 2>&1
YARA_EXIT=$?
rm -f "$INDEX_FILE"

echo "$YARA_EXIT" > "$LOGS/yara.exitcode"

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
