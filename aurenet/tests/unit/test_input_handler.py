"""
Unit tests for input handler.
"""

import time
from unittest.mock import Mock

from evdev import ecodes

from aurenet.core.events import EventBus, EventType
from aurenet.input.handler import InputHandler
from aurenet.input.keyboard_mapping import KeyboardMapper


class TestInputHandler:
    """Tests for InputHandler."""

    def test_handle_effect_change(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.EFFECT_CHANGED, lambda e: received_events.append(e))

        # Press F1 (audio effect)
        handler.handle_key(ecodes.KEY_F1, True)

        assert len(received_events) == 1
        assert received_events[0].data["effect"] == "audio"

    def test_handle_speed_adjust(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.SPEED_CHANGED, lambda e: received_events.append(e))

        # Press F9 (decrease speed)
        handler.handle_key(ecodes.KEY_F9, True)

        assert len(received_events) == 1
        assert received_events[0].data["delta"] == -0.2

    def test_handle_brightness_adjust(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.BRIGHTNESS_CHANGED, lambda e: received_events.append(e))

        # Press F11 (decrease brightness)
        handler.handle_key(ecodes.KEY_F11, True)

        assert len(received_events) == 1
        assert received_events[0].data["delta"] == -0.1

    def test_esc_hold_triggers_shutdown(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper, esc_hold_duration=0.1)

        received_events = []
        bus.subscribe(EventType.SHUTDOWN_REQUESTED, lambda e: received_events.append(e))

        # Press ESC
        handler.handle_key(ecodes.KEY_ESC, True)
        assert len(received_events) == 0

        # Wait for hold duration
        time.sleep(0.15)

        # Release ESC
        handler.handle_key(ecodes.KEY_ESC, False)

        assert len(received_events) == 1

    def test_esc_short_press_no_shutdown(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper, esc_hold_duration=0.5)

        received_events = []
        bus.subscribe(EventType.SHUTDOWN_REQUESTED, lambda e: received_events.append(e))

        # Press and release ESC quickly
        handler.handle_key(ecodes.KEY_ESC, True)
        time.sleep(0.1)
        handler.handle_key(ecodes.KEY_ESC, False)

        assert len(received_events) == 0

    def test_pressed_keys_tracking(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        assert len(handler.pressed_keys) == 0

        # Press some keys
        handler.handle_key(ecodes.KEY_A, True)
        handler.handle_key(ecodes.KEY_B, True)

        assert ecodes.KEY_A in handler.pressed_keys
        assert ecodes.KEY_B in handler.pressed_keys

        # Release one key
        handler.handle_key(ecodes.KEY_A, False)

        assert ecodes.KEY_A not in handler.pressed_keys
        assert ecodes.KEY_B in handler.pressed_keys

    def test_key_press_publishes_led_event(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.KEY_PRESSED, lambda e: received_events.append(e))

        # Press key with LED mapping
        handler.handle_key(ecodes.KEY_A, True)

        # Should get event with led_index
        assert len(received_events) == 1
        assert "led_index" in received_events[0].data

    def test_key_release_publishes_event(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.KEY_RELEASED, lambda e: received_events.append(e))

        # Press and release
        handler.handle_key(ecodes.KEY_A, True)
        handler.handle_key(ecodes.KEY_A, False)

        assert len(received_events) == 1
        assert "led_index" in received_events[0].data

    def test_test_animation_trigger(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.ANIMATION_TRIGGERED, lambda e: received_events.append(e))

        # Press space (test animation)
        handler.handle_key(ecodes.KEY_SPACE, True)

        assert len(received_events) == 1
        assert "animation_type" in received_events[0].data

    def test_context_manager(self):
        bus = EventBus()
        mapper = KeyboardMapper()

        # Create mock for _find_keyboard_device to avoid needing real device
        handler = InputHandler(bus, mapper)
        handler._find_keyboard_device = Mock(return_value=None)

        # Use context manager
        with handler:
            assert handler._running

        # Should be stopped after exit
        assert not handler._running
