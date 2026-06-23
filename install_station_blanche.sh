#!/bin/bash
set -e

echo "[+] Installation Station Blanche – Debian 13 / GNOME"

#################################
# Vérification root
#################################
if [ "$EUID" -ne 0 ]; then
  echo "[-] Ce script doit être exécuté en root (sudo ./install_station_blanche.sh)"
  exit 1
fi

#################################
# Vérification OS
#################################
if ! grep -q 'VERSION_ID="13"' /etc/os-release 2>/dev/null; then
  echo "[!] Attention : ce script est prévu pour Debian 13"
  read -rp "    Continuer quand même ? (o/N) " confirm
  [[ "$confirm" =~ ^[oO]$ ]] || exit 1
fi

#################################
# Variables
#################################
BASE="/opt/station-blanche"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR="$REPO_DIR"
APP_SCRIPT="station_blanche.py"
ICON_FILE="assets/icon.png"
DESKTOP_FILE="station-blanche.desktop"
APP_NAME="Station Blanche"

#################################
# Vérification source
#################################
if [ ! -f "$SOURCE_DIR/$APP_SCRIPT" ]; then
  echo "[-] Fichier principal introuvable : $SOURCE_DIR/$APP_SCRIPT"
  echo "    Lance ce script depuis la racine du projet."
  exit 1
fi

#################################
# Mise à jour système
#################################
echo "[+] Mise à jour système"
apt update && apt upgrade -y

#################################
# Installation dépendances système
#################################
echo "[+] Installation des dépendances système"
apt install -y \
  clamav clamav-daemon \
  yara \
  python3 python3-pip \
  python3-pyqt6 \
  rsync \
  udev

#################################
# Dépendances Python
#################################
if [ -f "$SOURCE_DIR/requirements.txt" ]; then
  echo "[+] Installation des dépendances Python (requirements.txt)"
  pip3 install --break-system-packages -r "$SOURCE_DIR/requirements.txt"
else
  echo "[+] Installation des dépendances Python (fallback)"
  pip3 install --break-system-packages PyQt6 yara-python
fi

#################################
# Mise à jour signatures ClamAV
#################################
echo "[+] Mise à jour des signatures ClamAV"
systemctl stop clamav-freshclam 2>/dev/null || true
freshclam
systemctl enable --now clamav-freshclam 2>/dev/null || true
systemctl enable --now clamav-daemon 2>/dev/null || true

#################################
# Déploiement dans /opt
#################################
echo "[+] Déploiement vers $BASE"
if [ -d "$BASE" ]; then
  echo "[!] $BASE existe déjà – mise à jour"
else
  mkdir -p "$BASE"
fi

rsync -a --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "$SOURCE_DIR/" \
  "$BASE/"

#################################
# Permissions sécurisées
#################################
echo "[+] Application des permissions"
chown -R root:root "$BASE"
chmod -R 750 "$BASE"
chmod +x "$BASE/$APP_SCRIPT"

# Assets lisibles par tous (icône)
[ -d "$BASE/assets" ] && chmod -R 755 "$BASE/assets"

#################################
# Création dossiers runtime
#################################
echo "[+] Création des dossiers runtime"
mkdir -p "$BASE/logs" "$BASE/mount" "$BASE/quarantine" "$BASE/reports"
chmod 700 "$BASE/logs" "$BASE/quarantine"
chmod 750 "$BASE/mount" "$BASE/reports"

#################################
# Règle udev (détection USB auto)
#################################
echo "[+] Installation de la règle udev"
cat > /etc/udev/rules.d/99-station-blanche.rules << 'EOF'
ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_USAGE}=="filesystem", \
  RUN+="/usr/bin/python3 /opt/station-blanche/station_blanche.py"
EOF
udevadm control --reload-rules 2>/dev/null || true

#################################
# Lanceur GNOME (.desktop)
# Installé pour l'utilisateur qui a lancé sudo
#################################
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo "[+] Création du lanceur GNOME pour $REAL_USER"

# Déterminer le chemin de l'icône
ICON_PATH="$BASE/$ICON_FILE"
if [ ! -f "$ICON_PATH" ]; then
  echo "[!] Icône introuvable ($ICON_PATH) – icône système utilisée"
  ICON_PATH="utilities-terminal"
fi

APPS_DIR="$REAL_HOME/.local/share/applications"
mkdir -p "$APPS_DIR"

cat > "$APPS_DIR/$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Station de décontamination USB
Exec=/usr/bin/python3 $BASE/$APP_SCRIPT
Icon=$ICON_PATH
Terminal=false
Categories=Utility;Security;
StartupNotify=true
EOF

chown "$REAL_USER:$REAL_USER" "$APPS_DIR/$DESKTOP_FILE"
chmod +x "$APPS_DIR/$DESKTOP_FILE"

# Copie sur le bureau (FR et EN)
for BUREAU in "$REAL_HOME/Bureau" "$REAL_HOME/Desktop"; do
  if [ -d "$BUREAU" ]; then
    cp "$APPS_DIR/$DESKTOP_FILE" "$BUREAU/$DESKTOP_FILE"
    chown "$REAL_USER:$REAL_USER" "$BUREAU/$DESKTOP_FILE"
    chmod +x "$BUREAU/$DESKTOP_FILE"
    # Marquer comme approuvé GNOME (évite le warning "untrusted")
    sudo -u "$REAL_USER" gio set "$BUREAU/$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
    echo "[+] Icône ajoutée sur le bureau : $BUREAU"
    break
  fi
done

# Rafraîchir la base des applications
sudo -u "$REAL_USER" update-desktop-database "$APPS_DIR" 2>/dev/null || true

#################################
echo ""
echo "[✓] Installation terminée"
echo "[✓] Station Blanche installée dans : $BASE"
echo "[✓] Application principale       : $BASE/$APP_SCRIPT"
echo "[✓] Lanceur bureau créé pour     : $REAL_USER"
echo ""
echo "    Double-clic sur l'icône 'Station Blanche' pour démarrer."
