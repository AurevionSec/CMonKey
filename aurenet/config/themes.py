"""
AURENET - Color Themes

Defines color themes for animations and status visualization.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class ColorTheme:
    """Defines a color scheme for animations and status."""

    name: str
    # Animation colors (gradient with 4-6 colors)
    gradient: List[Tuple[int, int, int]]
    # Reactive/Highlight color
    highlight: Tuple[int, int, int]
    # Status colors (OK, WARN, CRIT, UNKNOWN)
    status_ok: Tuple[int, int, int] = (46, 204, 113)
    status_warn: Tuple[int, int, int] = (241, 196, 15)
    status_crit: Tuple[int, int, int] = (231, 76, 60)
    status_unknown: Tuple[int, int, int] = (155, 89, 182)


# Predefined Themes
THEMES: Dict[str, ColorTheme] = {
    "default": ColorTheme(
        name="Default",
        gradient=[
            (255, 0, 128),
            (255, 100, 0),
            (255, 255, 0),
            (0, 255, 128),
            (0, 128, 255),
            (128, 0, 255),
        ],
        highlight=(255, 255, 255),
    ),
    "cyberpunk": ColorTheme(
        name="Cyberpunk",
        gradient=[(255, 0, 128), (0, 255, 255), (255, 0, 255), (0, 255, 128)],
        highlight=(255, 0, 255),
        status_ok=(0, 255, 136),
        status_warn=(255, 170, 0),
        status_crit=(255, 0, 68),
    ),
    "nord": ColorTheme(
        name="Nord",
        gradient=[
            (94, 129, 172),
            (136, 192, 208),
            (163, 190, 140),
            (235, 203, 139),
            (191, 97, 106),
        ],
        highlight=(236, 239, 244),
        status_ok=(163, 190, 140),
        status_warn=(235, 203, 139),
        status_crit=(191, 97, 106),
        status_unknown=(180, 142, 173),
    ),
    "fire": ColorTheme(
        name="Fire",
        gradient=[
            (255, 255, 200),
            (255, 200, 0),
            (255, 100, 0),
            (200, 50, 0),
            (100, 0, 0),
        ],
        highlight=(255, 255, 200),
        status_ok=(255, 200, 0),
        status_warn=(255, 100, 0),
        status_crit=(200, 0, 0),
    ),
    "ocean": ColorTheme(
        name="Ocean",
        gradient=[
            (0, 50, 100),
            (0, 100, 150),
            (0, 150, 200),
            (50, 200, 220),
            (150, 230, 255),
        ],
        highlight=(200, 255, 255),
        status_ok=(0, 200, 150),
        status_warn=(255, 200, 100),
        status_crit=(255, 80, 80),
    ),
    "matrix": ColorTheme(
        name="Matrix",
        gradient=[(0, 50, 0), (0, 100, 0), (0, 180, 0), (0, 255, 0), (150, 255, 150)],
        highlight=(200, 255, 200),
        status_ok=(0, 255, 0),
        status_warn=(200, 255, 0),
        status_crit=(255, 50, 50),
    ),
    "synthwave": ColorTheme(
        name="Synthwave",
        gradient=[
            (255, 0, 128),
            (255, 0, 255),
            (128, 0, 255),
            (0, 0, 255),
            (0, 128, 255),
        ],
        highlight=(255, 100, 200),
        status_ok=(0, 255, 200),
        status_warn=(255, 200, 0),
        status_crit=(255, 50, 100),
    ),
}


def get_theme(name: str) -> ColorTheme:
    """
    Get a theme by name.

    Args:
        name: Theme name

    Returns:
        ColorTheme instance

    Raises:
        KeyError: If theme doesn't exist
    """
    if name not in THEMES:
        raise KeyError(f"Unknown theme: {name}. Available themes: {list(THEMES.keys())}")
    return THEMES[name]
