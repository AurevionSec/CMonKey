"""
AURENET - Sunset Effect

Warm sunset colors with gradient from sky to horizon.
"""

import math
from typing import List
from openrgb.utils import RGBColor
from aurenet.effects.base import Effect
from aurenet.core.types import KeyboardState
from aurenet.core.utils import apply_brightness, blend_colors


class SunsetEffect(Effect):
    """Sunset effect with vertical gradient and slow horizontal wave."""

    def render(self, state: KeyboardState) -> List[RGBColor]:
        """
        Render sunset effect.

        Creates a sunset with colors transitioning from dark blue/purple sky
        at the top to orange/yellow horizon at the bottom, with a slow
        horizontal wave for subtle movement.

        Args:
            state: Current keyboard state (unused for this effect)

        Returns:
            List of RGB colors for all LEDs
        """
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Slow horizontal wave
            wave = math.sin(elapsed * 0.2 + pos[0] * 0.1)

            # Gradient from top to bottom (sky -> horizon)
            height_factor = pos[1] / 6  # 0 at top, 1 at bottom

            # Top: Dark blue/purple -> Bottom: Orange/red
            if height_factor < 0.3:
                base = blend_colors((20, 10, 60), (80, 30, 100), height_factor / 0.3)
            elif height_factor < 0.5:
                base = blend_colors((80, 30, 100), (200, 80, 50), (height_factor - 0.3) / 0.2)
            elif height_factor < 0.7:
                base = blend_colors((200, 80, 50), (255, 150, 30), (height_factor - 0.5) / 0.2)
            else:
                base = blend_colors((255, 150, 30), (255, 200, 100), (height_factor - 0.7) / 0.3)

            # Subtle wave variation
            variation = (wave + 1) / 2 * 0.2
            rgb = (
                min(255, int(base[0] * (1 + variation))),
                min(255, int(base[1] * (1 + variation * 0.5))),
                min(255, int(base[2] * (1 - variation * 0.3))),
            )

            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors
