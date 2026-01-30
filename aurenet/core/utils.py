"""
AURENET - Utility Functions

Common utility functions used across the application.
"""

from typing import Tuple
from openrgb.utils import RGBColor


def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Convert HSV color to RGB.

    Args:
        h: Hue (0.0 to 1.0)
        s: Saturation (0.0 to 1.0)
        v: Value/Brightness (0.0 to 1.0)

    Returns:
        RGB tuple with values 0-255
    """
    h = h % 1.0
    if s == 0.0:
        val = int(v * 255)
        return (val, val, val)

    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q

    return (int(r * 255), int(g * 255), int(b * 255))


def apply_brightness(color: Tuple[int, int, int], brightness: float) -> RGBColor:
    """
    Apply brightness to a color.

    Args:
        color: RGB tuple (r, g, b) with values 0-255
        brightness: Brightness multiplier (0.0 to 1.0)

    Returns:
        RGBColor with brightness applied
    """
    return RGBColor(
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness),
    )


def blend_colors(
    c1: Tuple[int, int, int], c2: Tuple[int, int, int], factor: float
) -> Tuple[int, int, int]:
    """
    Blend two colors together.

    Args:
        c1: First color (r, g, b)
        c2: Second color (r, g, b)
        factor: Blend factor (0.0 = c1, 1.0 = c2)

    Returns:
        Blended color
    """
    factor = max(0.0, min(1.0, factor))
    return (
        int(c1[0] * (1 - factor) + c2[0] * factor),
        int(c1[1] * (1 - factor) + c2[1] * factor),
        int(c1[2] * (1 - factor) + c2[2] * factor),
    )
