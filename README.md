# 🎹 AURENET - Audi RGB Universal Event Network

**Turn your RGB keyboard into a real-time server monitoring dashboard with visual effects.**

Each key represents a host. Colors show status at a glance. Animations alert you to problems. Multiple effect modes from audio visualization to ambient lighting.

![Demo](demo.gif)

[![Tests](https://github.com/your-org/aurenet/workflows/Tests/badge.svg)](https://github.com/your-org/aurenet/actions)
[![Coverage](https://codecov.io/gh/your-org/aurenet/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/aurenet)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

##  Features

- ** Host Monitoring** - Each key = one host from CheckMK
- ** Zone Colors** - Different colors for servers, network, IoT, mobile devices
- ** Supernova Animation** - Explosive effect when host goes critical
- ** Phoenix Animation** - Rising animation when host recovers
- ** Blackhole Animation** - Host disappears from monitoring
- ** Spawn Animation** - New host detected
- ** Warning Pulse** - Yellow pulsing for warning state
- ** GUI Hostlist** - Press Right-CTRL to see all hosts
- ** Audio Visualizer** - Alternative mode with music reactive lighting

##  Animations

| State Change | Animation | Description |
|--------------|-----------|-------------|
| OK → CRITICAL |  Supernova | Bright explosion, shockwave spreads |
| CRITICAL → OK |  Phoenix | Green flames rising |
| OK → WARNING |  Warning | Yellow pulse begins |
| Host disappears |  Blackhole | Implodes to darkness |
| New host |  Spawn | Sparkle effect |

## 🤖 Developer Notifications

Visual feedback for development workflows:

| Trigger | Animation | Color | Usage |
|---------|-----------|-------|-------|
| Claude Code Task Complete | 🟠 Orange Fade + Blink | Orange | `./trigger_task_complete.sh` |
| Codex Review Complete | 🔵 White-Blue Fade + Blink | Cyan | `./trigger_codex_complete.sh` |

**Animation Sequence:**
1. Fade from current colors to notification color (1.25s)
2. Blink 2x between notification color and previous (1s)
3. Fade back to previous colors (1.25s)
4. Total duration: ~3.5 seconds

**Integration Examples:**

```bash
# After task completion
./trigger_task_complete.sh

# After code review
codex review --uncommitted && ./trigger_codex_complete.sh

# Hook into CI/CD
echo "✅" > /tmp/aurenet_task_complete.txt
```

## Zone Colors

Hosts are colored by category:

| Category | Color | Keywords |
|----------|-------|----------|
| Servers | 🔵 Blue | server, srv, proxmox, esxi |
| Network | 🩵 Cyan | router, switch, gateway |
| Storage | 🟣 Purple | nas, storage, backup |
| Raspberry/IoT | 🩷 Pink | pi, raspberry, esp, tapo |
| Workstations | 🟢 Green | pc, desktop, workstation |
| Laptops | 🩵 Teal | laptop, notebook |
| Mobile | 🟠 Orange | phone, iphone, android |
| Cameras | 🔴 Red-Orange | cam, ring, security |
| Smart Home | ⬜ Warm White | home, assistant |

## 📁 Project Structure

```
aurenet/
├── aurenet/                     # Main package
│   ├── core/                    # Core components
│   │   ├── events.py           # Event bus system
│   │   ├── orchestrator.py     # Application coordinator
│   │   ├── shutdown.py         # Graceful shutdown
│   │   └── types.py            # Shared types
│   ├── config/                  # Configuration
│   │   ├── settings.py         # App settings
│   │   └── themes.py           # Color themes
│   ├── input/                   # Keyboard input
│   │   ├── handler.py          # Input handling
│   │   └── keyboard_mapping.py # Key mappings
│   ├── effects/                 # Visual effects
│   │   ├── base.py             # Effect interface
│   │   ├── audio/              # Audio visualizers
│   │   ├── ambient/            # Ambient effects
│   │   ├── interactive/        # Interactive effects
│   │   └── monitoring/         # Monitoring effects
│   ├── monitoring/              # External monitoring
│   │   ├── base.py             # Provider interface
│   │   └── checkmk.py          # CheckMK integration
│   ├── output/                  # LED output
│   │   ├── renderer.py         # Color rendering
│   │   └── hardware.py         # OpenRGB interface
│   └── infrastructure/          # External dependencies
│       ├── filesystem.py       # File operations
│       ├── http.py             # HTTP client
│       └── triggers.py         # Trigger files
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests (91 tests)
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test fixtures
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md         # Architecture overview
│   └── TESTING.md              # Testing guide
├── .github/workflows/           # CI/CD
│   └── test.yml                # GitHub Actions
├── rgb_keyboard.py              # Main entry point
└── README.md                    # This file
```

## 🏗️ Architecture

AURENET follows **event-driven hexagonal architecture**:

- **Event Bus:** All components communicate via publish-subscribe events
- **Dependency Injection:** Abstract interfaces, mockable dependencies
- **Thread Safety:** All shared state protected with locks
- **Graceful Shutdown:** LIFO shutdown order with error isolation

Key components:
- **Input Handler:** evdev keyboard monitoring → publishes KEY_PRESSED events
- **Effect Orchestrator:** Subscribes to events → updates configuration
- **CheckMK Monitor:** Background thread → polls API → publishes MONITORING_UPDATE
- **Effect Renderer:** Combines state → renders colors → sends to hardware

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## 💻 Development

### Setup

```bash
# Clone repository
git clone https://github.com/your-org/aurenet.git
cd aurenet

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest aurenet/tests/ --cov=aurenet

# Run linter
ruff check aurenet/

# Run type checker
mypy aurenet/ --ignore-missing-imports
```

### Running Tests

```bash
# All tests
pytest aurenet/tests/

# Unit tests only
pytest aurenet/tests/unit/ -v

# With coverage
pytest aurenet/tests/ --cov=aurenet --cov-report=html

# Specific test
pytest aurenet/tests/unit/test_events.py::TestEventBus::test_subscribe_and_publish -v
```

See [docs/TESTING.md](docs/TESTING.md) for testing guide.

### Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest aurenet/tests/`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

**Code Quality:**
- >75% test coverage required
- ruff linting must pass
- Type hints for public APIs
- Docstrings for modules and classes

## Requirements

- **Keyboard**: Roccat Vulcan AIMO (other OpenRGB keyboards may work)
- **OS**: Linux (tested on Arch/Hyprland)
- **Monitoring**: CheckMK instance with API access
- **Software**: OpenRGB server running
- **Python**: 3.10 or higher

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/aurenet.git
cd aurenet

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# Or manually:
# pip install openrgb-python requests evdev

# Start OpenRGB server (in another terminal)
openrgb --server

# Configure CheckMK credentials
export CHECKMK_URL="http://your-checkmk-server:5000"
export CHECKMK_USER="automation"
export CHECKMK_SECRET="your-api-secret"

# Run
python3 rgb_keyboard.py
```

## Configuration

Edit the CheckMK settings in `rgb_keyboard.py`:

```python
CHECKMK_URL = "http://192.168.10.66:5000"
CHECKMK_USER = "automation"
CHECKMK_SECRET = "your-secret"
```

## Controls

| Key | Action |
|-----|--------|
| F1 | Audio Equalizer |
| F2 | Bass Pulse |
| F3 | Audio Wave |
| F4 | Aurora |
| F5 | Sunset |
| F6 | Ocean |
| F7 | Clock |
| F8 | CheckMK (default) |
| F9/F10 | Speed -/+ |
| F11/F12 | Brightness -/+ |
| Right CTRL | Show host list GUI |
| ESC (hold) | Exit |

## 🖼️ GUI Hostlist

Press **Right CTRL** to open a floating window showing all hosts:

- Grouped by keyboard row
- Color-coded by status
- Press RCTRL + key to highlight specific host
- ESC or click outside to close

## Autostart (systemd)

```bash
# Create service
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/rgb-keyboard.service << 'SERVICE'
[Unit]
Description=RGB Keyboard CheckMK Monitor
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=/path/to/aurenet
ExecStart=/path/to/aurenet/.venv/bin/python3 rgb_keyboard.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
SERVICE

# Enable & start
systemctl --user daemon-reload
systemctl --user enable --now rgb-keyboard.service
```

## Contributing

Contributions welcome! Ideas:

- Support for more keyboards
- More monitoring backends (Zabbix, Nagios, Prometheus)
- Custom color themes
- Web configuration interface

## License

MIT License - see [LICENSE](LICENSE)

## Support

If you find this useful:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-orange?logo=ko-fi)](https://ko-fi.com/yourusername)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?logo=github)](https://github.com/sponsors/yourusername)

---

Made with ❤️ and RGB
