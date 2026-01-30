"""
AURENET - Aurora Effect

Aurora Borealis (Northern Lights) effect with slow waves.
"""

import math
from typing import List
from openrgb.utils import RGBColor
from aurenet.effects.base import Effect
from aurenet.core.types import KeyboardState
from aurenet.core.utils import apply_brightness


class AuroraEffect(Effect):
    """Aurora Borealis effect with multiple slow waves."""

    def render(self, state: KeyboardState) -> List[RGBColor]:
        """
        Render aurora effect.

        Creates a Northern Lights effect with multiple slow-moving waves
        that combine to create an aurora-like appearance.

        Args:
            state: Current keyboard state (unused for this effect)

        Returns:
            List of RGB colors for all LEDs
        """
        elapsed = self.get_elapsed()
        colors = []

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Multiple slow waves
            wave1 = math.sin(elapsed * 0.3 + pos[0] * 0.15) * 0.5 + 0.5
            wave2 = math.sin(elapsed * 0.2 + pos[0] * 0.1 + 2) * 0.5 + 0.5
            wave3 = math.sin(elapsed * 0.4 + pos[1] * 0.2) * 0.5 + 0.5

            # Theme: Waves through gradient
            combined = (wave1 + wave2 + wave3) / 3
            rgb = self.colors.get_gradient_color(combined)

            # Vertical fade (darker at bottom)
            fade = 0.3 + (1 - pos[1] / 6) * 0.7

            colors.append(apply_brightness(rgb, self.config.brightness * fade))

        return colors
