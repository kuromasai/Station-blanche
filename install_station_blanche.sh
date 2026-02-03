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
if ! grep -q "Debian GNU/Linux 13" /etc/os-release; then
  echo "[-] Ce script est prévu pour Debian 13 uniquement"
  exit 1
fi

#################################
# Variables
#################################
BASE="/opt/station-blanche"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

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
# Mise à jour signatures ClamAV
#################################
echo "[+] Mise à jour ClamAV"
systemctl stop clamav-freshclam || true
freshclam
systemctl start clamav-freshclam || true

#################################
# Déploiement Station Blanche
#################################
echo "[+] Déploiement vers /opt"

if [ -d "$BASE" ]; then
  echo "[!] $BASE existe déjà – mise à jour du contenu"
else
  mkdir -p "$BASE"
fi

rsync -a --delete \
  "$REPO_DIR/station-blanche/" \
  "$BASE/"

#################################
# Permissions sécurisées
#################################
echo "[+] Application des permissions"

chown -R root:root "$BASE"
chmod -R 750 "$BASE"

chmod +x "$BASE/bin/"*.sh
chmod +x "$BASE/bin/"*.py

#################################
# Création dossiers runtime (non versionnés)
#################################
echo "[+] Création des dossiers runtime"

mkdir -p "$BASE/logs" "$BASE/mount" "$BASE/quarantine" "$BASE/reports"
chmod 700 "$BASE/logs" "$BASE/quarantine"
chmod 750 "$BASE/mount" "$BASE/reports"

#################################
echo "[✓] Installation terminée"
echo "[✓] Station Blanche installée dans $BASE"
echo "[✓] Script principal : $BASE/bin/scan_usb.sh"
