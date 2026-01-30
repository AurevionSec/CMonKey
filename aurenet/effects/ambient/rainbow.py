"""
AURENET - Rainbow Effect

Rainbow wave across the keyboard based on X position.
"""

from typing import List
from openrgb.utils import RGBColor
from aurenet.effects.base import Effect
from aurenet.core.types import KeyboardState
from aurenet.core.utils import hsv_to_rgb, apply_brightness


class RainbowEffect(Effect):
    """Rainbow wave effect based on LED position."""

    def render(self, state: KeyboardState) -> List[RGBColor]:
        """
        Render rainbow wave effect.

        Creates a rainbow wave that moves across the keyboard horizontally
        based on the X position of each LED.

        Args:
            state: Current keyboard state (unused for this effect)

        Returns:
            List of RGB colors for all LEDs
        """
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))
            # Wave based on X position
            hue = (pos[0] / 20.0 + elapsed * 0.5) % 1.0
            rgb = hsv_to_rgb(hue, 1.0, 1.0)
            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors
