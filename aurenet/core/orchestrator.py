"""
AURENET - Application Orchestrator

Coordinates components via event bus.
"""

import logging
import threading

from aurenet.config.settings import AppConfig
from aurenet.core.events import Event, EventBus, EventType
from aurenet.core.types import EffectConfig

logger = logging.getLogger(__name__)


class ApplicationOrchestrator:
    """
    Coordinates application components via event bus.

    Subscribes to events and updates configuration state.
    Thread-safe for concurrent access to effect configuration.
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: AppConfig,
    ):
        """
        Initialize orchestrator.

        Args:
            event_bus: Event bus for subscribing to events
            config: Application configuration
        """
        self._event_bus = event_bus
        self._app_config = config
        self._lock = threading.RLock()

        # Effect configuration state
        self._effect_config = EffectConfig(
            speed=1.0,
            brightness=1.0,
            effect="checkmk",
            theme="default",
        )

        # Subscribe to events
        self._event_bus.subscribe(EventType.EFFECT_CHANGED, self._on_effect_changed)
        self._event_bus.subscribe(EventType.THEME_CHANGED, self._on_theme_changed)
        self._event_bus.subscribe(EventType.SPEED_CHANGED, self._on_speed_changed)
        self._event_bus.subscribe(EventType.BRIGHTNESS_CHANGED, self._on_brightness_changed)

    def get_effect_config(self) -> EffectConfig:
        """
        Get current effect configuration (thread-safe copy).

        Returns:
            Copy of current effect configuration
        """
        with self._lock:
            from copy import copy

            return copy(self._effect_config)

    def _on_effect_changed(self, event: Event) -> None:
        """Handle effect change event."""
        effect_name = event.data.get("effect")
        if effect_name:
            with self._lock:
                self._effect_config.effect = effect_name
            logger.info(f"Effect changed to: {effect_name}")

    def _on_theme_changed(self, event: Event) -> None:
        """Handle theme change event."""
        theme_name = event.data.get("theme")
        if theme_name:
            with self._lock:
                self._effect_config.theme = theme_name
            logger.info(f"Theme changed to: {theme_name}")

    def _on_speed_changed(self, event: Event) -> None:
        """Handle speed adjustment event."""
        delta = event.data.get("delta", 0.0)

        with self._lock:
            new_speed = self._effect_config.speed + delta
            # Clamp to valid range
            self._effect_config.speed = max(0.1, min(5.0, new_speed))
            speed = self._effect_config.speed

        logger.debug(f"Speed adjusted to: {speed:.1f}")

    def _on_brightness_changed(self, event: Event) -> None:
        """Handle brightness adjustment event."""
        delta = event.data.get("delta", 0.0)

        with self._lock:
            new_brightness = self._effect_config.brightness + delta
            # Clamp to valid range
            self._effect_config.brightness = max(0.0, min(1.0, new_brightness))
            brightness = self._effect_config.brightness

        logger.debug(f"Brightness adjusted to: {brightness:.1f}")
