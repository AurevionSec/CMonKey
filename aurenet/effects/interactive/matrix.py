"""
AURENET - Matrix Effect

Matrix-style falling code rain effect.
"""

import random
from typing import List
from openrgb.utils import RGBColor
from aurenet.effects.base import Effect
from aurenet.core.types import KeyboardState
from aurenet.core.utils import apply_brightness


class MatrixEffect(Effect):
    """Matrix rain effect with falling code trails."""

    def render(self, state: KeyboardState) -> List[RGBColor]:
        """
        Render matrix rain effect.

        Creates a Matrix-style falling code effect with multiple drops
        per column and random flickering.

        Args:
            state: Current keyboard state (unused for this effect)

        Returns:
            List of RGB colors for all LEDs
        """
        elapsed = self.get_elapsed()
        colors = []
        # Theme: Primary color for matrix rain
        primary = self.colors.get_gradient_at(2)  # Middle gradient color

        for i in range(self.num_leds):
            pos = self.led_positions.get(i, (0, 0))

            # Multiple "drops" per column
            intensity: float = 0.0
            for drop in range(3):
                drop_speed = 1.5 + drop * 0.5
                drop_offset = drop * 7
                drop_y = ((elapsed * drop_speed + drop_offset + pos[0] * 0.3) % 8) - 2

                dist = abs(pos[1] - drop_y)
                if dist < 1.5:
                    trail_intensity = max(0, 1 - dist / 1.5)
                    intensity = max(intensity, trail_intensity)

            # Random flickering
            if random.random() < 0.02:
                intensity = min(1, intensity + 0.5)

            # Theme: Scale color with intensity
            rgb = (
                int(primary[0] * intensity),
                int(primary[1] * intensity),
                int(primary[2] * intensity),
            )
            colors.append(apply_brightness(rgb, self.config.brightness))

        return colors
