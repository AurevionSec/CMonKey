"""
Unit tests for effects.
"""

import pytest
from openrgb.utils import RGBColor
from aurenet.effects import create_registry
from aurenet.effects.ambient.rainbow import RainbowEffect
from aurenet.effects.ambient.breathing import BreathingEffect
from aurenet.effects.ambient.aurora import AuroraEffect
from aurenet.effects.interactive.fire import FireEffect
from aurenet.effects.interactive.matrix import MatrixEffect
from aurenet.core.types import EffectConfig, KeyboardState
from aurenet.config.themes import ColorProvider


@pytest.fixture
def effect_config():
    """Create test effect configuration."""
    return EffectConfig(speed=1.0, brightness=1.0, effect="rainbow", theme="default")


@pytest.fixture
def led_positions():
    """Create test LED position mapping."""
    positions = {}
    for row in range(6):
        for col in range(20):
            led_index = row * 20 + col
            positions[led_index] = (col, row)
    return positions


@pytest.fixture
def color_provider():
    """Create test color provider."""
    return ColorProvider("default")


@pytest.fixture
def keyboard_state():
    """Create test keyboard state."""
    return KeyboardState()


class TestRainbowEffect:
    """Tests for RainbowEffect."""

    def test_render_returns_correct_number_of_colors(
        self, effect_config, led_positions, color_provider, keyboard_state
    ):
        effect = RainbowEffect(effect_config, 120, led_positions, color_provider)
        colors = effect.render(keyboard_state)

        assert len(colors) == 120
        assert all(isinstance(c, RGBColor) for c in colors)

    def test_render_uses_brightness(
        self, effect_config, led_positions, color_provider, keyboard_state
    ):
        # Half brightness
        effect_config.brightness = 0.5
        effect = RainbowEffect(effect_config, 120, led_positions, color_provider)
        colors = effect.render(keyboard_state)

        # Colors should be dimmer
        assert all(c.red <= 128 and c.green <= 128 and c.blue <= 128 for c in colors)


class TestBreathingEffect:
    """Tests for BreathingEffect."""

    def test_render_returns_correct_number_of_colors(
        self, effect_config, led_positions, color_provider, keyboard_state
    ):
        effect = BreathingEffect(effect_config, 120, led_positions, color_provider)
        colors = effect.render(keyboard_state)

        assert len(colors) == 120
        assert all(isinstance(c, RGBColor) for c in colors)


class TestFireEffect:
    """Tests for FireEffect."""

    def test_render_returns_correct_number_of_colors(
        self, effect_config, led_positions, color_provider, keyboard_state
    ):
        effect = FireEffect(effect_config, 120, led_positions, color_provider)
        colors = effect.render(keyboard_state)

        assert len(colors) == 120
        assert all(isinstance(c, RGBColor) for c in colors)


class TestMatrixEffect:
    """Tests for MatrixEffect."""

    def test_render_returns_correct_number_of_colors(
        self, effect_config, led_positions, color_provider, keyboard_state
    ):
        effect = MatrixEffect(effect_config, 120, led_positions, color_provider)
        colors = effect.render(keyboard_state)

        assert len(colors) == 120
        assert all(isinstance(c, RGBColor) for c in colors)


class TestAuroraEffect:
    """Tests for AuroraEffect."""

    def test_render_returns_correct_number_of_colors(
        self, effect_config, led_positions, color_provider, keyboard_state
    ):
        effect = AuroraEffect(effect_config, 120, led_positions, color_provider)
        colors = effect.render(keyboard_state)

        assert len(colors) == 120
        assert all(isinstance(c, RGBColor) for c in colors)


class TestEffectRegistry:
    """Tests for EffectRegistry."""

    def test_create_registry_has_all_effects(self):
        registry = create_registry()
        effects = registry.list_effects()

        assert "rainbow" in effects
        assert "breathing" in effects
        assert "fire" in effects
        assert "matrix" in effects
        assert "aurora" in effects
        assert "sunset" in effects

    def test_create_effect_by_name(self, effect_config, led_positions, color_provider):
        registry = create_registry()
        effect = registry.create("rainbow", effect_config, 120, led_positions, color_provider)

        assert isinstance(effect, RainbowEffect)

    def test_create_unknown_effect_raises_error(self, effect_config, led_positions, color_provider):
        registry = create_registry()

        with pytest.raises(ValueError, match="Unknown effect"):
            registry.create("nonexistent", effect_config, 120, led_positions, color_provider)
