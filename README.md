# 🎹 CMonKey - RGB Keyboard Monitoring

**Turn your RGB keyboard into a real-time server monitoring dashboard.**

Each key represents a host. Colors show status at a glance. Animations alert you to problems.

![Demo](demo.gif)

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

## Requirements

- **Keyboard**: Roccat Vulcan AIMO (other OpenRGB keyboards may work)
- **OS**: Linux (tested on Arch/Hyprland)
- **Monitoring**: CheckMK instance with API access
- **Software**: OpenRGB server running

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/aurenet.git
cd aurenet

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install openrgb-python requests evdev PyQt6

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
