#!/bin/bash
set -e

echo "[+] Installation Station Blanche – Debian 13"

#################################
# Vérification root
#################################
if [ "$EUID" -ne 0 ]; then
  echo "[-] Ce script doit être exécuté en root"
  exit 1
fi

#################################
# Vérification OS
#################################
if ! grep -q 'VERSION_ID="13"' /etc/os-release; then
  echo "[-] Ce script est prévu pour Debian 13 uniquement"
  exit 1
fi

#################################
# Variables
#################################
BASE="/opt/station-blanche"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_DIR="$REPO_DIR/station-blanche"

#################################
# Vérification source
#################################
if [ ! -d "$SOURCE_DIR" ]; then
  echo "[-] Dossier source introuvable : $SOURCE_DIR"
  exit 1
fi

#################################
# Mise à jour système
#################################
echo "[+] Mise à jour système"
apt update && apt upgrade -y

#################################
# Installation dépendances
#################################
echo "[+] Installation des dépendances"
apt install -y \
  clamav clamav-daemon \
  yara \
  python3 python3-pip \
  rsync

#################################
# Dépendances Python
#################################
if [ -f "$SOURCE_DIR/requirements.txt" ]; then
  echo "[+] Installation des dépendances Python"
  pip3 install --break-system-packages -r "$SOURCE_DIR/requirements.txt"
else
  echo "[!] Aucun requirements.txt trouvé – pip3 non utilisé"
fi

#################################
# Mise à jour signatures ClamAV
#################################
echo "[+] Mise à jour ClamAV"
systemctl stop clamav-freshclam || true
freshclam
systemctl start clamav-freshclam || true

#################################
# Déploiement Station Blanche
#################################
echo "[+] Déploiement vers $BASE"
if [ -d "$BASE" ]; then
  echo "[!] $BASE existe déjà – mise à jour du contenu"
else
  mkdir -p "$BASE"
fi

rsync -a --delete \
  "$SOURCE_DIR/" \
  "$BASE/"

#################################
# Permissions sécurisées
#################################
echo "[+] Application des permissions"
chown -R root:root "$BASE"
chmod -R 750 "$BASE"

# chmod +x uniquement sur les .sh
find "$BASE/bin/" -name "*.sh" -exec chmod +x {} \;

# chmod +x sur les .py uniquement s'ils ont un shebang
for f in "$BASE/bin/"*.py; do
  [ -f "$f" ] || continue
  if head -1 "$f" | grep -q "^#!"; then
    chmod +x "$f"
  fi
done

#################################
# Création dossiers runtime
#################################
echo "[+] Création des dossiers runtime"
mkdir -p "$BASE/logs" "$BASE/mount" "$BASE/quarantine" "$BASE/reports"
chmod 700 "$BASE/logs" "$BASE/quarantine"
chmod 750 "$BASE/mount" "$BASE/reports"

#################################
echo ""
echo "[✓] Installation terminée"
echo "[✓] Station Blanche installée dans $BASE"
echo "[✓] Script principal : $BASE/bin/scan_usb.sh"
