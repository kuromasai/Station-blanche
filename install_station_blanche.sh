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
REPO_URL="https://github.com/kuromasai/Station-blanche.git"
YARA_RULES_URL="https://github.com/Neo23x0/signature-base.git"
TMP_DIR=$(mktemp -d /tmp/station-blanche-install-XXXXXX)

# Nettoyage du dossier temporaire à la fin quoi qu'il arrive
cleanup() {
  echo "[+] Nettoyage du dossier temporaire"
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

#################################
# Mise à jour système
#################################
echo "[+] Mise à jour système"
apt update && apt upgrade -y

#################################
# Installation dépendances système
#################################
echo "[+] Installation des dépendances"
apt install -y \
  clamav clamav-daemon \
  yara \
  python3 python3-pip \
  python3-pyqt5 \
  python3-pyqt5.qtwebengine \
  libxcb-xinerama0 \
  libxcb-cursor0 \
  git \
  rsync

#################################
# Clone du repo Station Blanche
#################################
echo "[+] Clonage du repo Station Blanche"
git clone "$REPO_URL" "$TMP_DIR/Station-blanche"
SOURCE_DIR="$TMP_DIR/Station-blanche"

#################################
# Dépendances Python (pip)
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
  --exclude='.git' \
  "$SOURCE_DIR/" \
  "$BASE/"

#################################
# Clone des règles YARA signature-base
#################################
echo "[+] Clonage des règles YARA (Neo23x0/signature-base)"
# Supprimer l'ancien dossier si présent (reinstall)
rm -rf "$BASE/yara_rules/signature-base"
git clone "$YARA_RULES_URL" "$BASE/yara_rules/signature-base"

RULES_COUNT=$(find "$BASE/yara_rules/signature-base/yara" -name "*.yar" | wc -l)
echo "[+] $RULES_COUNT fichiers de règles YARA téléchargés"

#################################
# Permissions sécurisées
#################################
echo "[+] Application des permissions"
chown -R root:root "$BASE"
chmod -R 750 "$BASE"

# chmod +x uniquement sur les .sh
find "$BASE/bin/" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true

# chmod +x sur les .py avec shebang
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
echo "[✓] Règles YARA : $BASE/yara_rules/signature-base/yara/"
echo "[✓] Script principal : $BASE/bin/station_blanche.py"
echo ""
echo "[i] Pour lancer depuis la session bureau :"
echo "    sudo DISPLAY=\$DISPLAY XAUTHORITY=\$XAUTHORITY python3 $BASE/bin/station_blanche.py"
