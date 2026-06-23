#!/usr/bin/env python3
"""
Station Blanche - Application PyQt5
Interface graphique pour le scan USB sécurisé
"""

import sys
import os
import subprocess
import threading
import glob
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QComboBox,
    QTabWidget, QFrame, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor
from PyQt5.QtWebEngineWidgets import QWebEngineView

BASE = "/opt/station-blanche"
BIN = f"{BASE}/bin"
LOGS = f"{BASE}/logs"
REPORTS = f"{BASE}/reports"
MOUNT = f"{BASE}/mount"
YARA_RULES = f"{BASE}/yara_rules"

STEPS = [
    ("Inventaire",   "list_files.py"),
    ("ClamAV",       None),
    ("YARA",         None),
    ("Parsing ClamAV", "parse_clamav.py"),
    ("Parsing YARA", "parse_yara.py"),
    ("Corrélation",  "correlate.py"),
    ("Quarantaine",  "quarantine.py"),
    ("Rapport",      "generate_report.py"),
]

STYLE = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
}

QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #58a6ff;
    padding: 10px 0px 2px 0px;
    letter-spacing: 1px;
}

QLabel#subtitle {
    font-size: 11px;
    color: #6e7681;
    padding-bottom: 10px;
}

QLabel#section {
    font-size: 11px;
    font-weight: bold;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 2px;
    padding-top: 8px;
}

QLabel#device_label {
    font-size: 13px;
    color: #c9d1d9;
}

QLabel#status_clean {
    font-size: 15px;
    font-weight: bold;
    color: #3fb950;
    padding: 6px;
}
QLabel#status_infected {
    font-size: 15px;
    font-weight: bold;
    color: #f85149;
    padding: 6px;
}
QLabel#status_suspicious {
    font-size: 15px;
    font-weight: bold;
    color: #d29922;
    padding: 6px;
}
QLabel#status_idle {
    font-size: 13px;
    color: #6e7681;
    padding: 6px;
}

QComboBox {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-width: 200px;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
}

QPushButton#btn_scan {
    background-color: #1f6feb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#btn_scan:hover {
    background-color: #388bfd;
}
QPushButton#btn_scan:disabled {
    background-color: #21262d;
    color: #484f58;
}

QPushButton#btn_refresh {
    background-color: #21262d;
    color: #8b949e;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
}
QPushButton#btn_refresh:hover {
    background-color: #30363d;
    color: #c9d1d9;
}

QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #1f6feb;
    border-radius: 4px;
}

QTextEdit {
    background-color: #0d1117;
    color: #8b949e;
    border: 1px solid #21262d;
    border-radius: 6px;
    font-family: 'Monospace';
    font-size: 11px;
    padding: 8px;
}

QTabWidget::pane {
    border: 1px solid #21262d;
    border-radius: 6px;
    background-color: #0d1117;
}
QTabBar::tab {
    background-color: #161b22;
    color: #6e7681;
    border: 1px solid #21262d;
    border-bottom: none;
    padding: 8px 18px;
    font-size: 12px;
    border-radius: 4px 4px 0 0;
}
QTabBar::tab:selected {
    background-color: #0d1117;
    color: #c9d1d9;
    border-color: #30363d;
}

QFrame#separator {
    color: #21262d;
    background-color: #21262d;
    max-height: 1px;
}

