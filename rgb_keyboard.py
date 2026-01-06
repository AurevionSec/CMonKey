#!/usr/bin/env python3
"""
🎹 AURENET - RGB Keyboard CheckMK Monitor
Für Roccat Vulcan AIMO

Features:
- CheckMK Server-Monitoring auf der Tastatur
- 7 Farbthemes (Default, Cyberpunk, Nord, Fire, Ocean, Matrix, Synthwave)
- Reaktive Tastendruck-Wellen (Ripple Effect)
- Rainbow Wave Animation
- Audio Visualizer
- Feuer-Effekt, Matrix Rain, Aurora, Plasma u.v.m.
- Zonenfarben nach Host-Kategorie

Steuerung:
- F1-F8: Effekt wählen
- F9/F10: Geschwindigkeit -/+
- F11/F12: Helligkeit -/+
- RSTRG: Hostliste + Theme-Auswahl (im CheckMK-Modus)
- ESC (lange drücken): Beenden
"""

import time
import math
import random
import threading
import struct
import select
import subprocess
import sys
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


# Theme-Datei für GUI-Kommunikation
THEME_FILE = "/tmp/aurenet_theme.txt"


# ═══════════════════════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    speed: float = 1.0          # Animation Geschwindigkeit (0.1 - 3.0)
    brightness: float = 1.0      # Helligkeit (0.0 - 1.0)
    effect: str = "checkmk"      # Aktiver Effekt - startet mit CheckMK!
    theme: str = "default"       # Aktives Farbtheme
    base_color: Tuple[int, int, int] = (255, 0, 255)  # Basis-Farbe für manche Effekte
    reactive_color: Tuple[int, int, int] = (255, 255, 255)  # Reaktive Farbe


# ═══════════════════════════════════════════════════════════════════════════════
# FARBTHEMES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ColorTheme:
    """Definiert ein Farbschema für Animationen und Status."""
    name: str
    # Animations-Farben (Gradient mit 4-6 Farben)
    gradient: List[Tuple[int, int, int]]
    # Reaktive/Highlight-Farbe
    highlight: Tuple[int, int, int]
    # Status-Farben (OK, WARN, CRIT, UNKNOWN)
    status_ok: Tuple[int, int, int] = (46, 204, 113)
    status_warn: Tuple[int, int, int] = (241, 196, 15)
    status_crit: Tuple[int, int, int] = (231, 76, 60)
    status_unknown: Tuple[int, int, int] = (155, 89, 182)


# Vordefinierte Themes
THEMES: Dict[str, ColorTheme] = {
    "default": ColorTheme(
        name="Default",
        gradient=[(255, 0, 128), (255, 100, 0), (255, 255, 0), (0, 255, 128), (0, 128, 255), (128, 0, 255)],
        highlight=(255, 255, 255),
    ),
    "cyberpunk": ColorTheme(
        name="Cyberpunk",
        gradient=[(255, 0, 128), (0, 255, 255), (255, 0, 255), (0, 255, 128)],
        highlight=(255, 0, 255),
        status_ok=(0, 255, 136),
        status_warn=(255, 170, 0),
        status_crit=(255, 0, 68),
    ),
    "nord": ColorTheme(
        name="Nord",
        gradient=[(94, 129, 172), (136, 192, 208), (163, 190, 140), (235, 203, 139), (191, 97, 106)],
        highlight=(236, 239, 244),
        status_ok=(163, 190, 140),
        status_warn=(235, 203, 139),
        status_crit=(191, 97, 106),
        status_unknown=(180, 142, 173),
    ),
    "fire": ColorTheme(
        name="Fire",
        gradient=[(255, 255, 200), (255, 200, 0), (255, 100, 0), (200, 50, 0), (100, 0, 0)],
        highlight=(255, 255, 200),
        status_ok=(255, 200, 0),
        status_warn=(255, 100, 0),
        status_crit=(200, 0, 0),
    ),
    "ocean": ColorTheme(
        name="Ocean",
        gradient=[(0, 50, 100), (0, 100, 150), (0, 150, 200), (50, 200, 220), (150, 230, 255)],
        highlight=(200, 255, 255),
        status_ok=(0, 200, 150),
        status_warn=(255, 200, 100),
        status_crit=(255, 80, 80),
    ),
    "matrix": ColorTheme(
        name="Matrix",
        gradient=[(0, 50, 0), (0, 100, 0), (0, 180, 0), (0, 255, 0), (150, 255, 150)],
        highlight=(200, 255, 200),
        status_ok=(0, 255, 0),
        status_warn=(200, 255, 0),
        status_crit=(255, 50, 50),
    ),
    "synthwave": ColorTheme(
        name="Synthwave",
        gradient=[(255, 0, 128), (255, 0, 255), (128, 0, 255), (0, 0, 255), (0, 128, 255)],
        highlight=(255, 100, 200),
        status_ok=(0, 255, 200),
        status_warn=(255, 200, 0),
        status_crit=(255, 0, 100),
    ),
}


