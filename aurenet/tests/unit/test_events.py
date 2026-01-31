"""
Unit tests for event system.
"""

import pytest
from aurenet.core.events import EventBus, Event, EventType


class TestEvent:
    """Tests for Event class."""

    def test_create_event_with_data(self):
        event = Event.create(EventType.EFFECT_CHANGED, effect="rainbow")

        assert event.type == EventType.EFFECT_CHANGED
        assert event.data == {"effect": "rainbow"}
        assert event.timestamp > 0


class TestEventBus:
    """Tests for EventBus."""

    def test_subscribe_and_publish(self):
        bus = EventBus()
        received_events = []

        def handler(event: Event):
            received_events.append(event)

        bus.subscribe(EventType.EFFECT_CHANGED, handler)
        event = Event.create(EventType.EFFECT_CHANGED, effect="fire")
        bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].data["effect"] == "fire"

    def test_multiple_handlers(self):
        bus = EventBus()
        calls_a = []
        calls_b = []

        bus.subscribe(EventType.EFFECT_CHANGED, lambda e: calls_a.append(e))
        bus.subscribe(EventType.EFFECT_CHANGED, lambda e: calls_b.append(e))

        event = Event.create(EventType.EFFECT_CHANGED, effect="matrix")
        bus.publish(event)

        assert len(calls_a) == 1
        assert len(calls_b) == 1

    def test_multiple_event_types(self):
        bus = EventBus()
        effect_events = []
        speed_events = []

        bus.subscribe(EventType.EFFECT_CHANGED, lambda e: effect_events.append(e))
        bus.subscribe(EventType.SPEED_CHANGED, lambda e: speed_events.append(e))

        bus.publish(Event.create(EventType.EFFECT_CHANGED, effect="aurora"))
        bus.publish(Event.create(EventType.SPEED_CHANGED, delta=0.1))

        assert len(effect_events) == 1
        assert len(speed_events) == 1

    def test_unsubscribe(self):
        bus = EventBus()
        calls = []

        def handler(event: Event):
            calls.append(event)

        bus.subscribe(EventType.EFFECT_CHANGED, handler)
        bus.unsubscribe(EventType.EFFECT_CHANGED, handler)

        bus.publish(Event.create(EventType.EFFECT_CHANGED, effect="test"))

        assert len(calls) == 0

    def test_handler_error_does_not_break_other_handlers(self):
        bus = EventBus()
        calls = []

        def bad_handler(event: Event):
            raise RuntimeError("Handler error")

        def good_handler(event: Event):
            calls.append(event)

        bus.subscribe(EventType.EFFECT_CHANGED, bad_handler)
        bus.subscribe(EventType.EFFECT_CHANGED, good_handler)

        # Should not raise
        bus.publish(Event.create(EventType.EFFECT_CHANGED, effect="test"))

        # Good handler should still have been called
        assert len(calls) == 1

    def test_clear(self):
        bus = EventBus()
        calls = []

        bus.subscribe(EventType.EFFECT_CHANGED, lambda e: calls.append(e))
        bus.clear()
        bus.publish(Event.create(EventType.EFFECT_CHANGED, effect="test"))

        assert len(calls) == 0
