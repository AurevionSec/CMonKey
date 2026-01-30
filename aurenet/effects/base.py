"""
AURENET - Effect Base Class

Defines the interface and base implementation for all effects.
"""

import time
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, TYPE_CHECKING
from openrgb.utils import RGBColor
from aurenet.core.types import EffectConfig, KeyboardState

if TYPE_CHECKING:
    from aurenet.config.themes import ColorProvider


class Effect(ABC):
    """
    Base class for all keyboard effects.

    Effects receive configuration and keyboard state, then render
    colors for all LEDs on the keyboard.
    """

    def __init__(
        self,
        config: EffectConfig,
        num_leds: int,
        led_positions: Dict[int, Tuple[int, int]],
        color_provider: "ColorProvider",
    ):
        """
        Initialize effect.

        Args:
            config: Effect configuration (speed, brightness, theme, etc.)
            num_leds: Number of LEDs on the keyboard
            led_positions: Mapping from LED index to (row, col) position
            color_provider: Theme-based color provider
        """
        self.config = config
        self.num_leds = num_leds
        self.led_positions = led_positions
        self.colors = color_provider
        self.start_time = time.time()

    @abstractmethod
    def render(self, state: KeyboardState) -> List[RGBColor]:
        """
        Render the effect and return colors for all LEDs.

        Args:
            state: Current keyboard state (audio, pressed keys, time, etc.)

        Returns:
            List of RGBColor objects, one for each LED
        """
        pass

    def get_elapsed(self) -> float:
        """
        Get elapsed time since effect started, scaled by speed.

        Returns:
            Elapsed time in seconds, multiplied by speed factor
        """
        return (time.time() - self.start_time) * self.config.speed