QLabel#step_active {
    color: #58a6ff;
    font-size: 12px;
}
QLabel#step_done {
    color: #3fb950;
    font-size: 12px;
}
QLabel#step_idle {
    color: #30363d;
    font-size: 12px;
}
"""


class ScanWorker(QThread):
    log_signal = pyqtSignal(str, str)   # message, level (info/warn/error/ok)
    step_signal = pyqtSignal(int)        # index de l'étape courante
    done_signal = pyqtSignal(str)        # chemin du rapport HTML
    error_signal = pyqtSignal(str)

    def __init__(self, device):
        super().__init__()
        self.device = device

    def emit_log(self, msg, level="info"):
        self.log_signal.emit(msg, level)

    def run_cmd(self, cmd, shell=False):
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, shell=shell
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self.emit_log(line)
            proc.wait()
            return proc.returncode
        except Exception as e:
            self.emit_log(str(e), "error")
            return -1

    def run_python(self, script):
        return self.run_cmd(["python3", f"{BIN}/{script}"])

    def run(self):
        try:
            self._run_scan()
        except Exception as e:
            self.error_signal.emit(str(e))

    def _run_scan(self):
        os.makedirs(LOGS, exist_ok=True)
        os.makedirs(MOUNT, exist_ok=True)
        os.makedirs(REPORTS, exist_ok=True)

        # Nettoyage logs précédents
        for f in glob.glob(f"{LOGS}/*.json") + glob.glob(f"{LOGS}/*.log") + glob.glob(f"{LOGS}/*.exitcode"):
            os.remove(f)

        # Démontage automount existant
        result = subprocess.run(
            ["findmnt", "-n", "-o", "TARGET", "--source", self.device],
            capture_output=True, text=True
        )
        existing = result.stdout.strip()
        if existing:
            self.emit_log(f"[~] Démontage automount : {existing}")
            subprocess.run(["umount", existing])

        # Vérification point de montage
        if os.path.isdir(MOUNT) and os.listdir(MOUNT):
            subprocess.run(["umount", MOUNT], stderr=subprocess.DEVNULL)

        # Montage
        self.emit_log(f"[+] Montage de {self.device} en lecture seule")
        ret = subprocess.run(
            ["mount", "-o", "ro,nosuid,nodev,noexec", self.device, MOUNT]
        ).returncode
        if ret != 0:
            self.error_signal.emit("Échec du montage — vérifiez le périphérique.")
            return

        try:
            self._run_pipeline()
        finally:
            # Démontage garanti
            result = subprocess.run(
                ["mountpoint", "-q", MOUNT], capture_output=True
            )
            if result.returncode == 0:
                self.emit_log("[+] Démontage")
                subprocess.run(["umount", MOUNT])

    def _run_pipeline(self):
        # Étape 0 : Inventaire
        self.step_signal.emit(0)
        self.emit_log("[+] Inventaire des fichiers")
        if self.run_python("list_files.py") != 0:
            self.error_signal.emit("Erreur lors de l'inventaire des fichiers.")
            return

        # Étape 1 : ClamAV
        self.step_signal.emit(1)
        self.emit_log("[+] Scan ClamAV en cours...")
        proc = subprocess.Popen(
            ["clamscan", "-r", "--stdout", MOUNT, f"--log={LOGS}/clamav.log"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                self.emit_log(line)
        proc.wait()
        clam_exit = proc.returncode
        with open(f"{LOGS}/clamav.exitcode", "w") as f:
            f.write(str(clam_exit))
        if clam_exit == 2:
            self.error_signal.emit("ClamAV a rencontré une erreur (code 2).")
            return

        # Étape 2 : YARA
        self.step_signal.emit(2)
        yara_rules = glob.glob(f"{YARA_RULES}/*.yar")
        if not yara_rules:
            self.error_signal.emit(f"Aucune règle YARA trouvée dans {YARA_RULES}/")
            return
        self.emit_log("[+] Scan YARA en cours...")
        with open(f"{LOGS}/yara.log", "w") as ylog:
            proc = subprocess.Popen(
                ["yara", "-r"] + yara_rules + [MOUNT],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    self.emit_log(line)
                    ylog.write(line + "\n")
            proc.wait()
        yara_exit = proc.returncode
        with open(f"{LOGS}/yara.exitcode", "w") as f:
            f.write(str(yara_exit))
        if yara_exit == 1:
            self.emit_log("[!] YARA : correspondances trouvées", "warn")
        elif yara_exit > 1:
            self.error_signal.emit(f"YARA a rencontré une erreur (code {yara_exit}).")
            return

        # Étapes Python restantes
        scripts = [
            (3, "parse_clamav.py", "Parsing ClamAV"),
            (4, "parse_yara.py",   "Parsing YARA"),
            (5, "correlate.py",    "Corrélation"),
            (6, "quarantine.py",   "Quarantaine"),
        ]
        for step_idx, script, label in scripts:
            self.step_signal.emit(step_idx)
            self.emit_log(f"[+] {label}")
            if self.run_python(script) != 0:
                self.error_signal.emit(f"Erreur lors de : {label}")
                return

        # Étape 7 : Rapport
        self.step_signal.emit(7)
        self.emit_log("[+] Génération du rapport")
        if self.run_python("generate_report.py") != 0:
            self.error_signal.emit("Erreur lors de la génération du rapport.")
            return

        # Trouver le rapport le plus récent
        reports = sorted(glob.glob(f"{REPORTS}/report_*.html"))
        if reports:
            self.done_signal.emit(reports[-1])
        else:
            self.error_signal.emit("Rapport introuvable après génération.")


class StationBlanc(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Station Blanche")
        self.setMinimumSize(900, 650)
        self.worker = None
        self.scan_running = False
        self._build_ui()
        self._refresh_devices()

        # Timer de détection USB
        self.usb_timer = QTimer()
        self.usb_timer.timeout.connect(self._auto_detect_usb)
        self.usb_timer.start(2000)
        self._last_devices = set()

    def _build_ui(self):
        self.setStyleSheet(STYLE)
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(0)

        # Header
        title = QLabel("🛡️  Station Blanche")
        title.setObjectName("title")
        root.addWidget(title)

        subtitle = QLabel("Analyse de périphériques USB — usage interne CHU")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)
        root.addSpacing(14)

        # Sélection périphérique
        dev_label = QLabel("PÉRIPHÉRIQUE")
        dev_label.setObjectName("section")
        root.addWidget(dev_label)
        root.addSpacing(6)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(8)

        self.combo = QComboBox()
        dev_row.addWidget(self.combo)

        btn_refresh = QPushButton("↻ Actualiser")
        btn_refresh.setObjectName("btn_refresh")
        btn_refresh.clicked.connect(self._refresh_devices)
        dev_row.addWidget(btn_refresh)

        self.btn_scan = QPushButton("Lancer le scan")
        self.btn_scan.setObjectName("btn_scan")
        self.btn_scan.clicked.connect(self._start_scan)
        dev_row.addWidget(self.btn_scan)

        dev_row.addStretch()
        root.addLayout(dev_row)
        root.addSpacing(16)

        # Étapes de progression
        steps_label = QLabel("PROGRESSION")
        steps_label.setObjectName("section")
        root.addWidget(steps_label)
        root.addSpacing(8)

        self.progress = QProgressBar()
        self.progress.setMaximum(len(STEPS))
        self.progress.setValue(0)
        root.addWidget(self.progress)
        root.addSpacing(6)

        steps_row = QHBoxLayout()
        steps_row.setSpacing(0)
        self.step_labels = []
        for i, (name, _) in enumerate(STEPS):
            lbl = QLabel(name)
            lbl.setObjectName("step_idle")
            lbl.setAlignment(Qt.AlignCenter)
            steps_row.addWidget(lbl)
            self.step_labels.append(lbl)
            if i < len(STEPS) - 1:
                sep_lbl = QLabel("›")
                sep_lbl.setObjectName("step_idle")
                sep_lbl.setAlignment(Qt.AlignCenter)
                steps_row.addWidget(sep_lbl)
        root.addLayout(steps_row)
        root.addSpacing(4)

        # Status
        self.status_label = QLabel("En attente d'un périphérique")
        self.status_label.setObjectName("status_idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_label)
        root.addSpacing(12)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.HLine)
        root.addWidget(sep2)
        root.addSpacing(10)

        # Onglets logs / rapport
        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # Onglet logs
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("log_view")
        self.tabs.addTab(self.log_view, "Logs")

        # Onglet rapport
        self.web_view = QWebEngineView()
        self.web_view.setHtml("<body style='background:#0d1117;color:#6e7681;font-family:sans-serif;padding:40px;text-align:center'><p style='margin-top:80px'>Le rapport apparaîtra ici à la fin du scan.</p></body>")
        self.tabs.addTab(self.web_view, "Rapport")

    def _refresh_devices(self):
        import re
        self.combo.clear()
        try:
            out = subprocess.check_output(
                ["lsblk", "-o", "NAME,TYPE,SIZE,MOUNTPOINT", "-n", "-p"],
                text=True
            )
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "part":
                    # Nettoyer les caractères graphiques d'arbre (└─, ├─, etc.)
                    dev = re.sub(r'^[^\w/]*', '', parts[0])
                    size = parts[2] if len(parts) > 2 else "?"
                    mount = parts[3] if len(parts) > 3 else ""
                    label = f"{dev}  [{size}]"
                    if mount:
                        label += f"  monté sur {mount}"
                    self.combo.addItem(label, dev)
        except Exception as e:
            self.combo.addItem(f"Erreur : {e}")

    def _auto_detect_usb(self):
        if self.scan_running:
            return
        try:
            import re
            out = subprocess.check_output(
                ["lsblk", "-o", "NAME,TYPE,TRAN", "-n", "-p"],
                text=True
            )
            # TRAN est renseigné sur le disque parent (disk), pas sur les partitions.
            # On collecte les disques USB, puis on inclut leurs partitions.
            usb_disks = set()
            usb_parts = set()
            current_disk_is_usb = False
            for line in out.splitlines():
                parts = line.split()
                if not parts:
                    continue
                dev = re.sub(r'^[^\w/]*', '', parts[0])
                typ = parts[1] if len(parts) > 1 else ""
                tran = parts[2] if len(parts) > 2 else ""
                if typ == "disk":
                    current_disk_is_usb = (tran == "usb")
                    if current_disk_is_usb:
                        usb_disks.add(dev)
                elif typ == "part" and current_disk_is_usb:
                    usb_parts.add(dev)
            new_devs = usb_parts - self._last_devices
            if new_devs:
                self._refresh_devices()
                for i in range(self.combo.count()):
                    if self.combo.itemData(i) in new_devs:
                        self.combo.setCurrentIndex(i)
                        break
                self._log("[~] Nouveau périphérique USB détecté — prêt au scan.", "info")
            self._last_devices = usb_parts
        except Exception:
            pass

    def _start_scan(self):
        device = self.combo.currentData()
        if not device:
            QMessageBox.warning(self, "Station Blanche", "Aucun périphérique sélectionné.")
            return

        self.scan_running = True
        self.btn_scan.setEnabled(False)
        self.log_view.clear()
        self.progress.setValue(0)
        self.status_label.setText("Scan en cours…")
        self.status_label.setObjectName("status_idle")
        self.status_label.setStyleSheet("font-size:13px; color:#58a6ff; padding:6px;")
        self.tabs.setCurrentIndex(0)

        for lbl in self.step_labels:
            lbl.setObjectName("step_idle")
            lbl.setStyleSheet("color:#30363d; font-size:12px;")

        self.worker = ScanWorker(device)
        self.worker.log_signal.connect(self._log)
        self.worker.step_signal.connect(self._on_step)
        self.worker.done_signal.connect(self._on_done)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _log(self, msg, level="info"):
        colors = {
            "info":  "#8b949e",
            "ok":    "#3fb950",
            "warn":  "#d29922",
            "error": "#f85149",
        }
        color = colors.get(level, "#8b949e")
        if "[+]" in msg or "[✓]" in msg:
            color = "#3fb950"
        elif "[-]" in msg:
            color = "#f85149"
        elif "[!]" in msg or "[~]" in msg:
            color = "#d29922"

        # Échapper les caractères HTML pour éviter une injection depuis les sorties d'outils
        safe_msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.log_view.append(f'<span style="color:{color}">{safe_msg}</span>')
        self.log_view.moveCursor(QTextCursor.End)

    def _on_step(self, idx):
        # Marquer les étapes précédentes comme terminées
        for i, lbl in enumerate(self.step_labels):
            if i < idx:
                lbl.setStyleSheet("color:#3fb950; font-size:12px;")
            elif i == idx:
                lbl.setStyleSheet("color:#58a6ff; font-size:12px; font-weight:bold;")
            else:
                lbl.setStyleSheet("color:#30363d; font-size:12px;")
        self.progress.setValue(idx)

    def _on_done(self, report_path):
        self.scan_running = False
        self.btn_scan.setEnabled(True)
        self.progress.setValue(len(STEPS))

        for lbl in self.step_labels:
            lbl.setStyleSheet("color:#3fb950; font-size:12px;")

        self._log(f"[✓] Rapport : {report_path}", "ok")

        # Déterminer le verdict depuis le nom du fichier ou lire correlation.json
        verdict = "INCONNU"
        verdict_style = "font-size:15px; font-weight:bold; color:#8b949e; padding:6px;"
        try:
            import json
            with open(f"{LOGS}/correlation.json") as f:
                corr = json.load(f)
            infected = sum(1 for v in corr.values() if v["verdict"] == "INFECTED")
            suspicious = sum(1 for v in corr.values() if v["verdict"] == "SUSPICIOUS")
            if infected:
                verdict = f"⚠ INFECTÉ — {infected} fichier(s)"
                verdict_style = "font-size:15px; font-weight:bold; color:#f85149; padding:6px;"
            elif suspicious:
                verdict = f"⚠ SUSPECT — {suspicious} fichier(s)"
                verdict_style = "font-size:15px; font-weight:bold; color:#d29922; padding:6px;"
            else:
                verdict = "✓ PROPRE"
                verdict_style = "font-size:15px; font-weight:bold; color:#3fb950; padding:6px;"
        except Exception:
            pass

        self.status_label.setText(verdict)
        self.status_label.setStyleSheet(verdict_style)

        # Afficher le rapport dans l'onglet
        self.web_view.load(QUrl.fromLocalFile(report_path))
        self.tabs.setCurrentIndex(1)

    def _on_error(self, msg):
        self.scan_running = False
        self.btn_scan.setEnabled(True)
        self._log(f"[-] ERREUR : {msg}", "error")
        self.status_label.setText("Erreur lors du scan")
        self.status_label.setStyleSheet("font-size:15px; font-weight:bold; color:#f85149; padding:6px;")
        QMessageBox.critical(self, "Erreur — Station Blanche", msg)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("[-] Cette application doit être lancée en root (sudo).")
        sys.exit(1)

    # Désactiver le session manager Qt (erreur XSMP quand lancé en root)
    os.environ["SESSION_MANAGER"] = ""

    sys.argv += ["--no-sandbox"]
    app = QApplication(sys.argv)
    app.setApplicationName("Station Blanche")
    window = StationBlanc()
    window.show()
    sys.exit(app.exec_())
