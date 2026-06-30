import sys
import re
import sqlite3
import time
from datetime import datetime
from collections import defaultdict

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QTextEdit, QLabel, QLineEdit, QHBoxLayout, QTabWidget
)
from PyQt6.QtCore import QThread, pyqtSignal


#  CONFIG 
LOG_FILE = "sample_logs.txt"
FAILED_THRESHOLD = 5


#  DATABASE 
def init_db():
    conn = sqlite3.connect("siem.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            type TEXT,
            attempts INTEGER,
            severity TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def insert_alert(alert):
    conn = sqlite3.connect("siem.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO alerts (ip, type, attempts, severity, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (alert["ip"], alert["type"], alert["attempts"], alert["severity"], alert["time"]))
    conn.commit()
    conn.close()


def fetch_alerts(filter_ip=None):
    conn = sqlite3.connect("siem.db")
    c = conn.cursor()

    if filter_ip:
        c.execute("SELECT * FROM alerts WHERE ip LIKE ?", ('%' + filter_ip + '%',))
    else:
        c.execute("SELECT * FROM alerts ORDER BY id DESC")

    rows = c.fetchall()
    conn.close()
    return rows


#  DETECTION ENGINE
FAILED_PATTERN = re.compile(r"Failed password for .* from (\d+\.\d+\.\d+\.\d+)")

def analyze_logs():
    failed = defaultdict(int)

    try:
        with open(LOG_FILE, "r") as f:
            for line in f:
                match = FAILED_PATTERN.search(line)
                if match:
                    ip = match.group(1)
                    failed[ip] += 1
    except FileNotFoundError:
        return []

    alerts = []

    for ip, count in failed.items():
        if count >= FAILED_THRESHOLD:
            alerts.append({
                "ip": ip,
                "type": "Brute Force",
                "attempts": count,
                "severity": "High",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    return alerts


# MONITOR THREAD 
class MonitorThread(QThread):
    alert_signal = pyqtSignal(dict)

    def run(self):
        seen = set()  # avoid duplicate spam

        while True:
            alerts = analyze_logs()

            for alert in alerts:
                key = (alert["ip"], alert["attempts"])
                if key not in seen:
                    seen.add(key)
                    insert_alert(alert)
                    self.alert_signal.emit(alert)

            time.sleep(5)


#  GUI 
class SIEMApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔐 SIEM Pro Dashboard")
        self.setGeometry(200, 200, 900, 600)
        self.setStyleSheet(self.style())

        self.tabs = QTabWidget()
        self.dashboard_tab()
        self.alerts_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.start_monitoring()

    # ---------- Dashboard ---------- #
    def dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        self.stats_label = QLabel("Total Alerts: 0")
        layout.addWidget(self.stats_label)

        refresh_btn = QPushButton("Refresh Stats")
        refresh_btn.clicked.connect(self.update_stats)
        layout.addWidget(refresh_btn)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Dashboard")

    # ---------- Alerts ---------- #
    def alerts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by IP...")

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.load_alerts)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        tab.setLayout(layout)
        self.tabs.addTab(tab, "Alerts")

    # ---------- Monitoring ---------- #
    def start_monitoring(self):
        self.thread = MonitorThread()
        self.thread.alert_signal.connect(self.display_alert)
        self.thread.start()

    # ---------- UI Updates ---------- #
    def display_alert(self, alert):
        self.output.append(
            f"[{alert['severity']}] {alert['type']} → {alert['ip']} ({alert['attempts']} attempts)"
        )
        self.update_stats()

    def load_alerts(self):
        self.output.clear()
        rows = fetch_alerts(self.search_input.text())

        for row in rows:
            _, ip, typ, attempts, severity, timestamp = row
            self.output.append(
                f"[{severity}] {typ} → {ip} ({attempts}) @ {timestamp}"
            )

    def update_stats(self):
        rows = fetch_alerts()
        self.stats_label.setText(f"Total Alerts: {len(rows)}")

    def style(self):
        return """
        QWidget { background:#0f172a; color:#e2e8f0; font-family:Segoe UI; }
        QPushButton { background:#2563eb; padding:6px; border-radius:6px; }
        QPushButton:hover { background:#1d4ed8; }
        QLineEdit { background:#1e293b; padding:6px; border-radius:6px; }
        QTextEdit { background:#020617; border-radius:6px; }
        """


#  RUN 
if __name__ == "__main__":
    init_db()

    app = QApplication(sys.argv)
    window = SIEMApp()
    window.show()
    sys.exit(app.exec())