#!/usr/bin/env python3
"""Schwebendes Hostlist-Fenster fuer RGB Keyboard CheckMK Monitor."""

import json
import os
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

HOSTS_FILE = "/tmp/checkmk_hosts.json"
JUMP_FILE = "/tmp/hostlist_jump.txt"
THEME_FILE = "/tmp/aurenet_theme.txt"

THEMES = ["default", "cyberpunk", "nord", "fire", "ocean", "matrix", "synthwave"]
THEME_COLORS = {
    "default": "#ff0080",
    "cyberpunk": "#00ffff",
    "nord": "#88c0d0",
    "fire": "#ff6400",
    "ocean": "#0096c8",
    "matrix": "#00ff00",
    "synthwave": "#ff00ff",
}

STATE_COLORS = {
    0: "#2ecc71",
    1: "#f39c12",
    2: "#e74c3c",
    3: "#9b59b6",
}

STATE_NAMES = {0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKN"}

ROW_INFO = [
    (12, "Zahlenreihe"),
    (12, "QWERTZ"),
    (12, "ASDF"),
    (11, "YXCV"),
    (12, "F-Tasten"),
    (16, "Numpad"),
    (9, "Sondertasten"),
    (4, "Pfeiltasten"),
]


class HostListWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.host_labels = {}
        self.highlighted_idx = None
        self.scroll = None
        self.current_theme = "default"
        self.theme_buttons = {}

        self.setWindowTitle("CheckMK Hosts")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()
        self.load_hosts()
        self.load_current_theme()

        # Refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.load_hosts)
        self.timer.start(5000)

        # Jump check timer (schneller)
        self.jump_timer = QTimer()
        self.jump_timer.timeout.connect(self.check_jump)
        self.jump_timer.start(100)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 240);
                border-radius: 10px;
                border: 1px solid #444;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)

        # Header mit Titel
        title = QLabel("CheckMK Hosts")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        container_layout.addWidget(title)

        # Theme-Buttons
        theme_frame = QFrame()
        theme_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        theme_layout = QHBoxLayout(theme_frame)
        theme_layout.setContentsMargins(0, 5, 0, 10)
        theme_layout.setSpacing(4)

        theme_label = QLabel("Theme:")
        theme_label.setStyleSheet("color: #888; font-size: 11px;")
        theme_layout.addWidget(theme_label)

        for theme in THEMES:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setToolTip(theme.capitalize())
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME_COLORS[theme]};
                    border: 2px solid #333;
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border: 2px solid #fff;
                }}
            """)
            btn.clicked.connect(lambda checked, t=theme: self.set_theme(t))
            theme_layout.addWidget(btn)
            self.theme_buttons[theme] = btn

        theme_layout.addStretch()
        container_layout.addWidget(theme_frame)

        # Hosts ScrollArea
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: #333; }
            QScrollBar::handle:vertical { background: #666; border-radius: 4px; }
        """)

        self.hosts_widget = QWidget()
        self.hosts_layout = QVBoxLayout(self.hosts_widget)
        self.hosts_layout.setSpacing(2)
        self.scroll.setWidget(self.hosts_widget)
        container_layout.addWidget(self.scroll)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        container_layout.addWidget(self.status_label)

        layout.addWidget(container)
        self.setFixedSize(400, 520)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 420, screen.height() - 570)

    def load_hosts(self):
        self.host_labels = {}

        while self.hosts_layout.count():
            child = self.hosts_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not os.path.exists(HOSTS_FILE):
            self.status_label.setText("Keine Host-Daten")
            return

        try:
            with open(HOSTS_FILE, "r") as f:
                hosts = json.load(f)
        except Exception as e:
            self.status_label.setText(f"Fehler: {e}")
            return

        host_idx = 0
        ok = warn = crit = 0

        for row_size, row_name in ROW_INFO:
            if host_idx >= len(hosts):
                break

            header = QLabel(f"{row_name}")
            header.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 8px;")
            self.hosts_layout.addWidget(header)

            for _ in range(row_size):
                if host_idx >= len(hosts):
                    break

                h = hosts[host_idx]
                state = h.get("state", 0)
                name = h.get("name", "???")[:35]
                color = STATE_COLORS.get(state, "#666")

                if state == 0:
                    ok += 1
                elif state == 1:
                    warn += 1
                elif state == 2:
                    crit += 1

                label = QLabel(f"  {host_idx + 1:2}. {name}")
                label.setStyleSheet(
                    f"color: {color}; font-size: 12px; font-family: monospace;"
                )
                label.setProperty("base_color", color)
                label.setProperty("host_idx", host_idx)
                self.hosts_layout.addWidget(label)
                self.host_labels[host_idx] = label
                host_idx += 1

        self.hosts_layout.addStretch()
        self.status_label.setText(
            f"{len(hosts)} Hosts | OK:{ok} WARN:{warn} CRIT:{crit} | ESC=Schliessen"
        )

    def check_jump(self):
        if not os.path.exists(JUMP_FILE):
            return

        try:
            with open(JUMP_FILE, "r") as f:
                idx = int(f.read().strip())
            os.remove(JUMP_FILE)
            self.jump_to_host(idx)
        except Exception:
            pass

    def jump_to_host(self, idx):
        if idx not in self.host_labels:
            return

        # Altes Highlight entfernen
        if (
            self.highlighted_idx is not None
            and self.highlighted_idx in self.host_labels
        ):
            old_label = self.host_labels[self.highlighted_idx]
            old_color = old_label.property("base_color")
            old_label.setStyleSheet(
                f"color: {old_color}; font-size: 12px; font-family: monospace;"
            )

        # Neues Highlight
        label = self.host_labels[idx]
        label.setStyleSheet(
            "color: #fff; font-size: 12px; font-family: monospace; background: #0078d4; padding: 2px;"
        )
        self.highlighted_idx = idx

        # Zum Label scrollen
        self.scroll.ensureWidgetVisible(label, 50, 50)

        # Highlight nach 2 Sek entfernen
        QTimer.singleShot(2000, lambda: self.remove_highlight(idx))

    def remove_highlight(self, idx):
        if idx in self.host_labels and self.highlighted_idx == idx:
            label = self.host_labels[idx]
            color = label.property("base_color")
            label.setStyleSheet(
                f"color: {color}; font-size: 12px; font-family: monospace;"
            )
            self.highlighted_idx = None

    def load_current_theme(self):
        """Liest aktuelles Theme aus Datei."""
        if os.path.exists(THEME_FILE):
            try:
                with open(THEME_FILE, "r") as f:
                    theme = f.read().strip()
                    if theme in THEMES:
                        self.current_theme = theme
            except Exception:
                pass
        self.update_theme_buttons()

    def set_theme(self, theme):
        """Setzt neues Theme und schreibt es in Datei."""
        self.current_theme = theme
        try:
            with open(THEME_FILE, "w") as f:
                f.write(theme)
        except Exception:
            pass
        self.update_theme_buttons()

    def update_theme_buttons(self):
        """Aktualisiert Button-Styles für aktives Theme."""
        for theme, btn in self.theme_buttons.items():
            if theme == self.current_theme:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {THEME_COLORS[theme]};
                        border: 2px solid #fff;
                        border-radius: 12px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {THEME_COLORS[theme]};
                        border: 2px solid #333;
                        border-radius: 12px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #888;
                    }}
                """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = HostListWindow()
    window.show()
    window.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
