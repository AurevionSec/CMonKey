"""
AURENET - Core Types

Common types and dataclasses used throughout the application.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple, List, Optional, Any
import numpy as np


@dataclass
class EffectConfig:
    """Configuration for effect rendering."""

    speed: float = 1.0  # Animation speed (0.1 - 3.0)
    brightness: float = 1.0  # Brightness (0.0 - 1.0)
    effect: str = "checkmk"  # Active effect name
    theme: str = "default"  # Active color theme
    base_color: Tuple[int, int, int] = (255, 0, 255)  # Base color for some effects
    reactive_color: Tuple[int, int, int] = (255, 255, 255)  # Reactive color


@dataclass
class KeyPress:
    """Stores a keypress for ripple effects."""

    led_index: int
    timestamp: float
    pos: Tuple[int, int]  # (row, col) position on keyboard


@dataclass
class KeyboardState:
    """
    State snapshot passed to effects for rendering.
    Contains all the dynamic state needed by effects.
    """

    # Audio analysis data
    audio_bands: Optional[np.ndarray] = None
    audio_peak: float = 0.0
    audio_bass: float = 0.0

    # Pressed keys (for reactive effects)
    pressed_keys: List[KeyPress] = None

    # Time
    current_time: float = 0.0

    # Monitoring data (will be populated by monitoring effects)
    monitoring_data: Optional[Any] = None

    def __post_init__(self):
        if self.pressed_keys is None:
            self.pressed_keys = []


@dataclass
class HostState:
    """State of a monitored host."""

    name: str
    state: int  # 0=OK, 1=WARN, 2=CRIT, 3=UNKNOWN
    led_index: int
    zone_color: Tuple[int, int, int]
    priority: int = 0


class AnimationType(Enum):
    """Types of animations that can be triggered."""

    SUPERNOVA = "supernova"  # Host goes CRITICAL
    PHOENIX = "phoenix"  # Host recovers to OK
    WARNING = "warning"  # Host goes to WARNING
    BLACKHOLE = "blackhole"  # Host disappears
    SPAWN = "spawn"  # New host appears
    CELEBRATION = "celebration"  # All hosts OK


@dataclass
class AnimationEvent:
    """Event data for triggering an animation."""

    type: AnimationType
    hostname: str
    start_time: float
    led_index: int
    prev_state: Optional[int] = None
    priority: int = 0
