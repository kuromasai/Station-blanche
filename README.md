
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


                                            ┌───────────────────────────────┐
                                            │        Clé USB externe        │
                                            │  (support provenant extérieur)│
                                            └───────────────┬───────────────┘
                                                            │
                                                            │ Montage sécurisé (lecture seule)
                                                            │ ro / nosuid / nodev / noexec
                                                            ▼
                                            ┌───────────────────────────────┐
                                            │ /opt/station-blanche/mount    │
                                            │  Contenu de la clé USB        │
                                            └───────────────┬───────────────┘
                                                            │
                                                            │ Orchestration
                                                            ▼
                                            ┌───────────────────────────────┐
                                            │         scan_usb.sh           │
                                            │  Script principal             │
                                            └───────────────┬───────────────┘
                                                            │
                                                 ┌──────────┴───────────┐
                                                 │                      │
                                                 ▼                      ▼
                                            ┌───────────────┐    ┌───────────────┐
                                            │  Analyse      │    │  Analyse      │
                                            │  ClamAV       │    │  YARA         │
                                            │               │    │               │
                                            │ clamav.log    │    │ yara.log      │
                                            │ clamav.json   │    │ yara.json     │
                                            └───────────────┘    └───────────────┘
                                                 │                      │
                                                 └──────────┬───────────┘
                                                            ▼
                                            ┌───────────────────────────────┐
                                            │   Corrélation des résultats   │
                                            │        correlate.py           │
                                            │ → correlation.json            │
                                            └───────────────┬───────────────┘
                                                            │
                                                    ┌───────┴────────┐
                                                    │                │
                                                    ▼                ▼
                                            ┌───────────────┐  ┌────────────────┐
                                            │ Quarantaine   │  │ Rapport HTML   │
                                            │ /quarantine   │  │ /reports/      │
                                            │ (fichiers     │  │ report_DATE    │
                                            │ infectés)     │  │ .html          │
                                            └───────────────┘  └────────────────┘



##  Outils utilisés
- ClamAV
- YARA (Yara_rules)
- Python 3
- Bash
- Debian 13

## Installation

```bash
 sudo git clone https://github.com/kuromasai/Station-blanche.git
cd Station-blanche

## Utilisation
```bash
sudo scan_usb.sh /dev/sdX1
