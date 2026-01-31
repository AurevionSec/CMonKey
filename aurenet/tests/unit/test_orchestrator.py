"""
Unit tests for Application Orchestrator.
"""

import pytest
from aurenet.core.orchestrator import ApplicationOrchestrator
from aurenet.core.events import EventBus, Event, EventType
from aurenet.config.settings import AppConfig


class TestApplicationOrchestrator:
    """Tests for ApplicationOrchestrator."""

    def test_init(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        effect_config = orchestrator.get_effect_config()
        assert effect_config.effect == "checkmk"
        assert effect_config.speed == 1.0
        assert effect_config.brightness == 1.0

    def test_effect_changed(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Publish effect change
        bus.publish(Event.create(EventType.EFFECT_CHANGED, effect="rainbow"))

        # Verify effect was changed
        effect_config = orchestrator.get_effect_config()
        assert effect_config.effect == "rainbow"

    def test_theme_changed(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Publish theme change
        bus.publish(Event.create(EventType.THEME_CHANGED, theme="neon"))

        # Verify theme was changed
        effect_config = orchestrator.get_effect_config()
        assert effect_config.theme == "neon"

    def test_speed_adjustment_increase(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Initial speed is 1.0
        assert orchestrator.get_effect_config().speed == 1.0

        # Increase speed
        bus.publish(Event.create(EventType.SPEED_CHANGED, delta=0.2))

        assert orchestrator.get_effect_config().speed == 1.2

    def test_speed_adjustment_decrease(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Decrease speed
        bus.publish(Event.create(EventType.SPEED_CHANGED, delta=-0.2))

        assert orchestrator.get_effect_config().speed == 0.8

    def test_speed_clamping_max(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Try to increase beyond max
        bus.publish(Event.create(EventType.SPEED_CHANGED, delta=10.0))

        # Should clamp to 5.0
        assert orchestrator.get_effect_config().speed == 5.0

    def test_speed_clamping_min(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Try to decrease beyond min
        bus.publish(Event.create(EventType.SPEED_CHANGED, delta=-10.0))

        # Should clamp to 0.1
        assert orchestrator.get_effect_config().speed == 0.1

    def test_brightness_adjustment_increase(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Initial brightness is 1.0
        assert orchestrator.get_effect_config().brightness == 1.0

        # Try to increase (already at max, should stay at 1.0)
        bus.publish(Event.create(EventType.BRIGHTNESS_CHANGED, delta=0.1))

        assert orchestrator.get_effect_config().brightness == 1.0

    def test_brightness_adjustment_decrease(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Decrease brightness
        bus.publish(Event.create(EventType.BRIGHTNESS_CHANGED, delta=-0.1))

        assert orchestrator.get_effect_config().brightness == 0.9

    def test_brightness_clamping_min(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Try to decrease beyond min
        bus.publish(Event.create(EventType.BRIGHTNESS_CHANGED, delta=-10.0))

        # Should clamp to 0.0
        assert orchestrator.get_effect_config().brightness == 0.0

    def test_multiple_events(self):
        bus = EventBus()
        config = AppConfig()
        orchestrator = ApplicationOrchestrator(bus, config)

        # Publish multiple events
        bus.publish(Event.create(EventType.EFFECT_CHANGED, effect="matrix"))
        bus.publish(Event.create(EventType.SPEED_CHANGED, delta=0.5))
        bus.publish(Event.create(EventType.BRIGHTNESS_CHANGED, delta=-0.3))

        # Verify all changes applied
        effect_config = orchestrator.get_effect_config()
        assert effect_config.effect == "matrix"
        assert effect_config.speed == 1.5
        assert effect_config.brightness == 0.7
