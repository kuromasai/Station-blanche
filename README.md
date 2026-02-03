<p align="left">
  <img src="assets/logo_station-blanche.png" alt="Project logo" width="150"/>
</p>

# Station Blanche – Analyse de clés USB

Projet de station blanche sous Linux (Debian 13) permettant l’analyse sécurisée
de clés USB provenant de l’extérieur.

##  Objectifs
- Détecter les virus et malwares
- Utiliser ClamAV et YARA
- Corréler les résultats
- Générer un rapport HTML
- Mettre en quarantaine les fichiers infectés
- Fonctionne sur une station isolée (filtrage par URL recommandé sur les Firewall)

##  Architecture
- Scan en lecture seule
- Montage sécurisé (nosuid, nodev, noexec)
- Quarantaine locale
- Rapport horodaté
- Sécurisation conforme aux recommandations ANSSI

##  Outils utilisés
- ClamAV
- YARA (Yara_rules)
- Python 3
- Bash
- Debian 13

##  Utilisation
```bash
sudo scan_usb.sh /dev/sdX1
