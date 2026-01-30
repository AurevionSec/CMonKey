"""
AURENET - Fire Effect

Fire effect from bottom to top with theme-based colors.
"""

import math
import random
from typing import List
from openrgb.utils import RGBColor
from aurenet.effects.base import Effect
from aurenet.core.types import KeyboardState
from aurenet.core.utils import apply_brightness


class FireEffect(Effect):
    """Fire effect with flickering and heat gradient."""

    def render(self, state: KeyboardState) -> List[RGBColor]:
        """
        Render fire effect.

        Creates a fire effect that rises from the bottom of the keyboard
        with flickering and heat-based coloring from the theme gradient.

        Args:
            state: Current keyboard state (unused for this effect)

        Returns:
            List of RGB colors for all LEDs
        """
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Base intensity decreases upward
            base_heat = max(0, 1 - pos[1] / 6)

            # Flickering
            noise = random.random() * 0.3 + 0.7
            flicker = math.sin(elapsed * 10 + pos[0] * 0.5) * 0.2 + 0.8

            heat = base_heat * noise * flicker

            # Theme: Gradient for heat (0=cold/dark, 1=hot/bright)
            rgb = self.colors.get_heat_color(heat)

            colors.append(apply_brightness(rgb, self.config.brightness * heat))

        return colors
