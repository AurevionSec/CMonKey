"""
AURENET - Breathing Effect

Smooth breathing effect with theme colors.
"""

import math
from typing import List
from openrgb.utils import RGBColor
from aurenet.effects.base import Effect
from aurenet.core.types import KeyboardState
from aurenet.core.utils import apply_brightness


class BreathingEffect(Effect):
    """Smooth breathing effect using theme gradient."""

    def render(self, state: KeyboardState) -> List[RGBColor]:
        """
        Render breathing effect.

        Creates a smooth sine wave breathing effect that cycles through
        the theme gradient colors.

        Args:
            state: Current keyboard state (unused for this effect)

        Returns:
            List of RGB colors for all LEDs
        """
        elapsed = self.get_elapsed()

        # Sine wave for smooth breathing
        breath = (math.sin(elapsed * 2) + 1) / 2  # 0 to 1
        breath = breath**2  # More time in the darker phase

        # Breathe through theme gradient
        rgb = self.colors.get_gradient_color(breath * 0.5)  # Only half of gradient
        colors = [
            apply_brightness(rgb, self.config.brightness * breath * 0.9 + 0.1)
            for _ in range(self.num_leds)
        ]

        return colors