class ColorProvider:
    """Stellt Theme-basierte Farben für Effekte bereit."""

    def __init__(self, theme_name: str = "default"):
        self.set_theme(theme_name)

    def set_theme(self, theme_name: str):
        """Wechselt das aktive Theme."""
        self.theme = THEMES.get(theme_name, THEMES["default"])
        self._gradient_len = len(self.theme.gradient)

    def get_gradient_color(self, t: float) -> Tuple[int, int, int]:
        """
        Interpoliert durch den Gradient.
        t: 0.0 bis 1.0 (wird zyklisch behandelt)
        """
        t = t % 1.0
        pos = t * (self._gradient_len - 1)
        idx = int(pos)
        frac = pos - idx

        if idx >= self._gradient_len - 1:
            return self.theme.gradient[-1]

        c1 = self.theme.gradient[idx]
        c2 = self.theme.gradient[idx + 1]

        return (
            int(c1[0] + (c2[0] - c1[0]) * frac),
            int(c1[1] + (c2[1] - c1[1]) * frac),
            int(c1[2] + (c2[2] - c1[2]) * frac),
        )

    def get_heat_color(self, heat: float) -> Tuple[int, int, int]:
        """
        Mappt Hitze/Intensität (0.0-1.0) auf Gradient.
        0.0 = erstes Gradient-Element, 1.0 = letztes
        """
        heat = max(0.0, min(1.0, heat))
        return self.get_gradient_color(heat)

    def get_wave_color(self, phase: float, offset: float = 0.0) -> Tuple[int, int, int]:
        """Farbe für Wellen-Animationen (phase + offset zyklisch)."""
        return self.get_gradient_color((phase + offset) % 1.0)

    def get_highlight(self) -> Tuple[int, int, int]:
        """Highlight/Reaktive Farbe."""
        return self.theme.highlight

    def get_status_color(self, state: int) -> Tuple[int, int, int]:
        """Status-Farbe für CheckMK-States (0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN)."""
        if state == 0:
            return self.theme.status_ok
        elif state == 1:
            return self.theme.status_warn
        elif state == 2:
            return self.theme.status_crit
        return self.theme.status_unknown

    def get_gradient_at(self, index: int) -> Tuple[int, int, int]:
        """Direkter Zugriff auf Gradient-Farbe per Index."""
        return self.theme.gradient[index % self._gradient_len]


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class AudioAnalyzer:
    """Analysiert System-Audio für reaktive Effekte via parec."""

    def __init__(self):
        self.bands = [0.0] * 8  # 8 Frequenzbänder
        self.peak = 0.0
        self.bass = 0.0
        self.mid = 0.0
        self.high = 0.0
        self.running = False
        self.process = None
        self.thread = None
        self.history = deque(maxlen=10)

    def start(self):
        """Startet Audio-Capture via parec (PulseAudio/PipeWire)."""
        import subprocess
        import shutil

        if not AUDIO_AVAILABLE:
            print("⚠️ numpy nicht verfügbar")
            return

        if not shutil.which('parec'):
            print("⚠️ parec nicht gefunden")
            return

        try:
            # Finde Monitor-Source
            result = subprocess.run(['pactl', 'list', 'short', 'sources'],
                                    capture_output=True, text=True)
            monitor = None
            for line in result.stdout.strip().split('\n'):
                if '.monitor' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        monitor = parts[1]
                        if 'RUNNING' in line:
                            break  # Bevorzuge aktive Monitore

            if not monitor:
                print("⚠️ Kein Audio-Monitor gefunden")
                return

            print(f"🎵 Monitor: {monitor}")

            # Starte parec für Audio-Capture
            self.process = subprocess.Popen(
                ['parec', '--rate=44100', '--channels=1', '--format=s16le', '-d', monitor],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            self.running = True

            def read_audio():
                CHUNK = 2048
                while self.running and self.process.poll() is None:
                    try:
                        data = self.process.stdout.read(CHUNK * 2)  # 16-bit = 2 bytes
                        if len(data) < CHUNK * 2:
                            continue

                        # Konvertiere zu numpy array
                        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                        # FFT
                        fft = np.abs(np.fft.rfft(audio))
                        freqs = np.fft.rfftfreq(len(audio), 1/44100)

                        # 8 Frequenzbänder
                        band_edges = [20, 60, 150, 400, 1000, 2500, 6000, 12000, 20000]
                        bands = []

                        for i in range(8):
                            mask = (freqs >= band_edges[i]) & (freqs < band_edges[i+1])
                            if np.any(mask):
                                power = np.mean(fft[mask])
                                bands.append(min(1.0, power / 300))
                            else:
                                bands.append(0.0)

                        self.bands = bands
                        self.bass = (bands[0] + bands[1]) / 2
                        self.mid = (bands[2] + bands[3] + bands[4]) / 3
                        self.high = (bands[5] + bands[6] + bands[7]) / 3
                        self.peak = max(bands)
                        self.history.append(self.peak)

                    except Exception:
                        pass

            self.thread = threading.Thread(target=read_audio, daemon=True)
            self.thread.start()
            print("🎵 Audio-Capture gestartet")

        except Exception as e:
            print(f"⚠️ Audio-Fehler: {e}")
            self.running = False

    def stop(self):
        """Stoppt Audio-Capture."""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.wait()

    def get_smoothed_peak(self) -> float:
        """Gibt geglätteten Peak zurück."""
        if not self.history:
            return 0.0
        return sum(self.history) / len(self.history)


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKMK MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class CheckMKMonitor:
    """Holt Host-Status von CheckMK API."""

    def __init__(self, url: str = "http://192.168.10.66:5000/cmk",
                 user: str = "keyboard",
                 secret: str = "GGLXRKQAUDVKCDGDNWGT"):
        self.base_url = url
        self.user = user
        self.secret = secret
        self.hosts = []  # Liste von {'name': str, 'state': int}
        self.last_update = 0
        self.update_interval = 30  # Sekunden
        self.running = False
        self.thread = None
        # Vorheriger Status für Animation-Trigger
        self.previous_states = {}  # {hostname: state}
        # Animationen (hostname -> {'start': timestamp, 'prev_state': int, 'priority': int})
        self.supernovas = {}   # OK/WARN → CRIT
        self.phoenixes = {}    # CRIT/WARN → OK (Recovery)
        self.warnings = {}     # OK → WARN
        self.blackholes = {}   # Host verschwindet (mit key_index für Position)
        self.spawns = {}       # Neuer Host erscheint
        self.known_hosts = set()  # Alle bekannten Hostnamen

    def start(self):
        """Startet den Monitoring-Thread."""
        if not REQUESTS_AVAILABLE:
            print("⚠️ requests nicht verfügbar - CheckMK deaktiviert")
            return

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        print("🔍 CheckMK Monitor gestartet")

    def stop(self):
        """Stoppt den Monitoring-Thread."""
        self.running = False

    def _update_loop(self):
        """Aktualisiert Hosts periodisch."""
        import os
        last_fetch = 0
        while self.running:
            try:
                # Check für Test-Trigger-Dateien (jede Sekunde)
                if os.path.exists('/tmp/trigger_supernova'):
                    os.remove('/tmp/trigger_supernova')
                    if self.hosts:
                        test_host = self.hosts[0]['name']
                        self.supernovas[test_host] = {
                            'start': time.time(),
                            'prev_state': 0,
                            'priority': 0
                        }
                        print(f"💥 TEST-SUPERNOVA: {test_host}")

                if os.path.exists('/tmp/trigger_phoenix'):
                    os.remove('/tmp/trigger_phoenix')
                    if self.hosts:
                        test_host = self.hosts[0]['name']
                        self.phoenixes[test_host] = {
                            'start': time.time(),
                            'prev_state': 2,  # War CRIT
                            'priority': 0
                        }
                        print(f"🔥 TEST-PHOENIX: {test_host}")

                if os.path.exists('/tmp/trigger_warning'):
                    os.remove('/tmp/trigger_warning')
                    if self.hosts:
                        test_host = self.hosts[0]['name']
                        self.warnings[test_host] = {
                            'start': time.time(),
                            'priority': 0
                        }
                        print(f"⚠️ TEST-WARNING: {test_host}")

                if os.path.exists('/tmp/trigger_blackhole'):
                    os.remove('/tmp/trigger_blackhole')
                    if self.hosts:
                        test_host = self.hosts[0]['name']
                        self.blackholes[test_host] = {
                            'start': time.time(),
                            'key_index': 0,  # Erste Taste
                            'priority': 0
                        }
                        print(f"🕳️ TEST-BLACKHOLE: {test_host}")

                if os.path.exists('/tmp/trigger_spawn'):
                    os.remove('/tmp/trigger_spawn')
                    if self.hosts:
                        test_host = self.hosts[0]['name']
                        self.spawns[test_host] = {
                            'start': time.time(),
                            'key_index': 0,  # Erste Taste
                            'priority': 0
                        }
                        print(f"✨ TEST-SPAWN: {test_host}")

                if os.path.exists('/tmp/trigger_hostlist'):
                    os.remove('/tmp/trigger_hostlist')
                    self._print_hostlist()

                if os.path.exists('/tmp/trigger_hostgui'):
                    os.remove('/tmp/trigger_hostgui')
                    subprocess.Popen([
                        sys.executable,
                        os.path.join(os.path.dirname(__file__), 'hostlist_gui.py')
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                # API nur alle 30 Sekunden abfragen
                if time.time() - last_fetch >= self.update_interval:
                    self._fetch_hosts()
                    last_fetch = time.time()

            except Exception as e:
                print(f"⚠️ CheckMK Fehler: {e}")

            time.sleep(0.5)  # Schneller Loop für Trigger-Check

    def _fetch_hosts(self):
        """Holt alle Hosts mit Status von CheckMK."""
        url = f"{self.base_url}/check_mk/api/1.0/domain-types/host/collections/all"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.user} {self.secret}"
        }

        response = requests.get(url, headers=headers, params={"columns": "state"}, timeout=10)
        response.raise_for_status()

        data = response.json()
        now = time.time()

        new_hosts = []
        for h in data.get('value', []):
            name = h.get('id', '')
            state = h.get('extensions', {}).get('state', 0)
            new_hosts.append({'name': name, 'state': state})

            prev_state = self.previous_states.get(name, 0)
            priority = self._get_host_priority(name)

            # SUPERNOVA: Host geht auf CRITICAL (state 2)
            if state == 2 and prev_state != 2:
                self.supernovas[name] = {
                    'start': now,
                    'prev_state': prev_state,
                    'priority': priority
                }
                print(f"💥 SUPERNOVA: {name} geht CRITICAL!")

            # PHOENIX: Host erholt sich zu OK (state 0)
            elif state == 0 and prev_state > 0:
                self.phoenixes[name] = {
                    'start': now,
                    'prev_state': prev_state,
                    'priority': priority
                }
                print(f"🔥 PHOENIX: {name} ist wieder OK!")

            # WARNING: Host geht auf WARN (state 1) von OK
            elif state == 1 and prev_state == 0:
                self.warnings[name] = {
                    'start': now,
                    'priority': priority
                }
                print(f"⚠️ WARNING: {name} hat Probleme!")

            # Update previous state
            self.previous_states[name] = state

        # Sortieren nach Priorität (wichtige zuerst)
        new_hosts = self._sort_by_priority(new_hosts)
        current_names = {h['name'] for h in new_hosts}

        # BLACKHOLE: Host ist verschwunden
        if self.known_hosts:  # Nur wenn wir schon Hosts kennen
            disappeared = self.known_hosts - current_names
            for name in disappeared:
                # Finde alte Position in der sortierten Liste
                old_index = 0
                for i, h in enumerate(self.hosts):
                    if h['name'] == name:
                        old_index = i
                        break
                priority = self._get_host_priority(name)
                self.blackholes[name] = {
                    'start': now,
                    'key_index': old_index,
                    'priority': priority
                }
                print(f"🕳️ BLACKHOLE: {name} ist verschwunden!")
                # Aus previous_states entfernen
                self.previous_states.pop(name, None)

        # SPAWN: Neuer Host erscheint
        if self.known_hosts:  # Nur wenn wir schon Hosts kennen
            new_names = current_names - self.known_hosts
            for name in new_names:
                # Finde neue Position in der sortierten Liste
                new_index = 0
                for i, h in enumerate(new_hosts):
                    if h['name'] == name:
                        new_index = i
                        break
                priority = self._get_host_priority(name)
                self.spawns[name] = {
                    'start': now,
                    'key_index': new_index,
                    'priority': priority
                }
                print(f"✨ SPAWN: {name} ist neu erschienen!")

        # Bekannte Hosts aktualisieren
        self.known_hosts = current_names

        # Alte Animationen aufräumen
        self.supernovas = {k: v for k, v in self.supernovas.items()
                          if now - v['start'] < 14}
        self.phoenixes = {k: v for k, v in self.phoenixes.items()
                         if now - v['start'] < 6}
        self.warnings = {k: v for k, v in self.warnings.items()
                        if now - v['start'] < 4}
        self.blackholes = {k: v for k, v in self.blackholes.items()
                          if now - v['start'] < 5}
        self.spawns = {k: v for k, v in self.spawns.items()
                      if now - v['start'] < 4}

        self.hosts = new_hosts
        self.last_update = now

        # Hosts als JSON exportieren für GUI
        try:
            import json
            with open('/tmp/checkmk_hosts.json', 'w') as f:
                json.dump(new_hosts, f)
        except:
            pass

    def _get_host_priority(self, name: str) -> int:
        """Gibt Priorität zurück (0=wichtigste, höher=unwichtiger)."""
        name_lower = name.lower()
        if 'server' in name_lower or 'srv' in name_lower:
            return 0
        if 'router' in name_lower or 'switch' in name_lower or 'gateway' in name_lower:
            return 1
        if 'nas' in name_lower or 'storage' in name_lower:
            return 2
        if 'proxmox' in name_lower or 'esxi' in name_lower or 'vm' in name_lower:
            return 3
        if 'pi' in name_lower or 'raspberry' in name_lower:
            return 4
        if 'pc' in name_lower or 'desktop' in name_lower or 'workstation' in name_lower:
            return 5
        if 'laptop' in name_lower or 'notebook' in name_lower:
            return 6
        if 'phone' in name_lower or 'iphone' in name_lower or 'android' in name_lower:
            return 8
        if 'ipad' in name_lower or 'tablet' in name_lower:
            return 9
        return 7

    def _get_zone_color(self, name: str) -> tuple:
        """Gibt Zonenfarbe basierend auf Hostname zurück (R, G, B)."""
        name_lower = name.lower()

        # Server/Infrastruktur = Blau
        if 'server' in name_lower or 'srv' in name_lower or 'proxmox' in name_lower or 'esxi' in name_lower:
            return (30, 100, 255)

        # Netzwerk = Cyan
        if 'router' in name_lower or 'switch' in name_lower or 'gateway' in name_lower or 'ap' in name_lower:
            return (0, 200, 200)

        # Storage = Lila
        if 'nas' in name_lower or 'storage' in name_lower or 'backup' in name_lower:
            return (150, 50, 255)

        # Raspberry/IoT = Pink
        if 'pi' in name_lower or 'raspberry' in name_lower or 'esp' in name_lower or 'tapo' in name_lower:
            return (255, 50, 150)

        # PCs/Workstations = Grün
        if 'pc' in name_lower or 'desktop' in name_lower or 'workstation' in name_lower or 'mega' in name_lower:
            return (50, 255, 100)

        # Laptops = Türkis
        if 'laptop' in name_lower or 'notebook' in name_lower:
            return (50, 200, 180)

        # Mobile = Orange
        if 'phone' in name_lower or 'iphone' in name_lower or 'android' in name_lower or 'pixel' in name_lower:
            return (255, 150, 30)

        # Tablets = Gelb-Grün
        if 'ipad' in name_lower or 'tablet' in name_lower or 'pad' in name_lower:
            return (180, 255, 50)

        # Kameras/Security = Rot-Orange
        if 'cam' in name_lower or 'ring' in name_lower or 'security' in name_lower:
            return (255, 80, 50)

        # Smart Home = Warmweiß
        if 'home' in name_lower or 'assistant' in name_lower or 'alexa' in name_lower:
            return (255, 200, 150)

        # Default = Weiß-Grün
        return (100, 220, 100)

    def _print_hostlist(self):
        """Gibt alle Hosts mit Tastenpositionen aus."""
        if not self.hosts:
            print("❌ Keine Hosts geladen")
            return

        # Keyboard-Reihen für Beschreibung
        row_info = [
            (12, "Zahlenreihe (1-0, ß, ´)"),
            (12, "QWERTZ-Reihe"),
            (12, "ASDF-Reihe"),
            (11, "YXCV-Reihe"),
            (12, "F-Tasten (F1-F12)"),
            (16, "Numpad"),
            (9, "Sondertasten (Ins/Home/PgUp...)"),
            (4, "Pfeiltasten"),
        ]

        state_icons = {0: "🟢", 1: "🟡", 2: "🔴", 3: "🟣"}
        state_names = {0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKN"}

        print("\n" + "═" * 70)
        print("🖥️  HOSTLISTE - Tastenbelegung")
        print("═" * 70)

        host_idx = 0
        for row_size, row_name in row_info:
            if host_idx >= len(self.hosts):
                break

            print(f"\n📍 {row_name}:")
            print("-" * 50)

            row_hosts = []
            for i in range(row_size):
                if host_idx >= len(self.hosts):
                    break
                h = self.hosts[host_idx]
                icon = state_icons.get(h['state'], "⚪")
                status = state_names.get(h['state'], "???")
                row_hosts.append(f"  {host_idx+1:3}. {icon} {h['name'][:30]:<30} [{status}]")
                host_idx += 1

            for line in row_hosts:
                print(line)

        print("\n" + "═" * 70)
        print(f"📊 Gesamt: {len(self.hosts)} Hosts | 🟢 OK: {sum(1 for h in self.hosts if h['state']==0)} | "
              f"🟡 WARN: {sum(1 for h in self.hosts if h['state']==1)} | "
              f"🔴 CRIT: {sum(1 for h in self.hosts if h['state']==2)}")
        print("═" * 70 + "\n")

    def _sort_by_priority(self, hosts: List[Dict]) -> List[Dict]:
        """Sortiert Hosts nach Wichtigkeit."""
        def priority(h):
            name = h['name'].lower()
            # Wichtige Keywords = niedrigere Zahl = höhere Priorität
            if 'server' in name or 'srv' in name:
                return 0
            if 'router' in name or 'switch' in name or 'gateway' in name:
                return 1
            if 'nas' in name or 'storage' in name:
                return 2
            if 'proxmox' in name or 'esxi' in name or 'vm' in name:
                return 3
            if 'pi' in name or 'raspberry' in name:
                return 4
            if 'pc' in name or 'desktop' in name or 'workstation' in name:
                return 5
            if 'laptop' in name or 'notebook' in name:
                return 6
            if 'phone' in name or 'iphone' in name or 'android' in name:
                return 8
            if 'ipad' in name or 'tablet' in name:
                return 9
            # Alles andere
            return 7

        return sorted(hosts, key=priority)


# ═══════════════════════════════════════════════════════════════════════════════
# KEYBOARD LAYOUT - Roccat Vulcan Position Mapping
# ═══════════════════════════════════════════════════════════════════════════════

# LED Index zu (X, Y) Position Mapping für Welleneffekte
# Die Positionen sind relativ auf einem Grid
VULCAN_LAYOUT = {
    # Erste Reihe (ESC, F1-F12, etc.)
    0: (0, 0),     # ESC
    9: (2, 0),     # F1
    15: (3, 0),    # F2
    20: (4, 0),    # F3
    24: (5, 0),    # F4
    35: (6.5, 0),  # F5
    40: (7.5, 0),  # F6
    45: (8.5, 0),  # F7
    49: (9.5, 0),  # F8
    54: (11, 0),   # F9
    59: (12, 0),   # F10
    64: (13, 0),   # F11
    68: (14, 0),   # F12
    73: (15.5, 0), # Print
    78: (16.5, 0), # Scroll
    82: (17.5, 0), # Pause

    # Zweite Reihe (Zahlen)
    1: (0, 1),     # `
    6: (1, 1),     # 1
    11: (2, 1),    # 2
    16: (3, 1),    # 3
    21: (4, 1),    # 4
    25: (5, 1),    # 5
    30: (6, 1),    # 6
    36: (7, 1),    # 7
    41: (8, 1),    # 8
    46: (9, 1),    # 9
    50: (10, 1),   # 0
    55: (11, 1),   # -
    60: (12, 1),   # =
    65: (14, 1),   # Backspace
    74: (15.5, 1), # Ins
    79: (16.5, 1), # Home
    83: (17.5, 1), # PgUp
    85: (19, 1),   # NumLock
    89: (20, 1),   # Num /
    93: (21, 1),   # Num *
    96: (22, 1),   # Num -

    # Dritte Reihe (QWERTY)
    2: (0, 2),     # Tab
    10: (1.5, 2),  # Q
    17: (2.5, 2),  # W
    22: (3.5, 2),  # E
    26: (4.5, 2),  # R
    31: (5.5, 2),  # T
    37: (6.5, 2),  # Y
    42: (7.5, 2),  # U
    47: (8.5, 2),  # I
    51: (9.5, 2),  # O
    56: (10.5, 2), # P
    61: (11.5, 2), # [
    66: (12.5, 2), # ]
    75: (15.5, 2), # Del
    80: (16.5, 2), # End
    84: (17.5, 2), # PgDn
    86: (19, 2),   # Num 7
    90: (20, 2),   # Num 8
    94: (21, 2),   # Num 9

    # Vierte Reihe (ASDF)
    3: (0, 3),     # Caps
    12: (1.75, 3), # A
    18: (2.75, 3), # S
    23: (3.75, 3), # D
    27: (4.75, 3), # F
    32: (5.75, 3), # G
    38: (6.75, 3), # H
    43: (7.75, 3), # J
    48: (8.75, 3), # K
    52: (9.75, 3), # L
    57: (10.75, 3),# ;
    62: (11.75, 3),# '
    67: (12.75, 3),# #
    69: (14, 3),   # Enter
    87: (19, 3),   # Num 4
    91: (20, 3),   # Num 5
    95: (21, 3),   # Num 6
    97: (22.5, 3), # Num +

    # Fünfte Reihe (ZXCV)
    4: (0, 4),     # L Shift
    7: (1.25, 4),  # ISO \
    13: (2.25, 4), # Z
    19: (3.25, 4), # X
    28: (4.25, 4), # C
    33: (5.25, 4), # V
    39: (6.25, 4), # B
    44: (7.25, 4), # N
    53: (8.25, 4), # M
    58: (9.25, 4), # ,
    63: (10.25, 4),# .
    70: (11.25, 4),# /
    71: (13.5, 4), # R Shift
    76: (16.5, 4), # Up
    88: (19, 4),   # Num 1
    92: (20, 4),   # Num 2
    98: (21, 4),   # Num 3

    # Sechste Reihe (Space etc.)
    5: (0, 5),     # L Ctrl
    8: (1.5, 5),   # L Win
    14: (3, 5),    # L Alt
    34: (6.5, 5),  # Space
    72: (10, 5),   # R Alt
    77: (11.5, 5), # Fn
    81: (13, 5),   # Menu
    99: (14.5, 5), # R Ctrl
    100: (15.5, 5),# Left
    101: (16.5, 5),# Down
    102: (17.5, 5),# Right
    103: (19.5, 5),# Num 0
    104: (21, 5),  # Num .
    105: (22.5, 5),# Num Enter
}


# ═══════════════════════════════════════════════════════════════════════════════
# FARBHELFER
# ═══════════════════════════════════════════════════════════════════════════════

def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """Konvertiert HSV zu RGB."""
    h = h % 1.0
    if s == 0.0:
        r = g = b = int(v * 255)
        return (r, g, b)

    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    i = i % 6
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else: r, g, b = v, p, q

    return (int(r * 255), int(g * 255), int(b * 255))


def blend_colors(c1: Tuple[int, int, int], c2: Tuple[int, int, int],
                 factor: float) -> Tuple[int, int, int]:
    """Mischt zwei Farben."""
    factor = max(0.0, min(1.0, factor))
    return (
        int(c1[0] * (1 - factor) + c2[0] * factor),
        int(c1[1] * (1 - factor) + c2[1] * factor),
        int(c1[2] * (1 - factor) + c2[2] * factor)
    )


def apply_brightness(color: Tuple[int, int, int], brightness: float) -> RGBColor:
    """Wendet Helligkeit auf eine Farbe an."""
    return RGBColor(
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EFFEKTE
# ═══════════════════════════════════════════════════════════════════════════════

class KeyPress:
    """Speichert einen Tastendruck für Ripple-Effekte."""
    def __init__(self, led_index: int, timestamp: float):
        self.led_index = led_index
        self.timestamp = timestamp
        self.pos = VULCAN_LAYOUT.get(led_index, (0, 0))


class EffectEngine:
    """Haupt-Engine für alle Lichteffekte."""

    def __init__(self, keyboard, num_leds: int, config: Config,
                 audio: AudioAnalyzer = None, checkmk: CheckMKMonitor = None):
        self.keyboard = keyboard
        self.num_leds = num_leds
        self.config = config
        self.audio = audio
        self.checkmk = checkmk
        self.start_time = time.time()
        self.key_presses: deque = deque(maxlen=50)
        self.running = True
        self.led_to_host = {}  # Mapping: LED-Index -> {'name': str, 'state': int}

        # ColorProvider für Theme-basierte Farben
        self.colors = ColorProvider(config.theme)

        # LED-Positionen berechnen
        self.led_positions = {}
        for i in range(num_leds):
            if i in VULCAN_LAYOUT:
                self.led_positions[i] = VULCAN_LAYOUT[i]
            else:
                # Fallback für nicht gemappte LEDs
                self.led_positions[i] = (i % 20, i // 20)

    def add_keypress(self, led_index: int):
        """Fügt einen Tastendruck hinzu."""
        self.key_presses.append(KeyPress(led_index, time.time()))

    def get_elapsed(self) -> float:
        """Gibt die vergangene Zeit zurück."""
        return (time.time() - self.start_time) * self.config.speed

    def set_theme(self, theme_name: str):
        """Wechselt das Farbtheme."""
        if theme_name in THEMES:
            self.config.theme = theme_name
            self.colors.set_theme(theme_name)
            print(f"🎨 Theme: {THEMES[theme_name].name}")
            return True
        return False

    def next_theme(self):
        """Wechselt zum nächsten Theme."""
        theme_list = list(THEMES.keys())
        try:
            idx = theme_list.index(self.config.theme)
            next_idx = (idx + 1) % len(theme_list)
        except ValueError:
            next_idx = 0
        self.set_theme(theme_list[next_idx])

    def check_theme_file(self):
        """Prüft Theme-Datei auf Änderungen (von GUI gesetzt)."""
        import os
        if not os.path.exists(THEME_FILE):
            return
        try:
            with open(THEME_FILE, 'r') as f:
                theme = f.read().strip()
            if theme and theme in THEMES and theme != self.config.theme:
                self.set_theme(theme)
        except Exception as e:
            print(f"Theme check error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Rainbow Wave
    # ─────────────────────────────────────────────────────────────────────────
    def effect_rainbow(self) -> List[RGBColor]:
        """Regenbogen-Welle über die Tastatur."""
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))
            # Welle basierend auf X-Position
            hue = (pos[0] / 20.0 + elapsed * 0.5) % 1.0
            rgb = hsv_to_rgb(hue, 1.0, 1.0)
            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # Reactive Ripple
    # ─────────────────────────────────────────────────────────────────────────
    def effect_reactive(self) -> List[RGBColor]:
        """Reaktive Wellen bei Tastendruck."""
        now = time.time()
        # Theme: Dunkle Basisfarbe vom Gradient-Start
        base = self.colors.get_gradient_at(0)
        base_dim = (base[0] // 10, base[1] // 10, base[2] // 10)
        colors = [apply_brightness(base_dim, self.config.brightness)
                  for _ in range(self.num_leds)]

        # Alte Tastendrücke entfernen
        while self.key_presses and (now - self.key_presses[0].timestamp) > 2.0:
            self.key_presses.popleft()

        # Ripple für jeden aktiven Tastendruck
        for kp in self.key_presses:
            age = (now - kp.timestamp) * self.config.speed * 2
            radius = age * 5  # Wachsende Radius
            fade = max(0, 1 - age / 2)  # Ausblenden über 2 Sekunden

            if fade <= 0:
                continue

            for i in range(self.num_leds):
                pos = self.led_positions.get(i, (0, 0))
                dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)

                # Ring-Effekt
                ring_width = 1.5
                ring_intensity = max(0, 1 - abs(dist - radius) / ring_width)
                ring_intensity *= fade

                if ring_intensity > 0:
                    # Theme: Highlight-Farbe für Reaktion
                    reactive = self.colors.get_highlight()
                    current = (colors[i].red, colors[i].green, colors[i].blue)
                    blended = blend_colors(current, reactive, ring_intensity)
                    colors[i] = apply_brightness(blended, self.config.brightness)

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # Fire Effect
    # ─────────────────────────────────────────────────────────────────────────
    def effect_fire(self) -> List[RGBColor]:
        """Feuer-Effekt von unten nach oben (Theme-basiert)."""
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Basis-Intensität nimmt nach oben ab
            base_heat = max(0, 1 - pos[1] / 6)

            # Flackern
            noise = random.random() * 0.3 + 0.7
            flicker = math.sin(elapsed * 10 + pos[0] * 0.5) * 0.2 + 0.8

            heat = base_heat * noise * flicker

            # Theme: Gradient für Hitze (0=kalt/dunkel, 1=heiß/hell)
            rgb = self.colors.get_heat_color(heat)

            colors.append(apply_brightness(rgb, self.config.brightness * heat))

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # Matrix Rain
    # ─────────────────────────────────────────────────────────────────────────
    def effect_matrix(self) -> List[RGBColor]:
        """Matrix-Style fallender Code (Theme-basiert)."""
        elapsed = self.get_elapsed()
        colors = []
        # Theme: Primärfarbe für Matrix-Regen
        primary = self.colors.get_gradient_at(2)  # Mittlere Gradient-Farbe

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Mehrere "Tropfen" pro Spalte
            intensity = 0
            for drop in range(3):
                drop_speed = 1.5 + drop * 0.5
                drop_offset = drop * 7
                drop_y = ((elapsed * drop_speed + drop_offset + pos[0] * 0.3) % 8) - 2

                dist = abs(pos[1] - drop_y)
                if dist < 1.5:
                    trail_intensity = max(0, 1 - dist / 1.5)
                    intensity = max(intensity, trail_intensity)

            # Zufälliges Flackern
            if random.random() < 0.02:
                intensity = min(1, intensity + 0.5)

            # Theme: Farbe mit Intensität skalieren
            rgb = (int(primary[0] * intensity),
                   int(primary[1] * intensity),
                   int(primary[2] * intensity))
            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # Breathing
    # ─────────────────────────────────────────────────────────────────────────
    def effect_breathing(self) -> List[RGBColor]:
        """Sanftes Atmen mit Theme-Farbe."""
        elapsed = self.get_elapsed()

        # Sinuswelle für sanftes Ein- und Ausatmen
        breath = (math.sin(elapsed * 2) + 1) / 2  # 0 bis 1
        breath = breath ** 2  # Etwas mehr Zeit im dunklen Bereich

        # Theme: Durch Gradient atmen
        rgb = self.colors.get_gradient_color(breath * 0.5)  # Nur halber Gradient
        colors = [apply_brightness(rgb, self.config.brightness * breath * 0.9 + 0.1)
                  for _ in range(self.num_leds)]

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # CPU/RAM Monitor
    # ─────────────────────────────────────────────────────────────────────────
    def effect_system_monitor(self) -> List[RGBColor]:
        """Zeigt CPU/RAM Auslastung als Farben."""
        if not PSUTIL_AVAILABLE:
            return self.effect_rainbow()

        cpu = psutil.cpu_percent() / 100
        ram = psutil.virtual_memory().percent / 100

        colors = []
        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Obere Hälfte = CPU, Untere Hälfte = RAM
            if pos[1] < 3:
                # CPU: Grün -> Gelb -> Rot
                if cpu < 0.5:
                    rgb = blend_colors((0, 255, 0), (255, 255, 0), cpu * 2)
                else:
                    rgb = blend_colors((255, 255, 0), (255, 0, 0), (cpu - 0.5) * 2)
            else:
                # RAM: Blau -> Cyan -> Magenta
                if ram < 0.5:
                    rgb = blend_colors((0, 100, 255), (0, 255, 255), ram * 2)
                else:
                    rgb = blend_colors((0, 255, 255), (255, 0, 255), (ram - 0.5) * 2)

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # Spectrum Wave
    # ─────────────────────────────────────────────────────────────────────────
    def effect_spectrum(self) -> List[RGBColor]:
        """Spektrum-Welle mit mehreren Farben gleichzeitig."""
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Mehrere überlappende Sinuswellen
            wave1 = math.sin(elapsed * 2 + pos[0] * 0.3) * 0.5 + 0.5
            wave2 = math.sin(elapsed * 1.5 + pos[1] * 0.5 + 1) * 0.5 + 0.5
            wave3 = math.sin(elapsed * 2.5 + (pos[0] + pos[1]) * 0.2 + 2) * 0.5 + 0.5

            rgb = (
                int(255 * wave1),
                int(255 * wave2),
                int(255 * wave3)
            )
            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # Starfield
    # ─────────────────────────────────────────────────────────────────────────
    def effect_starfield(self) -> List[RGBColor]:
        """Twinkling Sterne."""
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            # Jede LED hat eigenen Twinkle-Zyklus basierend auf Index
            phase = (i * 0.7 + elapsed * 0.5) % 1.0
            twinkle = abs(math.sin(phase * math.pi * 2))

            # Manche LEDs twinklen schneller
            if i % 5 == 0:
                twinkle = abs(math.sin((phase * 3) * math.pi * 2))

            # Zufällige helle Blitze
            if random.random() < 0.01:
                twinkle = 1.0

            # Leicht bläuliche Sterne
            rgb = (
                int(200 * twinkle + 55),
                int(200 * twinkle + 55),
                int(255 * twinkle)
            )
            colors.append(apply_brightness(rgb, self.config.brightness * twinkle))

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # EXPLOSION - Jeder Tastendruck = fette Farbexplosion
    # ─────────────────────────────────────────────────────────────────────────
    def effect_explosion(self) -> List[RGBColor]:
        """Jeder Tastendruck erzeugt eine fette Farbexplosion."""
        now = time.time()
        colors = [RGBColor(0, 0, 0) for _ in range(self.num_leds)]

        # Alte Tastendrücke entfernen
        while self.key_presses and (now - self.key_presses[0].timestamp) > 1.5:
            self.key_presses.popleft()

        for kp in self.key_presses:
            age = (now - kp.timestamp) * self.config.speed * 3
            # Zufällige Farbe pro Explosion (basierend auf timestamp)
            hue = (kp.timestamp * 3.7) % 1.0

            for i in range(self.num_leds):
                pos = self.led_positions.get(i, (0, 0))
                dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)

                # Expandierende Explosion
                radius = age * 8
                thickness = 2.0 + age * 2

                # Intensität basierend auf Distanz zum Ring
                if dist < radius + thickness:
                    intensity = max(0, 1 - abs(dist - radius) / thickness)
                    intensity *= max(0, 1 - age / 1.5)  # Fade out
                    intensity = intensity ** 0.5  # Weicherer Falloff

                    if intensity > 0:
                        # Farbe mit Shift über Zeit
                        local_hue = (hue + dist * 0.02) % 1.0
                        rgb = hsv_to_rgb(local_hue, 1.0, intensity)
                        # Additive Blending
                        colors[i] = RGBColor(
                            min(255, colors[i].red + int(rgb[0] * self.config.brightness)),
                            min(255, colors[i].green + int(rgb[1] * self.config.brightness)),
                            min(255, colors[i].blue + int(rgb[2] * self.config.brightness))
                        )

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # SNAKE TRAIL - Leuchtende Spur der letzten Tasten
    # ─────────────────────────────────────────────────────────────────────────
    def effect_snake(self) -> List[RGBColor]:
        """Die letzten gedrückten Tasten bilden eine leuchtende Schlange."""
        now = time.time()
        colors = [apply_brightness((10, 0, 20), self.config.brightness * 0.1)
                  for _ in range(self.num_leds)]

        # Behalte die letzten 20 Tastendrücke
        recent = list(self.key_presses)[-20:]

        for idx, kp in enumerate(reversed(recent)):
            age = now - kp.timestamp
            if age > 3.0:
                continue

            # Position in der Schlange (0 = Kopf, 1 = Schwanz)
            snake_pos = idx / max(len(recent), 1)

            # Kopf ist hell, Schwanz dunkler
            intensity = (1 - snake_pos) * max(0, 1 - age / 3.0)

            # Regenbogenfarbe entlang der Schlange
            hue = (snake_pos + now * 0.5) % 1.0
            rgb = hsv_to_rgb(hue, 1.0, 1.0)

            # Die gedrückte Taste und ihre Nachbarn leuchten
            for i in range(self.num_leds):
                pos = self.led_positions.get(i, (0, 0))
                dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)

                if dist < 1.5:
                    glow = (1 - dist / 1.5) * intensity
                    blended = blend_colors(
                        (colors[i].red, colors[i].green, colors[i].blue),
                        rgb, glow
                    )
                    colors[i] = apply_brightness(blended, self.config.brightness)

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # HEATMAP - Häufig gedrückte Tasten werden "heiß"
    # ─────────────────────────────────────────────────────────────────────────
    def effect_heatmap(self) -> List[RGBColor]:
        """Tasten werden heißer je öfter sie gedrückt werden."""
        now = time.time()

        # Heat-Map initialisieren falls nicht vorhanden
        if not hasattr(self, 'heat_values'):
            self.heat_values = [0.0] * self.num_leds

        # Heat abkühlen
        for i in range(self.num_leds):
            self.heat_values[i] = max(0, self.heat_values[i] - 0.01 * self.config.speed)

        # Neue Tastendrücke aufheizen
        for kp in self.key_presses:
            age = now - kp.timestamp
            if age < 0.1:  # Nur ganz frische
                for i in range(self.num_leds):
                    pos = self.led_positions.get(i, (0, 0))
                    dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)
                    if dist < 2:
                        self.heat_values[i] = min(1.0, self.heat_values[i] + 0.3 * (1 - dist/2))

        colors = []
        for i in range(self.num_leds):
            heat = self.heat_values[i]

            # Kalt (blau) -> Warm (rot) -> Heiß (weiß)
            if heat < 0.3:
                rgb = blend_colors((0, 0, 50), (0, 100, 255), heat / 0.3)
            elif heat < 0.6:
                rgb = blend_colors((0, 100, 255), (255, 100, 0), (heat - 0.3) / 0.3)
            elif heat < 0.85:
                rgb = blend_colors((255, 100, 0), (255, 50, 50), (heat - 0.6) / 0.25)
            else:
                rgb = blend_colors((255, 50, 50), (255, 255, 255), (heat - 0.85) / 0.15)

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # COMBO METER - Schnelles Tippen = Intensiveres Leuchten
    # ─────────────────────────────────────────────────────────────────────────
    def effect_combo(self) -> List[RGBColor]:
        """Je schneller du tippst, desto krasser wird's!"""
        now = time.time()
        elapsed = self.get_elapsed()

        # Zähle Tastendrücke der letzten Sekunde
        recent_count = sum(1 for kp in self.key_presses if now - kp.timestamp < 1.0)

        # Combo-Level (0-1) basierend auf Tippgeschwindigkeit
        combo = min(1.0, recent_count / 15)  # 15 keys/sec = max combo

        # Basis-Animation wird intensiver mit Combo
        colors = []
        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Pulsierender Hintergrund
            pulse = (math.sin(elapsed * (2 + combo * 8)) + 1) / 2
            wave = (math.sin(elapsed * 3 + pos[0] * 0.3) + 1) / 2

            # Farbe wird gesättigter und heller mit Combo
            hue = (elapsed * 0.2 + combo * 0.5) % 1.0
            sat = 0.5 + combo * 0.5
            val = 0.2 + combo * 0.6 + pulse * 0.2

            rgb = hsv_to_rgb(hue, sat, val)

            # Bei hoher Combo: Blitzeffekte
            if combo > 0.7 and random.random() < combo * 0.1:
                rgb = (255, 255, 255)

            colors.append(apply_brightness(rgb, self.config.brightness))

        # Reactive Overlays für aktuelle Tastendrücke
        for kp in self.key_presses:
            age = now - kp.timestamp
            if age < 0.3:
                intensity = (1 - age / 0.3) * (0.5 + combo * 0.5)
                for i in range(self.num_leds):
                    pos = self.led_positions.get(i, (0, 0))
                    dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)
                    if dist < 2:
                        glow = intensity * (1 - dist / 2)
                        colors[i] = RGBColor(
                            min(255, colors[i].red + int(255 * glow)),
                            min(255, colors[i].green + int(255 * glow)),
                            min(255, colors[i].blue + int(200 * glow))
                        )

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # SHOCKWAVE - Massive Druckwelle bei jedem Key
    # ─────────────────────────────────────────────────────────────────────────
    def effect_shockwave(self) -> List[RGBColor]:
        """Jeder Tastendruck sendet eine Schockwelle über die ganze Tastatur."""
        now = time.time()
        colors = [RGBColor(5, 0, 10) for _ in range(self.num_leds)]

        while self.key_presses and (now - self.key_presses[0].timestamp) > 2.0:
            self.key_presses.popleft()

        for kp in self.key_presses:
            age = (now - kp.timestamp) * self.config.speed * 2.5
            fade = max(0, 1 - age / 2.0)

            if fade <= 0:
                continue

            # Schnell expandierender Ring
            radius = age * 12

            # Farbe basierend auf Alter
            hue = (kp.timestamp * 2.3 + age * 0.5) % 1.0

            for i in range(self.num_leds):
                pos = self.led_positions.get(i, (0, 0))
                dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)

                # Scharfer Ring mit Nachglühen
                ring_dist = abs(dist - radius)
                if ring_dist < 3:
                    # Hauptring
                    ring_intensity = max(0, 1 - ring_dist / 1.5) * fade
                    # Nachglühen hinter dem Ring
                    if dist < radius:
                        trail = max(0, 1 - (radius - dist) / 5) * fade * 0.3
                        ring_intensity = max(ring_intensity, trail)

                    if ring_intensity > 0:
                        rgb = hsv_to_rgb(hue, 1.0, ring_intensity)
                        colors[i] = RGBColor(
                            min(255, colors[i].red + int(rgb[0] * self.config.brightness)),
                            min(255, colors[i].green + int(rgb[1] * self.config.brightness)),
                            min(255, colors[i].blue + int(rgb[2] * self.config.brightness))
                        )

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # LIGHTNING - Blitze bei Tastendruck
    # ─────────────────────────────────────────────────────────────────────────
    def effect_lightning(self) -> List[RGBColor]:
        """Elektrische Blitze zucken bei jedem Tastendruck."""
        now = time.time()
        elapsed = self.get_elapsed()

        # Dunkler Hintergrund mit subtiler Animation
        colors = []
        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))
            bg = 5 + int(math.sin(elapsed * 0.5 + pos[0] * 0.1) * 3)
            colors.append(RGBColor(bg, bg, int(bg * 1.5)))

        while self.key_presses and (now - self.key_presses[0].timestamp) > 0.5:
            self.key_presses.popleft()

        for kp in self.key_presses:
            age = now - kp.timestamp
            if age > 0.4:
                continue

            # Blitz-Intensität (schneller flash, dann nachlassen)
            if age < 0.05:
                intensity = 1.0
            else:
                intensity = max(0, 1 - (age - 0.05) / 0.35) ** 2

            # Blitz-Pfad: zufällig aber konsistent pro Tastendruck
            random.seed(int(kp.timestamp * 1000))

            # Hauptblitz zur Taste
            for i in range(self.num_leds):
                pos = self.led_positions.get(i, (0, 0))
                dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)

                # Kern-Flash
                if dist < 1:
                    colors[i] = RGBColor(
                        min(255, int(255 * intensity * self.config.brightness)),
                        min(255, int(255 * intensity * self.config.brightness)),
                        min(255, int(255 * intensity * self.config.brightness))
                    )
                # Elektrische Arme (zufällige Verzweigungen)
                elif dist < 6 and random.random() < 0.4 * intensity:
                    arm_intensity = intensity * (1 - dist / 6) * random.random()
                    colors[i] = RGBColor(
                        min(255, colors[i].red + int(150 * arm_intensity * self.config.brightness)),
                        min(255, colors[i].green + int(150 * arm_intensity * self.config.brightness)),
                        min(255, colors[i].blue + int(255 * arm_intensity * self.config.brightness))
                    )

            random.seed()  # Reset random

        return colors

    # ─────────────────────────────────────────────────────────────────────────
    # PLASMA - Organisches reaktives Plasma
    # ─────────────────────────────────────────────────────────────────────────
    def effect_plasma(self) -> List[RGBColor]:
        """Lebendiges Plasma das auf Eingaben reagiert."""
        now = time.time()
        elapsed = self.get_elapsed()

        # Zähle aktive Tastendrücke für Intensität
        active = sum(1 for kp in self.key_presses if now - kp.timestamp < 0.5)
        energy = min(1.0, active / 5)

        colors = []
        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Plasma-Funktion mit mehreren Sinuswellen
            v1 = math.sin(pos[0] * 0.3 + elapsed * 2)
            v2 = math.sin(pos[1] * 0.4 + elapsed * 1.5)
            v3 = math.sin((pos[0] + pos[1]) * 0.2 + elapsed * 2.5)
            v4 = math.sin(math.sqrt(pos[0]**2 + pos[1]**2) * 0.3 + elapsed * 1.8)

            # Kombiniere und normalisiere
            plasma = (v1 + v2 + v3 + v4) / 4

            # Basis-Intensität
            base_intensity = 0.3 + energy * 0.4

            # Farbe basierend auf Plasma-Wert
            hue = (plasma + elapsed * 0.1 + energy * 0.3) % 1.0
            sat = 0.7 + energy * 0.3
            val = base_intensity + (plasma + 1) / 4

            rgb = hsv_to_rgb(hue, sat, val)

            # Boost bei nahen Tastendrücken
            for kp in self.key_presses:
                age = now - kp.timestamp
                if age < 0.8:
                    dist = math.sqrt((pos[0] - kp.pos[0])**2 + (pos[1] - kp.pos[1])**2)
                    if dist < 4:
                        boost = (1 - age / 0.8) * (1 - dist / 4)
                        rgb = blend_colors(rgb, (255, 255, 255), boost * 0.5)

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ═══════════════════════════════════════════════════════════════════════════
    # 🎵 AUDIO-REAKTIVE EFFEKTE
    # ═══════════════════════════════════════════════════════════════════════════

    def effect_audio(self) -> List[RGBColor]:
        """Audio Visualizer - Equalizer über die Tastatur."""
        if not self.audio or not self.audio.running:
            return self.effect_spectrum()

        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # X-Position bestimmt Frequenzband (0-7)
            band_idx = min(7, int(pos[0] / 3))
            band_value = self.audio.bands[band_idx] if band_idx < len(self.audio.bands) else 0

            # Y-Position bestimmt Schwellwert (unten = niedrig, oben = hoch)
            threshold = 1 - (pos[1] / 6)
            lit = band_value > threshold

            if lit:
                # Farbe basierend auf Band (Regenbogen)
                hue = band_idx / 8
                intensity = min(1.0, band_value * 1.5)
                rgb = hsv_to_rgb(hue, 1.0, intensity)
            else:
                # Dunkler Hintergrund
                rgb = (5, 5, 15)

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    def effect_audio_pulse(self) -> List[RGBColor]:
        """Audio Pulse - Ganze Tastatur pulst zum Beat."""
        if not self.audio or not self.audio.running:
            return self.effect_breathing()

        elapsed = self.get_elapsed()
        bass = self.audio.bass
        mid = self.audio.mid
        high = self.audio.high

        colors = []
        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Bass = Rot/Orange von unten
            # Mid = Grün/Cyan von Mitte
            # High = Blau/Violett von oben

            bass_influence = max(0, 1 - pos[1] / 4) * bass * 2
            mid_influence = max(0, 1 - abs(pos[1] - 3) / 3) * mid * 2
            high_influence = max(0, pos[1] / 5) * high * 2

            r = min(255, int(255 * bass_influence + 100 * mid_influence))
            g = min(255, int(200 * mid_influence + 50 * high_influence))
            b = min(255, int(255 * high_influence + 100 * bass_influence))

            colors.append(apply_brightness((r, g, b), self.config.brightness))

        return colors

    def effect_audio_wave(self) -> List[RGBColor]:
        """Audio Wave - Wellen die mit der Musik fließen."""
        if not self.audio or not self.audio.running:
            return self.effect_rainbow()

        elapsed = self.get_elapsed()
        peak = self.audio.get_smoothed_peak()

        colors = []
        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Welle die sich mit Audio-Intensität bewegt
            wave_speed = 1 + peak * 5
            wave = math.sin(elapsed * wave_speed - pos[0] * 0.3)

            # Farbe basierend auf Bass/Mid/High
            hue = (self.audio.bass * 0.1 + elapsed * 0.1) % 1.0
            sat = 0.7 + self.audio.mid * 0.3
            val = 0.2 + (wave + 1) / 2 * 0.5 + peak * 0.3

            rgb = hsv_to_rgb(hue, sat, val)
            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ═══════════════════════════════════════════════════════════════════════════
    # 🌅 SCHÖNE AMBIENT EFFEKTE
    # ═══════════════════════════════════════════════════════════════════════════

    def effect_aurora(self) -> List[RGBColor]:
        """Aurora Borealis - Nordlichter (Theme-basiert)."""
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Mehrere langsame Wellen
            wave1 = math.sin(elapsed * 0.3 + pos[0] * 0.15) * 0.5 + 0.5
            wave2 = math.sin(elapsed * 0.2 + pos[0] * 0.1 + 2) * 0.5 + 0.5
            wave3 = math.sin(elapsed * 0.4 + pos[1] * 0.2) * 0.5 + 0.5

            # Theme: Wellen durch Gradient
            combined = (wave1 + wave2 + wave3) / 3
            rgb = self.colors.get_gradient_color(combined)

            # Vertikaler Fade (unten dunkler)
            fade = 0.3 + (1 - pos[1] / 6) * 0.7

            colors.append(apply_brightness(rgb, self.config.brightness * fade))

        return colors

    def effect_sunset(self) -> List[RGBColor]:
        """Sunset - Warme Sonnenuntergang-Farben."""
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Langsame horizontale Welle
            wave = math.sin(elapsed * 0.2 + pos[0] * 0.1)

            # Gradient von oben nach unten (Himmel -> Horizont)
            height_factor = pos[1] / 6  # 0 oben, 1 unten

            # Oben: Dunkelblau/Lila -> Unten: Orange/Rot
            if height_factor < 0.3:
                base = blend_colors((20, 10, 60), (80, 30, 100), height_factor / 0.3)
            elif height_factor < 0.5:
                base = blend_colors((80, 30, 100), (200, 80, 50), (height_factor - 0.3) / 0.2)
            elif height_factor < 0.7:
                base = blend_colors((200, 80, 50), (255, 150, 30), (height_factor - 0.5) / 0.2)
            else:
                base = blend_colors((255, 150, 30), (255, 200, 100), (height_factor - 0.7) / 0.3)

            # Subtile Wellen-Variation
            variation = (wave + 1) / 2 * 0.2
            rgb = (
                min(255, int(base[0] * (1 + variation))),
                min(255, int(base[1] * (1 + variation * 0.5))),
                min(255, int(base[2] * (1 - variation * 0.3)))
            )

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    def effect_ocean(self) -> List[RGBColor]:
        """Ocean - Beruhigende Ozean-Wellen."""
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Mehrere Wellen mit unterschiedlichen Geschwindigkeiten
            wave1 = math.sin(elapsed * 0.5 + pos[0] * 0.2) * 0.5 + 0.5
            wave2 = math.sin(elapsed * 0.3 + pos[0] * 0.15 + pos[1] * 0.1) * 0.5 + 0.5
            wave3 = math.sin(elapsed * 0.7 + pos[1] * 0.3) * 0.3 + 0.5

            combined = (wave1 + wave2 + wave3) / 3

            # Ozean-Farben: Tiefblau bis Türkis
            rgb = blend_colors((10, 40, 100), (50, 180, 200), combined)

            # Gelegentliche "Schaumkronen"
            if combined > 0.8 and random.random() < 0.02:
                rgb = blend_colors(rgb, (200, 230, 255), 0.5)

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ═══════════════════════════════════════════════════════════════════════════
    # ⏱️ NÜTZLICHE EFFEKTE
    # ═══════════════════════════════════════════════════════════════════════════

    def effect_clock(self) -> List[RGBColor]:
        """Clock - Zeigt die aktuelle Uhrzeit an."""
        now = time.localtime()
        hour = now.tm_hour
        minute = now.tm_min
        second = now.tm_sec

        colors = [RGBColor(5, 5, 10) for _ in range(self.num_leds)]

        # Zahlen-Positionen auf der Tastatur (Zahlenreihe)
        # Wir nutzen die Zahlenreihe für Stunden und Minuten
        hour_tens = hour // 10
        hour_ones = hour % 10
        min_tens = minute // 10
        min_ones = minute % 10

        # LED-Indizes für Zahlenreihe: 1-9, 0
        number_leds = {
            1: 6, 2: 11, 3: 16, 4: 21, 5: 25,
            6: 30, 7: 36, 8: 41, 9: 46, 0: 50
        }

        # Stunden (Cyan)
        if hour_tens in number_leds:
            colors[number_leds[hour_tens]] = apply_brightness((0, 200, 255), self.config.brightness)
        if hour_ones in number_leds:
            colors[number_leds[hour_ones]] = apply_brightness((0, 255, 200), self.config.brightness)

        # Minuten (Magenta) - auf QWERTY Reihe
        qwerty_leds = {1: 10, 2: 17, 3: 22, 4: 26, 5: 31, 6: 37, 7: 42, 8: 47, 9: 51, 0: 56}
        if min_tens in qwerty_leds:
            colors[qwerty_leds[min_tens]] = apply_brightness((255, 0, 200), self.config.brightness)
        if min_ones in qwerty_leds:
            colors[qwerty_leds[min_ones]] = apply_brightness((255, 100, 200), self.config.brightness)

        # Sekunden-Puls (dezent über die ganze Tastatur)
        pulse = (math.sin(second * math.pi / 30) + 1) / 2 * 0.1
        for i in range(self.num_leds):
            if colors[i].red < 20:
                colors[i] = RGBColor(
                    int(10 + pulse * 20),
                    int(10 + pulse * 30),
                    int(20 + pulse * 40)
                )

        return colors

    def effect_pomodoro(self) -> List[RGBColor]:
        """Pomodoro Timer - Visualisiert 25min Arbeits-Zyklen."""
        elapsed = self.get_elapsed()

        # 25 Minuten = 1500 Sekunden pro Zyklus
        cycle_time = 1500
        time_in_cycle = elapsed % cycle_time
        progress = time_in_cycle / cycle_time

        colors = []

        # Fortschritt von links nach rechts über die Tastatur
        max_x = 22  # Ungefähre Tastatur-Breite

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Wie weit ist diese LED im Vergleich zum Fortschritt?
            led_progress = pos[0] / max_x

            if led_progress < progress:
                # Abgeschlossen: Grün
                intensity = 0.8 - (progress - led_progress) * 0.5
                rgb = (0, int(200 * intensity), int(50 * intensity))
            elif led_progress < progress + 0.05:
                # Aktuell: Hell/Weiß
                rgb = (200, 255, 200)
            else:
                # Noch nicht: Dunkelrot
                rgb = (30, 5, 5)

            # Bei 80%+ Fortschritt: Pulsieren als Warnung
            if progress > 0.8:
                pulse = (math.sin(elapsed * 3) + 1) / 2 * 0.3
                rgb = (
                    min(255, int(rgb[0] + 100 * pulse)),
                    rgb[1],
                    rgb[2]
                )

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    def effect_cpu_warning(self) -> List[RGBColor]:
        """CPU Warning - Warnt bei hoher CPU/RAM Auslastung."""
        if not PSUTIL_AVAILABLE:
            return self.effect_breathing()

        cpu = psutil.cpu_percent() / 100
        ram = psutil.virtual_memory().percent / 100
        elapsed = self.get_elapsed()

        colors = []

        # Basis: Ruhiges Grün bei niedrigen Werten
        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # CPU-Bereich (linke Hälfte)
            if pos[0] < 11:
                if cpu < 0.5:
                    rgb = blend_colors((0, 50, 0), (0, 150, 0), cpu * 2)
                elif cpu < 0.8:
                    rgb = blend_colors((0, 150, 0), (200, 200, 0), (cpu - 0.5) / 0.3)
                else:
                    # Kritisch: Pulsierendes Rot
                    pulse = (math.sin(elapsed * 5) + 1) / 2
                    rgb = blend_colors((200, 0, 0), (255, 100, 0), pulse)
            # RAM-Bereich (rechte Hälfte)
            else:
                if ram < 0.5:
                    rgb = blend_colors((0, 0, 50), (0, 100, 150), ram * 2)
                elif ram < 0.8:
                    rgb = blend_colors((0, 100, 150), (200, 100, 200), (ram - 0.5) / 0.3)
                else:
                    # Kritisch: Pulsierendes Magenta
                    pulse = (math.sin(elapsed * 5) + 1) / 2
                    rgb = blend_colors((200, 0, 100), (255, 50, 200), pulse)

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors

    # ═══════════════════════════════════════════════════════════════════════════
    # 🖥️ CHECKMK MONITORING MIT SUPERNOVA
    # ═══════════════════════════════════════════════════════════════════════════

    def effect_checkmk(self) -> List[RGBColor]:
        """CheckMK Monitoring - Jede Taste = ein Host. Mit Supernova-Animation!"""
        if not self.checkmk or not self.checkmk.hosts:
            return self.effect_breathing()

        elapsed = self.get_elapsed()
        now = time.time()
        colors = [RGBColor(5, 5, 5) for _ in range(self.num_leds)]

        # LED-Reihenfolge für Hosts (von links nach rechts, oben nach unten)
        host_leds = [
            # Reihe 1: Zahlen (wichtigste Hosts)
            6, 11, 16, 21, 25, 30, 36, 41, 46, 50, 55, 60,
            # Reihe 2: QWERTZ
            10, 17, 22, 26, 31, 37, 42, 47, 51, 56, 61, 66,
            # Reihe 3: ASDF
            12, 18, 23, 27, 32, 38, 43, 48, 52, 57, 62, 67,
            # Reihe 4: YXCV
            7, 13, 19, 28, 33, 39, 44, 53, 58, 63, 70,
            # F-Tasten
            9, 15, 20, 24, 35, 40, 45, 49, 54, 59, 64, 68,
            # Numpad
            85, 89, 93, 96, 86, 90, 94, 87, 91, 95, 97, 88, 92, 98, 103, 104,
            # Sondertasten
            74, 79, 83, 75, 80, 84, 73, 78, 82,
            # Pfeiltasten
            76, 100, 101, 102,
        ]

        # Mapping: hostname -> (led_index, host_idx)
        host_to_led = {}
        self.led_to_host = {}  # Reset für diesen Frame

        # Normale Host-Farben setzen
        for idx, led in enumerate(host_leds):
            if idx >= len(self.checkmk.hosts):
                colors[led] = RGBColor(2, 2, 2)
                continue

            host = self.checkmk.hosts[idx]
            state = host['state']
            name = host['name']
            host_to_led[name] = (led, idx)
            self.led_to_host[led] = {'name': name, 'state': state, 'idx': idx}

            # Prüfe ob Supernova aktiv
            if name in self.checkmk.supernovas:
                continue  # Wird später behandelt

            # Normale Farben - Theme-basiert!
            if state == 0:
                # OK = Theme-Farbe (statisch)
                status_color = self.colors.get_status_color(0)
                rgb = (int(status_color[0] * 0.85), int(status_color[1] * 0.85), int(status_color[2] * 0.85))
            elif state == 1:
                # WARN = Theme-Farbe (pulsierend)
                pulse = 0.3 + abs(math.sin(elapsed * 3)) * 0.7
                status_color = self.colors.get_status_color(1)
                rgb = (int(status_color[0] * pulse), int(status_color[1] * pulse), int(status_color[2] * pulse))
            elif state == 2:
                # CRIT = Theme-Farbe (schnell pulsierend)
                pulse = 0.2 + abs(math.sin(elapsed * 5)) * 0.8
                status_color = self.colors.get_status_color(2)
                rgb = (int(status_color[0] * pulse), int(status_color[1] * pulse), int(status_color[2] * pulse))
            else:
                # UNKNOWN = Theme-Farbe (pulsierend)
                pulse = 0.3 + abs(math.sin(elapsed * 2.5)) * 0.7
                status_color = self.colors.get_status_color(3)
                rgb = (int(status_color[0] * pulse), int(status_color[1] * pulse), int(status_color[2] * pulse))

            colors[led] = apply_brightness(rgb, self.config.brightness)

        # ═══════════════════════════════════════════════════════════════════
        # 💥 SUPERNOVA ANIMATION
        # ═══════════════════════════════════════════════════════════════════
        for hostname, supernova in self.checkmk.supernovas.items():
            if hostname not in host_to_led:
                continue

            led, host_idx = host_to_led[hostname]
            age = now - supernova['start']
            prev_state = supernova['prev_state']
            priority = supernova['priority']

            # Vorherige Farbe bestimmen
            if prev_state == 0:
                prev_color = (0, 180, 50)  # Grün
            elif prev_state == 1:
                prev_color = (255, 180, 0)  # Gelb
            else:
                prev_color = (150, 50, 200)  # Lila/Unknown

            # ─────────────────────────────────────────────────────────────
            # Phase 1 (0-4s): Pulsieren in vorheriger Farbe, immer schneller
            # ─────────────────────────────────────────────────────────────
            if age < 4.0:
                # Langsam starten, exponentiell schneller werden
                speed = 2 + (age / 4.0) ** 2 * 25  # Von 2 Hz auf 27 Hz
                pulse = 0.3 + abs(math.sin(age * speed * math.pi)) * 0.7
                rgb = (int(prev_color[0] * pulse),
                       int(prev_color[1] * pulse),
                       int(prev_color[2] * pulse))
                colors[led] = apply_brightness(rgb, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 2 (4-5.5s): Fade zu Blau
            # ─────────────────────────────────────────────────────────────
            elif age < 5.5:
                t = (age - 4.0) / 1.5  # 0 -> 1
                blue = (50, 50, 255)
                rgb = blend_colors(prev_color, blue, t)
                colors[led] = apply_brightness(rgb, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 3 (5.5-9s): Blau -> Lila -> Hellblau -> Weiß mit Flicker
            # ─────────────────────────────────────────────────────────────
            elif age < 9.0:
                t = (age - 5.5) / 3.5  # 0 -> 1

                # Farbverlauf
                if t < 0.33:
                    rgb = blend_colors((50, 50, 255), (180, 50, 255), t * 3)  # Blau->Lila
                elif t < 0.66:
                    rgb = blend_colors((180, 50, 255), (150, 200, 255), (t - 0.33) * 3)  # Lila->Hellblau
                else:
                    rgb = blend_colors((150, 200, 255), (255, 255, 255), (t - 0.66) * 3)  # Hellblau->Weiß

                # Flicker - wird schneller und unregelmäßiger
                flicker_speed = 5 + t * 40
                flicker_intensity = 0.1 + t * 0.5
                flicker = 1.0 - random.random() * flicker_intensity * (0.5 + 0.5 * math.sin(age * flicker_speed))

                rgb = (int(rgb[0] * flicker), int(rgb[1] * flicker), int(rgb[2] * flicker))
                colors[led] = apply_brightness(rgb, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 4 (9-9.5s): Kurz bei Weiß verharren
            # ─────────────────────────────────────────────────────────────
            elif age < 9.5:
                colors[led] = apply_brightness((255, 255, 255), self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 5 (9.5-10s): IMPLOSION zu Rot + Nachbarn weiß
            # ─────────────────────────────────────────────────────────────
            elif age < 10.0:
                t = (age - 9.5) / 0.5  # 0 -> 1

                # Haupttaste: Weiß -> Rot
                rgb = blend_colors((255, 255, 255), (255, 0, 0), t)
                colors[led] = apply_brightness(rgb, self.config.brightness)

                # Nachbarn: Mehr Nachbarn bei wichtigeren Systemen
                neighbor_radius = 1 + (9 - min(priority, 9)) * 0.3  # 1.0 bis 3.7
                led_pos = self.led_positions.get(led, (0, 0))

                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 +
                                    (other_pos[1] - led_pos[1])**2)

                    if dist < neighbor_radius:
                        # Nachbar-Intensität
                        neighbor_intensity = (1 - dist / neighbor_radius) * (1 - t)
                        current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                        white_blend = blend_colors(current, (255, 255, 255), neighbor_intensity * 0.8)
                        colors[other_led] = apply_brightness(white_blend, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 6 (10-12.5s): Lila Welle + Host bleibt rot
            # ─────────────────────────────────────────────────────────────
            elif age < 12.5:
                # Host bleibt rot pulsierend
                pulse = 0.7 + math.sin(elapsed * 4) * 0.3
                colors[led] = apply_brightness((int(255 * pulse), 0, 0), self.config.brightness)

                # Lila Welle breitet sich aus
                wave_age = age - 10.0
                wave_radius = wave_age * 8  # Schnelle Ausbreitung
                wave_width = 2.0
                led_pos = self.led_positions.get(led, (0, 0))

                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 +
                                    (other_pos[1] - led_pos[1])**2)

                    # Ring-Effekt
                    ring_dist = abs(dist - wave_radius)
                    if ring_dist < wave_width:
                        wave_intensity = (1 - ring_dist / wave_width) * max(0, 1 - wave_age / 2)
                        if wave_intensity > 0:
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            purple = (200, 100, 255)  # Helllila
                            wave_blend = blend_colors(current, purple, wave_intensity * 0.6)
                            colors[other_led] = apply_brightness(wave_blend, self.config.brightness)

            else:
                # Animation vorbei - normales Rot
                pulse = 0.6 + math.sin(elapsed * 3) * 0.4
                colors[led] = apply_brightness((int(255 * pulse), 0, 0), self.config.brightness)

        # ═══════════════════════════════════════════════════════════════════
        # 🔥 PHOENIX ANIMATION (Recovery: CRIT/WARN → OK)
        # ═══════════════════════════════════════════════════════════════════
        for hostname, phoenix in self.checkmk.phoenixes.items():
            if hostname not in host_to_led:
                continue

            led, host_idx = host_to_led[hostname]
            age = now - phoenix['start']
            prev_state = phoenix['prev_state']
            priority = phoenix['priority']

            # Vorherige Problem-Farbe
            if prev_state == 2:
                problem_color = (255, 0, 0)  # Rot
            else:
                problem_color = (255, 180, 0)  # Gelb/Orange

            led_pos = self.led_positions.get(led, (0, 0))

            # ─────────────────────────────────────────────────────────────
            # Phase 1 (0-0.5s): Kurz hell aufglühen in Problem-Farbe
            # ─────────────────────────────────────────────────────────────
            if age < 0.5:
                flash = 0.5 + age * 1.0  # 0.5 -> 1.0
                rgb = (int(problem_color[0] * flash),
                       int(problem_color[1] * flash),
                       int(problem_color[2] * flash))
                colors[led] = apply_brightness(rgb, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 2 (0.5-2s): "Asche" - Farbe zerfällt nach unten
            # ─────────────────────────────────────────────────────────────
            elif age < 2.0:
                t = (age - 0.5) / 1.5
                # Taste wird dunkler
                fade = max(0, 1 - t * 1.5)
                rgb = (int(problem_color[0] * fade * 0.3),
                       int(problem_color[1] * fade * 0.3),
                       int(problem_color[2] * fade * 0.3))
                colors[led] = apply_brightness(rgb, self.config.brightness)

                # Asche-Partikel fallen nach unten (Nachbar-LEDs unterhalb)
                for other_led in range(self.num_leds):
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dx = abs(other_pos[0] - led_pos[0])
                    dy = other_pos[1] - led_pos[1]  # Positiv = unterhalb

                    if dx < 1.5 and dy > 0 and dy < 2 + t * 2:
                        ash_intensity = (1 - dx / 1.5) * (1 - dy / (2 + t * 2)) * t * (1 - t)
                        if ash_intensity > 0:
                            ash_color = (80, 40, 20)  # Dunkle Asche
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            ash_blend = blend_colors(current, ash_color, ash_intensity * 0.5)
                            colors[other_led] = apply_brightness(ash_blend, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 3 (2-4s): Grüne Flamme steigt von unten auf
            # ─────────────────────────────────────────────────────────────
            elif age < 4.0:
                t = (age - 2.0) / 2.0

                # Grüne Flamme auf der Haupttaste
                flame = 0.3 + t * 0.7
                flicker = 0.8 + random.random() * 0.2
                rgb = (int(50 * flame * flicker),
                       int(255 * flame * flicker),
                       int(80 * flame * flicker))
                colors[led] = apply_brightness(rgb, self.config.brightness)

                # Flammen-Effekt von unten
                for other_led in range(self.num_leds):
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dx = abs(other_pos[0] - led_pos[0])
                    dy = led_pos[1] - other_pos[1]  # Positiv = oberhalb (Flamme steigt)

                    flame_height = t * 3
                    if dx < 1 and dy > 0 and dy < flame_height:
                        flame_intensity = (1 - dx) * (1 - dy / flame_height) * (1 - t * 0.5)
                        flame_flicker = 0.7 + random.random() * 0.3
                        if flame_intensity > 0:
                            flame_color = (100, 255, 100)
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            flame_blend = blend_colors(current, flame_color, flame_intensity * flame_flicker * 0.6)
                            colors[other_led] = apply_brightness(flame_blend, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 4 (4-5.5s): Sanfte grüne Welle breitet sich aus
            # ─────────────────────────────────────────────────────────────
            elif age < 5.5:
                t = (age - 4.0) / 1.5

                # Haupttaste: Stabiles Grün
                pulse = 0.8 + math.sin(elapsed * 2) * 0.2
                colors[led] = apply_brightness((0, int(200 * pulse), int(60 * pulse)), self.config.brightness)

                # Heilungs-Welle
                wave_radius = t * 6
                wave_width = 2.5

                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                    ring_dist = abs(dist - wave_radius)
                    if ring_dist < wave_width:
                        wave_intensity = (1 - ring_dist / wave_width) * max(0, 1 - t * 0.7)
                        if wave_intensity > 0:
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            heal_color = (50, 255, 100)  # Heilgrün
                            wave_blend = blend_colors(current, heal_color, wave_intensity * 0.4)
                            colors[other_led] = apply_brightness(wave_blend, self.config.brightness)

            else:
                # Animation vorbei - normales Grün
                pulse = 0.8 + math.sin(elapsed * 0.5 + host_idx * 0.1) * 0.2
                colors[led] = apply_brightness((0, int(180 * pulse), int(50 * pulse)), self.config.brightness)

        # ═══════════════════════════════════════════════════════════════════
        # ⚠️ WARNING ANIMATION (OK → WARN)
        # ═══════════════════════════════════════════════════════════════════
        for hostname, warning in self.checkmk.warnings.items():
            if hostname not in host_to_led:
                continue

            led, host_idx = host_to_led[hostname]
            age = now - warning['start']
            priority = warning['priority']
            led_pos = self.led_positions.get(led, (0, 0))

            # ─────────────────────────────────────────────────────────────
            # Phase 1 (0-0.3s): Kurzes Flackern
            # ─────────────────────────────────────────────────────────────
            if age < 0.3:
                flicker = random.random()
                if flicker > 0.5:
                    colors[led] = apply_brightness((255, 200, 0), self.config.brightness)
                else:
                    colors[led] = apply_brightness((100, 80, 0), self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 2 (0.3-1.8s): 3x Gelbes Aufblitzen
            # ─────────────────────────────────────────────────────────────
            elif age < 1.8:
                t = (age - 0.3) / 1.5
                # 3 Blitze
                flash_phase = (t * 3) % 1.0
                if flash_phase < 0.4:
                    intensity = flash_phase / 0.4
                else:
                    intensity = max(0, 1 - (flash_phase - 0.4) / 0.6)

                rgb = (int(255 * intensity), int(200 * intensity), 0)
                colors[led] = apply_brightness(rgb, self.config.brightness)

                # Nachbarn flackern orange bei jedem Blitz
                if flash_phase < 0.3:
                    neighbor_radius = 1.5 + (9 - min(priority, 9)) * 0.2
                    for other_led in range(self.num_leds):
                        if other_led == led:
                            continue
                        other_pos = self.led_positions.get(other_led, (0, 0))
                        dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                        if dist < neighbor_radius:
                            neighbor_intensity = (1 - dist / neighbor_radius) * intensity * 0.4
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            orange = (255, 120, 0)
                            neighbor_blend = blend_colors(current, orange, neighbor_intensity)
                            colors[other_led] = apply_brightness(neighbor_blend, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 3 (1.8-3.5s): Kleine gelbe Ringe breiten sich aus
            # ─────────────────────────────────────────────────────────────
            elif age < 3.5:
                t = (age - 1.8) / 1.7

                # Haupttaste: Gelb pulsierend
                pulse = 0.7 + math.sin(age * 4) * 0.3
                colors[led] = apply_brightness((int(255 * pulse), int(180 * pulse), 0), self.config.brightness)

                # 2 Wellen
                for wave_num in range(2):
                    wave_start = wave_num * 0.4
                    if t > wave_start:
                        wave_t = (t - wave_start) / (1.0 - wave_start) if wave_start < 1.0 else 0
                        wave_radius = wave_t * 4
                        wave_width = 1.0

                        for other_led in range(self.num_leds):
                            if other_led == led:
                                continue
                            other_pos = self.led_positions.get(other_led, (0, 0))
                            dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                            ring_dist = abs(dist - wave_radius)
                            if ring_dist < wave_width:
                                wave_intensity = (1 - ring_dist / wave_width) * max(0, 1 - wave_t)
                                if wave_intensity > 0:
                                    current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                                    yellow = (255, 200, 50)
                                    wave_blend = blend_colors(current, yellow, wave_intensity * 0.3)
                                    colors[other_led] = apply_brightness(wave_blend, self.config.brightness)

            else:
                # Animation vorbei - normales Gelb
                pulse = 0.7 + math.sin(elapsed * 2) * 0.3
                colors[led] = apply_brightness((int(255 * pulse), int(180 * pulse), 0), self.config.brightness)

        # ═══════════════════════════════════════════════════════════════════
        # 🕳️ BLACKHOLE ANIMATION (Host verschwindet)
        # ═══════════════════════════════════════════════════════════════════
        for hostname, blackhole in self.checkmk.blackholes.items():
            key_idx = blackhole['key_index']
            if key_idx >= len(host_leds):
                continue

            led = host_leds[key_idx]
            age = now - blackhole['start']
            priority = blackhole['priority']
            led_pos = self.led_positions.get(led, (0, 0))

            # ─────────────────────────────────────────────────────────────
            # Phase 1 (0-1s): Taste flackert und wird dunkler
            # ─────────────────────────────────────────────────────────────
            if age < 1.0:
                t = age / 1.0
                # Flackern mit abnehmendem Licht
                flicker = 1 - t + random.random() * 0.3 * (1 - t)
                # Farbe geht von letztem Status zu dunkel-lila
                rgb = (int(100 * flicker), 0, int(150 * flicker))
                colors[led] = apply_brightness(rgb, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 2 (1-2.5s): Schwarzes Loch saugt Nachbarn an
            # ─────────────────────────────────────────────────────────────
            elif age < 2.5:
                t = (age - 1.0) / 1.5
                # Schwarzes Zentrum
                colors[led] = RGBColor(0, 0, 0)

                # Sog-Effekt auf Nachbarn
                sog_radius = 3 + (9 - min(priority, 9)) * 0.3
                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                    if dist < sog_radius:
                        # Intensität basierend auf Distanz und Zeit
                        sog_intensity = (1 - dist / sog_radius) * t
                        if sog_intensity > 0:
                            # Verdunkeln in Richtung Zentrum
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            dark = (int(current[0] * (1 - sog_intensity * 0.5)),
                                    int(current[1] * (1 - sog_intensity * 0.5)),
                                    int(current[2] * (1 - sog_intensity * 0.5)))
                            colors[other_led] = apply_brightness(dark, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 3 (2.5-3.5s): Implosion - alles kollabiert zum Zentrum
            # ─────────────────────────────────────────────────────────────
            elif age < 3.5:
                t = (age - 2.5) / 1.0
                colors[led] = RGBColor(0, 0, 0)

                # Ring kollabiert nach innen
                ring_radius = (1 - t) * 4
                ring_width = 0.8

                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                    ring_dist = abs(dist - ring_radius)
                    if ring_dist < ring_width:
                        ring_intensity = (1 - ring_dist / ring_width) * (1 - t)
                        if ring_intensity > 0:
                            # Dunkles Lila kollabiert
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            purple = (60, 0, 100)
                            ring_blend = blend_colors(current, purple, ring_intensity * 0.6)
                            colors[other_led] = apply_brightness(ring_blend, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 4 (3.5-5s): Nachrücken - Welle zeigt Verschiebung
            # ─────────────────────────────────────────────────────────────
            elif age < 5.0:
                t = (age - 3.5) / 1.5
                # Welle von rechts nach links (Hosts rücken nach)
                wave_x = led_pos[0] + (1 - t) * 15  # Welle kommt von rechts

                for other_led in range(self.num_leds):
                    other_pos = self.led_positions.get(other_led, (0, 0))

                    # Nur Tasten rechts von der verschwundenen
                    if other_pos[0] > led_pos[0]:
                        wave_dist = abs(other_pos[0] - wave_x)
                        if wave_dist < 1.5:
                            wave_intensity = (1 - wave_dist / 1.5) * 0.5
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            shift_color = (0, 200, 255)  # Cyan für Verschiebung
                            wave_blend = blend_colors(current, shift_color, wave_intensity)
                            colors[other_led] = apply_brightness(wave_blend, self.config.brightness)

        # ═══════════════════════════════════════════════════════════════════
        # ✨ SPAWN ANIMATION (Neuer Host erscheint)
        # ═══════════════════════════════════════════════════════════════════
        for hostname, spawn in self.checkmk.spawns.items():
            key_idx = spawn['key_index']
            if key_idx >= len(host_leds):
                continue

            led = host_leds[key_idx]
            age = now - spawn['start']
            priority = spawn['priority']
            led_pos = self.led_positions.get(led, (0, 0))

            # Host-Status für finale Farbe finden
            final_state = 0
            for h in self.checkmk.hosts:
                if h['name'] == hostname:
                    final_state = h['state']
                    break

            if final_state == 0:
                final_color = (0, 255, 0)  # Grün
            elif final_state == 1:
                final_color = (255, 180, 0)  # Gelb
            else:
                final_color = (255, 0, 0)  # Rot

            # ─────────────────────────────────────────────────────────────
            # Phase 1 (0-0.5s): Funken und weißer Blitz
            # ─────────────────────────────────────────────────────────────
            if age < 0.5:
                t = age / 0.5
                # Weißer Blitz
                flash = 1.0 if random.random() > t * 0.8 else 0.3
                colors[led] = apply_brightness((int(255 * flash), int(255 * flash), int(255 * flash)), self.config.brightness)

                # Funken auf Nachbarn
                spark_radius = 3
                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                    if dist < spark_radius and random.random() > 0.7:
                        spark_intensity = (1 - dist / spark_radius) * random.random()
                        spark_color = (255, 255, 200)  # Gelb-weiß
                        current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                        spark_blend = blend_colors(current, spark_color, spark_intensity * 0.7)
                        colors[other_led] = apply_brightness(spark_blend, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 2 (0.5-2s): Materialisierung - Farbe bildet sich
            # ─────────────────────────────────────────────────────────────
            elif age < 2.0:
                t = (age - 0.5) / 1.5
                # Von Weiß zur finalen Farbe mit Flackern
                flicker = 0.8 + random.random() * 0.2
                blend_t = t * flicker
                rgb = blend_colors((255, 255, 255), final_color, blend_t)
                colors[led] = apply_brightness(rgb, self.config.brightness)

                # Pulsierende Ringe breiten sich aus
                ring_radius = t * 5
                ring_width = 1.2

                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                    ring_dist = abs(dist - ring_radius)
                    if ring_dist < ring_width:
                        ring_intensity = (1 - ring_dist / ring_width) * (1 - t) * 0.4
                        if ring_intensity > 0:
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            ring_color = (200, 255, 200)  # Helles Grün
                            ring_blend = blend_colors(current, ring_color, ring_intensity)
                            colors[other_led] = apply_brightness(ring_blend, self.config.brightness)

            # ─────────────────────────────────────────────────────────────
            # Phase 3 (2-3.5s): Stabilisierung mit Nachleuchten
            # ─────────────────────────────────────────────────────────────
            elif age < 3.5:
                t = (age - 2.0) / 1.5
                # Sanftes Pulsieren in finaler Farbe
                pulse = 0.8 + math.sin(age * 8) * 0.2 * (1 - t)
                rgb = (int(final_color[0] * pulse),
                       int(final_color[1] * pulse),
                       int(final_color[2] * pulse))
                colors[led] = apply_brightness(rgb, self.config.brightness)

                # Leichtes Glühen auf Nachbarn (wird schwächer)
                glow_radius = 2 * (1 - t)
                for other_led in range(self.num_leds):
                    if other_led == led:
                        continue
                    other_pos = self.led_positions.get(other_led, (0, 0))
                    dist = math.sqrt((other_pos[0] - led_pos[0])**2 + (other_pos[1] - led_pos[1])**2)

                    if dist < glow_radius:
                        glow_intensity = (1 - dist / glow_radius) * (1 - t) * 0.2
                        if glow_intensity > 0:
                            current = (colors[other_led].red, colors[other_led].green, colors[other_led].blue)
                            glow_blend = blend_colors(current, final_color, glow_intensity)
                            colors[other_led] = apply_brightness(glow_blend, self.config.brightness)

        # ═══════════════════════════════════════════════════════════════════
        # ESC-Taste: Gesamtstatus
        # ═══════════════════════════════════════════════════════════════════
        problems = sum(1 for h in self.checkmk.hosts if h['state'] > 0)
        critical = sum(1 for h in self.checkmk.hosts if h['state'] == 2)

        if critical > 0:
            # Kritische Hosts: Rot pulsierend
            pulse = 0.5 + abs(math.sin(elapsed * 5)) * 0.5
            colors[0] = apply_brightness((int(255 * pulse), 0, 0), self.config.brightness)
        elif problems > 0:
            # Nur Warnings: Orange
            colors[0] = apply_brightness((255, 150, 0), self.config.brightness)
        else:
            # Alles OK: Grün
            colors[0] = apply_brightness((0, 255, 0), self.config.brightness)

        return colors

    def get_effect_colors(self) -> List[RGBColor]:
        """Gibt die Farben für den aktuellen Effekt zurück."""
        effects = {
            # 🎵 Audio-Reaktiv
            "audio": self.effect_audio,
            "audio_pulse": self.effect_audio_pulse,
            "audio_wave": self.effect_audio_wave,
            # 🌅 Schöne Ambient
            "aurora": self.effect_aurora,
            "sunset": self.effect_sunset,
            "ocean": self.effect_ocean,
            # ⏱️ Nützlich
            "clock": self.effect_clock,
            "pomodoro": self.effect_pomodoro,
            "cpu_warning": self.effect_cpu_warning,
            # 🖥️ Monitoring
            "checkmk": self.effect_checkmk,
            # 💥 Interaktive Effekte
            "explosion": self.effect_explosion,
            "shockwave": self.effect_shockwave,
            "lightning": self.effect_lightning,
            "combo": self.effect_combo,
            "heatmap": self.effect_heatmap,
            "snake": self.effect_snake,
            "plasma": self.effect_plasma,
            "reactive": self.effect_reactive,
            # Alte Effekte (noch verfügbar)
            "rainbow": self.effect_rainbow,
            "fire": self.effect_fire,
            "matrix": self.effect_matrix,
            "breathing": self.effect_breathing,
            "monitor": self.effect_system_monitor,
            "spectrum": self.effect_spectrum,
            "starfield": self.effect_starfield,
        }

        effect_func = effects.get(self.config.effect, self.effect_explosion)
        return effect_func()


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

class InputHandler:
    """Liest Tastatureingaben für reaktive Effekte und Steuerung."""

    # Mapping von evdev Keycodes zu LED-Indizes (vereinfacht)
    KEYCODE_TO_LED = {
        ecodes.KEY_ESC: 0,
        ecodes.KEY_F1: 9, ecodes.KEY_F2: 15, ecodes.KEY_F3: 20, ecodes.KEY_F4: 24,
        ecodes.KEY_F5: 35, ecodes.KEY_F6: 40, ecodes.KEY_F7: 45, ecodes.KEY_F8: 49,
        ecodes.KEY_F9: 54, ecodes.KEY_F10: 59, ecodes.KEY_F11: 64, ecodes.KEY_F12: 68,
        ecodes.KEY_GRAVE: 1, ecodes.KEY_1: 6, ecodes.KEY_2: 11, ecodes.KEY_3: 16,
        ecodes.KEY_4: 21, ecodes.KEY_5: 25, ecodes.KEY_6: 30, ecodes.KEY_7: 36,
        ecodes.KEY_8: 41, ecodes.KEY_9: 46, ecodes.KEY_0: 50, ecodes.KEY_MINUS: 55,
        ecodes.KEY_EQUAL: 60, ecodes.KEY_BACKSPACE: 65,
        ecodes.KEY_TAB: 2, ecodes.KEY_Q: 10, ecodes.KEY_W: 17, ecodes.KEY_E: 22,
        ecodes.KEY_R: 26, ecodes.KEY_T: 31, ecodes.KEY_Y: 37, ecodes.KEY_U: 42,
        ecodes.KEY_I: 47, ecodes.KEY_O: 51, ecodes.KEY_P: 56,
        ecodes.KEY_CAPSLOCK: 3, ecodes.KEY_A: 12, ecodes.KEY_S: 18, ecodes.KEY_D: 23,
        ecodes.KEY_F: 27, ecodes.KEY_G: 32, ecodes.KEY_H: 38, ecodes.KEY_J: 43,
        ecodes.KEY_K: 48, ecodes.KEY_L: 52, ecodes.KEY_ENTER: 69,
        ecodes.KEY_LEFTSHIFT: 4, ecodes.KEY_Z: 13, ecodes.KEY_X: 19, ecodes.KEY_C: 28,
        ecodes.KEY_V: 33, ecodes.KEY_B: 39, ecodes.KEY_N: 44, ecodes.KEY_M: 53,
        ecodes.KEY_RIGHTSHIFT: 71,
        ecodes.KEY_LEFTCTRL: 5, ecodes.KEY_LEFTALT: 14, ecodes.KEY_SPACE: 34,
        ecodes.KEY_RIGHTALT: 72, ecodes.KEY_RIGHTCTRL: 99,
    }

    EFFECT_KEYS = {
        # 🎵 Audio (F1-F3)
        ecodes.KEY_F1: "audio",        # Audio Equalizer
        ecodes.KEY_F2: "audio_pulse",  # Bass-Pulse
        ecodes.KEY_F3: "audio_wave",   # Audio-Wellen
        # 🌅 Schön (F4-F6)
        ecodes.KEY_F4: "aurora",       # Nordlichter
        ecodes.KEY_F5: "sunset",       # Sonnenuntergang
        ecodes.KEY_F6: "ocean",        # Ozean-Wellen
        # ⏱️ Nützlich (F7-F8)
        ecodes.KEY_F7: "clock",        # Uhrzeit-Anzeige
        ecodes.KEY_F8: "checkmk",      # CheckMK Monitoring (Default)
    }

    def __init__(self, config: Config, engine: EffectEngine):
        self.config = config
        self.engine = engine
        self.running = True
        self.devices = []
        self.esc_press_time = None
        self.rctrl_pressed = False  # Rechte STRG für Host-Info Kombi

    def find_keyboards(self) -> List[InputDevice]:
        """Findet ALLE Roccat Vulcan Tastatur-Geräte."""
        keyboards = []
        devices = [InputDevice(path) for path in evdev.list_devices()]

        for device in devices:
            if "roccat" in device.name.lower() or "vulcan" in device.name.lower():
                caps = device.capabilities()
                if ecodes.EV_KEY in caps:
                    # ALLE Roccat-Geräte mit Tasten einbeziehen (für ENDE etc.)
                    keyboards.append(device)
                    print(f"   📥 {device.path}: {device.name}")

        return keyboards

    def handle_key(self, keycode: int, pressed: bool):
        """Verarbeitet einen Tastendruck."""
        if pressed:
            # Effekt-Auswahl mit F1-F8
            if keycode in self.EFFECT_KEYS:
                self.config.effect = self.EFFECT_KEYS[keycode]
                print(f"🎨 Effekt: {self.config.effect}")

            # TEST: Leertaste löst Test-Supernova aus
            elif keycode == ecodes.KEY_SPACE and self.config.effect == "checkmk":
                if hasattr(self.engine, 'checkmk') and self.engine.checkmk:
                    # Simuliere Supernova für ersten Host
                    if self.engine.checkmk.hosts:
                        test_host = self.engine.checkmk.hosts[0]['name']
                        self.engine.checkmk.supernovas[test_host] = {
                            'start': time.time(),
                            'prev_state': 0,  # War grün
                            'priority': 0  # Wichtigster
                        }
                        print(f"💥 TEST-SUPERNOVA: {test_host}")

            # Geschwindigkeit mit F9/F10
            elif keycode == ecodes.KEY_F9:
                self.config.speed = max(0.1, self.config.speed - 0.2)
                print(f"⏱️ Speed: {self.config.speed:.1f}")
            elif keycode == ecodes.KEY_F10:
                self.config.speed = min(3.0, self.config.speed + 0.2)
                print(f"⏱️ Speed: {self.config.speed:.1f}")

            # Helligkeit mit F11/F12
            elif keycode == ecodes.KEY_F11:
                self.config.brightness = max(0.1, self.config.brightness - 0.1)
                print(f"💡 Brightness: {self.config.brightness:.0%}")
            elif keycode == ecodes.KEY_F12:
                self.config.brightness = min(1.0, self.config.brightness + 0.1)
                print(f"💡 Brightness: {self.config.brightness:.0%}")

            # ESC zum Beenden (lange drücken)
            elif keycode == ecodes.KEY_ESC:
                self.esc_press_time = time.time()

            # RSTRG = Hostlist-GUI öffnen (nur im CheckMK-Modus)
            if keycode == ecodes.KEY_RIGHTCTRL and self.config.effect == "checkmk":
                import os
                # Prüfen ob GUI schon läuft
                result = subprocess.run(['pgrep', '-f', 'hostlist_gui.py'], capture_output=True)
                if result.returncode != 0:  # Nicht gefunden = starten
                    subprocess.Popen([
                        sys.executable,
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hostlist_gui.py')
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.rctrl_pressed = True

            # Reaktiver Effekt: LED aufleuchten lassen
            if keycode in self.KEYCODE_TO_LED:
                led_index = self.KEYCODE_TO_LED[keycode]
                self.engine.add_keypress(led_index)

                # RSTRG + Taste = zum Host in GUI springen
                if self.rctrl_pressed and self.config.effect == "checkmk":
                    if led_index in self.engine.led_to_host:
                        host_idx = self.engine.led_to_host[led_index]['idx']
                        with open('/tmp/hostlist_jump.txt', 'w') as f:
                            f.write(str(host_idx))

        else:  # Key released
            if keycode == ecodes.KEY_RIGHTCTRL:
                self.rctrl_pressed = False
            if keycode == ecodes.KEY_ESC and self.esc_press_time:
                if time.time() - self.esc_press_time > 1.0:
                    print("👋 Beende...")
                    self.running = False
                self.esc_press_time = None

    def run(self):
        """Input-Loop - liest von ALLEN Tastatur-Geräten gleichzeitig."""
        if not EVDEV_AVAILABLE:
            print("⚠️ evdev nicht verfügbar - Tasteneingabe deaktiviert")
            while self.running:
                time.sleep(1)
            return

        print("⌨️ Suche Tastatur-Geräte...")
        self.devices = self.find_keyboards()

        if not self.devices:
            print("⚠️ Keine Tastatur gefunden - Tasteneingabe deaktiviert")
            while self.running:
                time.sleep(1)
            return

        print(f"✅ {len(self.devices)} Geräte gefunden")

        # Lese von allen Geräten gleichzeitig mit select
        try:
            fd_to_device = {dev.fd: dev for dev in self.devices}

            while self.running:
                # Warte auf Events von allen Geräten
                r, _, _ = select.select(self.devices, [], [], 0.1)

                for dev in r:
                    try:
                        for event in dev.read():
                            if event.type == ecodes.EV_KEY:
                                key_event = categorize(event)
                                pressed = key_event.keystate in [1, 2]  # 1=down, 2=hold
                                self.handle_key(event.code, pressed)
                    except BlockingIOError:
                        pass
                    except Exception as e:
                        print(f"Read error: {e}")

        except Exception as e:
            print(f"Input error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║   🖥️ RGB TASTATUR - CheckMK Monitoring (Default)                              ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   Jede Taste = ein Host    Grün=OK  Gelb=WARN  Rot=CRIT  ESC=Gesamtstatus    ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   🎵 AUDIO (F1-F3)        🌅 SCHÖN (F4-F6)      ⏱️ NÜTZLICH (F7-F8)           ║
║   F1 = Equalizer          F4 = Aurora           F7 = Uhrzeit                  ║
║   F2 = Bass-Pulse         F5 = Sunset           F8 = CheckMK                  ║
║   F3 = Audio-Wave         F6 = Ocean                                          ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║   F9/F10 = Speed -/+      F11/F12 = Dim/Bright      ESC (1s) = Beenden       ║
║   RSTRG = Hostliste anzeigen                                                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
""")


def main():
    print_banner()

    print("🔌 Verbinde mit OpenRGB...")
    try:
        client = OpenRGBClient()
    except Exception as e:
        print(f"❌ OpenRGB Verbindung fehlgeschlagen: {e}")
        print("   Stelle sicher, dass der OpenRGB Server läuft (openrgb --server)")
        return

    # Finde die Tastatur
    keyboard = None
    for device in client.devices:
        if device.type == DeviceType.KEYBOARD:
            keyboard = device
            break

    if not keyboard:
        print("❌ Keine RGB Tastatur gefunden!")
        return

    print(f"✅ Tastatur gefunden: {keyboard.name}")
    print(f"   LEDs: {len(keyboard.leds)}")

    # Direct Mode aktivieren
    try:
        keyboard.set_mode("Direct")
    except:
        print("⚠️ Direct Mode nicht verfügbar, nutze Standard-Modus")

    # Audio Analyzer starten
    audio = AudioAnalyzer()
    audio.start()

    # CheckMK Monitor starten
    checkmk = CheckMKMonitor()
    checkmk.start()

    # Konfiguration und Engine erstellen
    config = Config()
    engine = EffectEngine(keyboard, len(keyboard.leds), config, audio, checkmk)

    # Input Handler starten
    input_handler = InputHandler(config, engine)
    input_thread = threading.Thread(target=input_handler.run, daemon=True)
    input_thread.start()

    print("\n🚀 CheckMK Monitoring aktiv! F1-F6 für andere Effekte.\n")

    # Haupt-Animations-Loop
    frame_count = 0
    try:
        while input_handler.running:
            colors = engine.get_effect_colors()
            keyboard.set_colors(colors)

            # Theme-Datei alle 30 Frames prüfen (~0.5 Sek)
            frame_count += 1
            if frame_count >= 30:
                engine.check_theme_file()
                frame_count = 0

            time.sleep(1/60)  # ~60 FPS
    except KeyboardInterrupt:
        print("\n👋 Unterbrochen")
    finally:
        # Aufräumen
        audio.stop()
        checkmk.stop()
        try:
            keyboard.set_mode("Default")
        except:
            pass
        print("✨ Fertig!")


if __name__ == "__main__":
    main()
