"""
AURENET - CheckMK Monitoring Provider

Polls CheckMK API for host status and tracks animation events.
"""

import time
import threading
from typing import List, Dict, Set, Any, Optional, Tuple
from requests import RequestException
from aurenet.monitoring.base import MonitoringProvider
from aurenet.core.types import HostState, AnimationEvent, AnimationType
from aurenet.core.errors import MonitoringError
from aurenet.infrastructure.http import HttpClient
from aurenet.infrastructure.triggers import TriggerFileSystem


class CheckMKMonitor(MonitoringProvider):
    """CheckMK monitoring provider with thread-safe state management."""

    def __init__(
        self,
        base_url: str,
        user: str,
        secret: str,
        http_client: HttpClient,
        trigger_fs: TriggerFileSystem,
        update_interval: float = 30.0,
    ):
        """
        Initialize CheckMK monitor.

        Args:
            base_url: CheckMK server URL (e.g., http://server:5000/cmk)
            user: Automation user
            secret: Automation secret
            http_client: HTTP client for API requests
            trigger_fs: Trigger file system for test triggers
            update_interval: Poll interval in seconds
        """
        self._base_url = base_url
        self._user = user
        self._secret = secret
        self._http = http_client
        self._triggers = trigger_fs
        self._update_interval = update_interval

        # Thread safety
        self._hosts_lock = threading.RLock()
        self._animation_lock = threading.RLock()

        # State
        self._hosts: List[HostState] = []
        self._previous_states: Dict[str, int] = {}
        self._known_hosts: Set[str] = set()

        # Animation events
        self._supernovas: Dict[str, Dict[str, Any]] = {}
        self._phoenixes: Dict[str, Dict[str, Any]] = {}
        self._warnings: Dict[str, Dict[str, Any]] = {}
        self._blackholes: Dict[str, Dict[str, Any]] = {}
        self._spawns: Dict[str, Dict[str, Any]] = {}
        self._celebration: Optional[Dict[str, float]] = None
        self._had_problems: bool = False

        # Thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the monitoring thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
        print("🔍 CheckMK Monitor gestartet")

    def stop(self) -> None:
        """Stop the monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def get_hosts(self) -> List[HostState]:
        """Get current host states (thread-safe copy)."""
        with self._hosts_lock:
            return [
                HostState(
                    name=h.name,
                    state=h.state,
                    led_index=h.led_index,
                    zone_color=h.zone_color,
                    priority=h.priority,
                )
                for h in self._hosts
            ]

    def get_animation_events(self) -> List[AnimationEvent]:
        """Get triggered animation events for current frame."""
        with self._animation_lock:
            events = []

            # Collect supernova events
            for hostname, data in self._supernovas.items():
                led_index = self._get_led_index_for_host(hostname)
                events.append(
                    AnimationEvent(
                        type=AnimationType.SUPERNOVA,
                        hostname=hostname,
                        start_time=data["start"],
                        led_index=led_index,
                        prev_state=data["prev_state"],
                        priority=data["priority"],
                    )
                )

            # Collect phoenix events
            for hostname, data in self._phoenixes.items():
                led_index = self._get_led_index_for_host(hostname)
                events.append(
                    AnimationEvent(
                        type=AnimationType.PHOENIX,
                        hostname=hostname,
                        start_time=data["start"],
                        led_index=led_index,
                        prev_state=data["prev_state"],
                        priority=data["priority"],
                    )
                )

            # Collect warning events
            for hostname, data in self._warnings.items():
                led_index = self._get_led_index_for_host(hostname)
                events.append(
                    AnimationEvent(
                        type=AnimationType.WARNING,
                        hostname=hostname,
                        start_time=data["start"],
                        led_index=led_index,
                        priority=data["priority"],
                    )
                )

            # Collect blackhole events
            for hostname, data in self._blackholes.items():
                events.append(
                    AnimationEvent(
                        type=AnimationType.BLACKHOLE,
                        hostname=hostname,
                        start_time=data["start"],
                        led_index=data["key_index"],
                        priority=data["priority"],
                    )
                )

            # Collect spawn events
            for hostname, data in self._spawns.items():
                events.append(
                    AnimationEvent(
                        type=AnimationType.SPAWN,
                        hostname=hostname,
                        start_time=data["start"],
                        led_index=data["key_index"],
                        priority=data["priority"],
                    )
                )

            # Collect celebration event
            if self._celebration:
                events.append(
                    AnimationEvent(
                        type=AnimationType.CELEBRATION,
                        hostname="all",
                        start_time=self._celebration["start"],
                        led_index=0,
                    )
                )

            return events

    def _get_led_index_for_host(self, hostname: str) -> int:
        """Get LED index for a given hostname."""
        with self._hosts_lock:
            for host in self._hosts:
                if host.name == hostname:
                    return host.led_index
        return 0

    def _update_loop(self):
        """Main update loop running in separate thread."""
        last_fetch = 0.0

        while self._running:
            try:
                # Check for test trigger files (every 0.5s)
                self._check_test_triggers()

                # Fetch hosts periodically
                now = time.time()
                if now - last_fetch >= self._update_interval:
                    self._fetch_and_update_hosts()
                    last_fetch = now

                time.sleep(0.5)  # Fast loop for trigger checks

            except Exception as e:
                print(f"❌ CheckMK update error: {e}")
                time.sleep(5.0)  # Back off on errors

    def _check_test_triggers(self):
        """Check for test trigger files."""
        if self._triggers.check_and_clear("trigger_supernova"):
            with self._hosts_lock:
                if self._hosts:
                    test_host = self._hosts[0].name
                    with self._animation_lock:
                        self._supernovas[test_host] = {
                            "start": time.time(),
                            "prev_state": 0,
                            "priority": 0,
                        }
                    print(f"💥 TEST-SUPERNOVA: {test_host}")

        if self._triggers.check_and_clear("trigger_phoenix"):
            with self._hosts_lock:
                if self._hosts:
                    test_host = self._hosts[0].name
                    with self._animation_lock:
                        self._phoenixes[test_host] = {
                            "start": time.time(),
                            "prev_state": 2,
                            "priority": 0,
                        }
                    print(f"🔥 TEST-PHOENIX: {test_host}")

        if self._triggers.check_and_clear("trigger_warning"):
            with self._hosts_lock:
                if self._hosts:
                    test_host = self._hosts[0].name
                    with self._animation_lock:
                        self._warnings[test_host] = {
                            "start": time.time(),
                            "priority": 0,
                        }
                    print(f"⚠️ TEST-WARNING: {test_host}")

        if self._triggers.check_and_clear("trigger_blackhole"):
            with self._hosts_lock:
                if self._hosts:
                    test_host = self._hosts[0].name
                    with self._animation_lock:
                        self._blackholes[test_host] = {
                            "start": time.time(),
                            "key_index": 0,
                            "priority": 0,
                        }
                    print(f"🕳️ TEST-BLACKHOLE: {test_host}")

        if self._triggers.check_and_clear("trigger_spawn"):
            with self._hosts_lock:
                if self._hosts:
                    test_host = self._hosts[0].name
                    with self._animation_lock:
                        self._spawns[test_host] = {
                            "start": time.time(),
                            "key_index": 0,
                            "priority": 0,
                        }
                    print(f"✨ TEST-SPAWN: {test_host}")

    def _fetch_and_update_hosts(self):
        """Fetch hosts from CheckMK with retry logic."""
        url = f"{self._base_url}/check_mk/api/1.0/domain-types/host/collections/all"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._user} {self._secret}",
        }
        params = {"columns": "state"}

        # Retry logic with exponential backoff
        for attempt in range(3):
            try:
                response = self._http.get(url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                self._process_response(response.json())
                return
            except RequestException as e:
                if attempt == 2:
                    raise MonitoringError(f"Failed to fetch hosts after 3 attempts: {e}")
                time.sleep(2**attempt)  # Exponential backoff: 1s, 2s

    def _process_response(self, data: Dict[str, Any]):
        """Process API response and update host state."""
        now = time.time()
        new_hosts_raw = []

        # Parse response
        for h in data.get("value", []):
            name = h.get("id", "")
            state = h.get("extensions", {}).get("state", 0)
            new_hosts_raw.append({"name": name, "state": state})

            # Track state changes for animations
            with self._animation_lock:
                prev_state = self._previous_states.get(name, 0)
                priority = self._get_host_priority(name)

                # SUPERNOVA: Host goes CRITICAL (state 2)
                if state == 2 and prev_state != 2:
                    self._supernovas[name] = {
                        "start": now,
                        "prev_state": prev_state,
                        "priority": priority,
                    }
                    print(f"💥 SUPERNOVA: {name} geht CRITICAL!")

                # PHOENIX: Host recovers to OK (state 0)
                elif state == 0 and prev_state > 0:
                    self._phoenixes[name] = {
                        "start": now,
                        "prev_state": prev_state,
                        "priority": priority,
                    }
                    print(f"🔥 PHOENIX: {name} ist wieder OK!")

                # WARNING: Host goes to WARN (state 1) from OK
                elif state == 1 and prev_state == 0:
                    self._warnings[name] = {"start": now, "priority": priority}
                    print(f"⚠️ WARNING: {name} hat Probleme!")

                # Update previous state
                self._previous_states[name] = state

        # Sort by priority
        sorted_hosts = self._sort_by_priority(new_hosts_raw)
        current_names = {h["name"] for h in sorted_hosts}

        # BLACKHOLE: Host disappeared
        with self._animation_lock:
            if self._known_hosts:
                disappeared = self._known_hosts - current_names
                for name in disappeared:
                    # Find old position
                    old_index = 0
                    with self._hosts_lock:
                        for i, h in enumerate(self._hosts):
                            if h.name == name:
                                old_index = i
                                break

                    priority = self._get_host_priority(name)
                    self._blackholes[name] = {
                        "start": now,
                        "key_index": old_index,
                        "priority": priority,
                    }
                    print(f"🕳️ BLACKHOLE: {name} ist verschwunden!")
                    self._previous_states.pop(name, None)

            # SPAWN: New host appears
            if self._known_hosts:
                new_names = current_names - self._known_hosts
                for name in new_names:
                    # Find new position
                    new_index = 0
                    for i, h in enumerate(sorted_hosts):
                        if h["name"] == name:
                            new_index = i
                            break

                    priority = self._get_host_priority(name)
                    self._spawns[name] = {
                        "start": now,
                        "key_index": new_index,
                        "priority": priority,
                    }
                    print(f"✨ SPAWN: {name} ist neu erschienen!")

            self._known_hosts = current_names

        # Clean up old animations (older than 5 seconds)
        with self._animation_lock:
            self._supernovas = {k: v for k, v in self._supernovas.items() if now - v["start"] < 5.0}
            self._phoenixes = {k: v for k, v in self._phoenixes.items() if now - v["start"] < 5.0}
            self._warnings = {k: v for k, v in self._warnings.items() if now - v["start"] < 5.0}
            self._blackholes = {k: v for k, v in self._blackholes.items() if now - v["start"] < 5.0}
            self._spawns = {k: v for k, v in self._spawns.items() if now - v["start"] < 5.0}

        # Convert to HostState objects
        new_hosts = []
        for i, host_dict in enumerate(sorted_hosts):
            new_hosts.append(
                HostState(
                    name=host_dict["name"],
                    state=host_dict["state"],
                    led_index=i,
                    zone_color=self._get_zone_color(host_dict["name"]),
                    priority=self._get_host_priority(host_dict["name"]),
                )
            )

        # Update hosts (thread-safe)
        with self._hosts_lock:
            self._hosts = new_hosts

        # Check for celebration (all hosts OK)
        self._check_celebration()

    def _check_celebration(self):
        """Check if all hosts are OK and trigger celebration."""
        with self._hosts_lock:
            if not self._hosts:
                return

            all_ok = all(h.state == 0 for h in self._hosts)

            with self._animation_lock:
                if all_ok and self._had_problems and not self._celebration:
                    self._celebration = {"start": time.time()}
                    print("🎉 CELEBRATION: Alle Hosts OK!")

                if not all_ok:
                    self._had_problems = True
                    self._celebration = None

    def _get_host_priority(self, name: str) -> int:
        """Get priority for host (0=most important, higher=less important)."""
        name_lower = name.lower()
        if "server" in name_lower or "srv" in name_lower:
            return 0
        if "router" in name_lower or "switch" in name_lower or "gateway" in name_lower:
            return 1
        if "nas" in name_lower or "storage" in name_lower:
            return 2
        if "proxmox" in name_lower or "esxi" in name_lower or "vm" in name_lower:
            return 3
        if "pi" in name_lower or "raspberry" in name_lower:
            return 4
        if "pc" in name_lower or "desktop" in name_lower or "workstation" in name_lower:
            return 5
        if "laptop" in name_lower or "notebook" in name_lower:
            return 6
        if "phone" in name_lower or "iphone" in name_lower or "android" in name_lower:
            return 8
        if "ipad" in name_lower or "tablet" in name_lower:
            return 9
        return 7

    def _get_zone_color(self, name: str) -> Tuple[int, int, int]:
        """Get zone color based on hostname."""
        name_lower = name.lower()

        # Servers/Infrastructure = Blue
        if (
            "server" in name_lower
            or "srv" in name_lower
            or "proxmox" in name_lower
            or "esxi" in name_lower
        ):
            return (30, 100, 255)

        # Network = Cyan
        if (
            "router" in name_lower
            or "switch" in name_lower
            or "gateway" in name_lower
            or "ap" in name_lower
        ):
            return (0, 200, 200)

        # Storage = Purple
        if "nas" in name_lower or "storage" in name_lower or "backup" in name_lower:
            return (150, 50, 255)

        # Raspberry/IoT = Pink
        if (
            "pi" in name_lower
            or "raspberry" in name_lower
            or "esp" in name_lower
            or "tapo" in name_lower
        ):
            return (255, 50, 150)

        # PCs/Workstations = Green
        if (
            "pc" in name_lower
            or "desktop" in name_lower
            or "workstation" in name_lower
            or "mega" in name_lower
        ):
            return (50, 255, 100)

        # Laptops = Teal
        if "laptop" in name_lower or "notebook" in name_lower:
            return (50, 200, 180)

        # Mobile = Orange
        if (
            "phone" in name_lower
            or "iphone" in name_lower
            or "android" in name_lower
            or "pixel" in name_lower
        ):
            return (255, 150, 30)

        # Tablets = Yellow-Green
        if "ipad" in name_lower or "tablet" in name_lower or "pad" in name_lower:
            return (180, 255, 50)

        # Cameras/Security = Red-Orange
        if "cam" in name_lower or "ring" in name_lower or "security" in name_lower:
            return (255, 80, 50)

        # Smart Home = Warm White
        if "home" in name_lower or "assistant" in name_lower or "alexa" in name_lower:
            return (255, 200, 150)

        # Default = White-Green
        return (100, 220, 100)

    def _sort_by_priority(self, hosts: List[Dict]) -> List[Dict]:
        """Sort hosts by importance."""
        return sorted(hosts, key=lambda h: self._get_host_priority(h["name"]))
