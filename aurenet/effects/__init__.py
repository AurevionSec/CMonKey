"""
AURENET - Effects Module

Central registry for all keyboard effects.
"""

from typing import Dict, Type, Tuple
from aurenet.effects.base import Effect
from aurenet.core.types import EffectConfig
from aurenet.config.themes import ColorProvider


class EffectRegistry:
    """
    Registry for all available effects.

    Manages effect registration and creation.
    """

    def __init__(self):
        self._effects: Dict[str, Type[Effect]] = {}

    def register(self, name: str, effect_class: Type[Effect]) -> None:
        """
        Register an effect class.

        Args:
            name: Effect name (used for lookup)
            effect_class: Effect class to register
        """
        self._effects[name] = effect_class

    def create(
        self,
        name: str,
        config: EffectConfig,
        num_leds: int,
        led_positions: Dict[int, Tuple[int, int]],
        color_provider: ColorProvider,
    ) -> Effect:
        """
        Create an effect instance by name.

        Args:
            name: Effect name
            config: Effect configuration
            num_leds: Number of LEDs
            led_positions: LED position mapping
            color_provider: Theme color provider

        Returns:
            Effect instance

        Raises:
            ValueError: If effect name is unknown
        """
        if name not in self._effects:
            raise ValueError(f"Unknown effect: {name}. Available: {list(self._effects.keys())}")

        return self._effects[name](config, num_leds, led_positions, color_provider)

    def list_effects(self) -> list[str]:
        """Get list of all registered effect names."""
        return list(self._effects.keys())


def create_registry() -> EffectRegistry:
    """
    Create and populate the effect registry with all available effects.

    Returns:
        EffectRegistry with all effects registered
    """
    from aurenet.effects.ambient.rainbow import RainbowEffect
    from aurenet.effects.ambient.breathing import BreathingEffect
    from aurenet.effects.ambient.aurora import AuroraEffect
    from aurenet.effects.ambient.sunset import SunsetEffect
    from aurenet.effects.interactive.fire import FireEffect
    from aurenet.effects.interactive.matrix import MatrixEffect

    registry = EffectRegistry()

    # Register ambient effects
    registry.register("rainbow", RainbowEffect)
    registry.register("breathing", BreathingEffect)
    registry.register("aurora", AuroraEffect)
    registry.register("sunset", SunsetEffect)

    # Register interactive effects
    registry.register("fire", FireEffect)
    registry.register("matrix", MatrixEffect)

    return registry
