"""
Unit tests for input handling.
"""

import pytest
from evdev import ecodes
from aurenet.input.keyboard_mapping import KeyboardMapper, ActionType, KeyAction
from aurenet.input.handler import InputHandler
from aurenet.core.events import EventBus, Event, EventType


class TestKeyboardMapper:
    """Tests for KeyboardMapper."""

    def test_get_led_index_valid_key(self):
        mapper = KeyboardMapper()

        # Test some key mappings
        assert mapper.get_led_index(ecodes.KEY_ESC) == 0
        assert mapper.get_led_index(ecodes.KEY_F1) == 9
        assert mapper.get_led_index(ecodes.KEY_A) == 12
        assert mapper.get_led_index(ecodes.KEY_SPACE) == 34

    def test_get_led_index_invalid_key(self):
        mapper = KeyboardMapper()

        # Non-existent keycode
        assert mapper.get_led_index(999) is None

    def test_get_action_effect_change(self):
        mapper = KeyboardMapper()

        # F1 should map to audio effect
        action = mapper.get_action(ecodes.KEY_F1)
        assert action is not None
        assert action.type == ActionType.EFFECT_CHANGE
        assert action.effect_name == "audio"

        # F8 should map to checkmk effect
        action = mapper.get_action(ecodes.KEY_F8)
        assert action is not None
        assert action.type == ActionType.EFFECT_CHANGE
        assert action.effect_name == "checkmk"

    def test_get_action_speed_adjust(self):
        mapper = KeyboardMapper()

        # F9 should decrease speed
        action = mapper.get_action(ecodes.KEY_F9)
        assert action is not None
        assert action.type == ActionType.SPEED_ADJUST
        assert action.delta == -0.2

        # F10 should increase speed
        action = mapper.get_action(ecodes.KEY_F10)
        assert action is not None
        assert action.type == ActionType.SPEED_ADJUST
        assert action.delta == 0.2

    def test_get_action_brightness_adjust(self):
        mapper = KeyboardMapper()

        # F11 should decrease brightness
        action = mapper.get_action(ecodes.KEY_F11)
        assert action is not None
        assert action.type == ActionType.BRIGHTNESS_ADJUST
        assert action.delta == -0.1

        # F12 should increase brightness
        action = mapper.get_action(ecodes.KEY_F12)
        assert action is not None
        assert action.type == ActionType.BRIGHTNESS_ADJUST
        assert action.delta == 0.1

    def test_get_action_special_keys(self):
        mapper = KeyboardMapper()

        # ESC should map to exit
        action = mapper.get_action(ecodes.KEY_ESC)
        assert action is not None
        assert action.type == ActionType.EXIT

        # Right CTRL should map to hostlist
        action = mapper.get_action(ecodes.KEY_RIGHTCTRL)
        assert action is not None
        assert action.type == ActionType.SHOW_HOSTLIST

        # Space should map to test animation
        action = mapper.get_action(ecodes.KEY_SPACE)
        assert action is not None
        assert action.type == ActionType.TEST_ANIMATION

    def test_get_action_no_action(self):
        mapper = KeyboardMapper()

        # Regular letter key with no action
        action = mapper.get_action(ecodes.KEY_A)
        assert action is None


class TestInputHandler:
    """Tests for InputHandler."""

    def test_handle_effect_change(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.EFFECT_CHANGED, lambda e: received_events.append(e))

        # Press F1 (audio effect)
        handler.handle_key(ecodes.KEY_F1, pressed=True)

        assert len(received_events) == 1
        assert received_events[0].type == EventType.EFFECT_CHANGED
        assert received_events[0].data["effect"] == "audio"

    def test_handle_speed_adjust(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.SPEED_CHANGED, lambda e: received_events.append(e))

        # Press F9 (speed down)
        handler.handle_key(ecodes.KEY_F9, pressed=True)

        assert len(received_events) == 1
        assert received_events[0].type == EventType.SPEED_CHANGED
        assert received_events[0].data["delta"] == -0.2

    def test_handle_brightness_adjust(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.BRIGHTNESS_CHANGED, lambda e: received_events.append(e))

        # Press F12 (brightness up)
        handler.handle_key(ecodes.KEY_F12, pressed=True)

        assert len(received_events) == 1
        assert received_events[0].type == EventType.BRIGHTNESS_CHANGED
        assert received_events[0].data["delta"] == 0.1

    def test_handle_test_animation(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.ANIMATION_TRIGGERED, lambda e: received_events.append(e))

        # Press Space (test animation)
        handler.handle_key(ecodes.KEY_SPACE, pressed=True)

        assert len(received_events) == 1
        assert received_events[0].type == EventType.ANIMATION_TRIGGERED
        assert received_events[0].data["animation_type"] == "test_supernova"

    def test_handle_key_press_without_action(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.KEY_PRESSED, lambda e: received_events.append(e))

        # Press 'A' (no action, but has LED index)
        handler.handle_key(ecodes.KEY_A, pressed=True)

        assert len(received_events) == 1
        assert received_events[0].type == EventType.KEY_PRESSED
        assert received_events[0].data["led_index"] == 12
        assert received_events[0].data["keycode"] == ecodes.KEY_A

    def test_handle_key_release(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.KEY_RELEASED, lambda e: received_events.append(e))

        # Release 'A'
        handler.handle_key(ecodes.KEY_A, pressed=False)

        assert len(received_events) == 1
        assert received_events[0].type == EventType.KEY_RELEASED
        assert received_events[0].data["led_index"] == 12

    def test_esc_long_press(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.SHUTDOWN_REQUESTED, lambda e: received_events.append(e))

        import time

        # Press ESC
        handler.handle_key(ecodes.KEY_ESC, pressed=True)

        # Wait for long press (> 1 second)
        time.sleep(1.1)

        # Release ESC
        handler.handle_key(ecodes.KEY_ESC, pressed=False)

        # Should trigger shutdown
        assert len(received_events) == 1
        assert received_events[0].type == EventType.SHUTDOWN_REQUESTED

    def test_rctrl_state_tracking(self):
        bus = EventBus()
        mapper = KeyboardMapper()
        handler = InputHandler(bus, mapper)

        received_events = []
        bus.subscribe(EventType.KEY_PRESSED, lambda e: received_events.append(e))

        # Press Right CTRL (triggers SHOW_HOSTLIST action + general key press)
        handler.handle_key(ecodes.KEY_RIGHTCTRL, pressed=True)

        # Press 'A' while Right CTRL is held
        handler.handle_key(ecodes.KEY_A, pressed=True)

        # RIGHTCTRL publishes 2 events (show_hostlist action + led event)
        # A publishes 1 event (led event with rctrl_pressed=True)
        assert len(received_events) == 3
        assert received_events[2].data["rctrl_pressed"] is True

        # Release Right CTRL
        handler.handle_key(ecodes.KEY_RIGHTCTRL, pressed=False)

        # Press 'A' again without Right CTRL
        handler.handle_key(ecodes.KEY_A, pressed=True)

        # This event should have rctrl_pressed=False (no action event this time)
        assert len(received_events) == 4
        assert received_events[3].data["rctrl_pressed"] is False
