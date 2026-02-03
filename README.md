# Station-blanche

# 🛡️ Station Blanche – Analyse de clés USB

Projet de station blanche sous Linux (Debian 13) permettant l’analyse sécurisée
de clés USB provenant de l’extérieur.

## 🎯 Objectif
- Détecter les virus et malwares
- Utiliser ClamAV et YARA
- Corréler les résultats
- Générer un rapport HTML
- Mettre en quarantaine les fichiers infectés
- Fonctionner sur une station isolée (sans réseau)

## 🧱 Architecture
- Scan en lecture seule
- Montage sécurisé (nosuid, nodev, noexec)
- Quarantaine locale
- Rapport horodaté
- Approche conforme aux recommandations ANSSI

## 🧪 Outils utilisés
- ClamAV
- YARA
- Python 3
- Bash
- Debian 13

## 🚀 Utilisation
```bash
sudo scan_usb.sh /dev/sdX1
