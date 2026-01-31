"""
AURENET - Keyboard Mapping

Maps keycodes to LED indices and actions.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional
from evdev import ecodes


class ActionType(Enum):
    """Types of actions that can be triggered by keypresses."""

    EFFECT_CHANGE = "effect_change"
    SPEED_ADJUST = "speed_adjust"
    BRIGHTNESS_ADJUST = "brightness_adjust"
    EXIT = "exit"
    SHOW_HOSTLIST = "show_hostlist"
    TEST_ANIMATION = "test_animation"


@dataclass
class KeyAction:
    """Action associated with a keypress."""

    type: ActionType
    effect_name: Optional[str] = None
    delta: Optional[float] = None


# Mapping from evdev keycodes to LED indices
KEYCODE_TO_LED: Dict[int, int] = {
    ecodes.KEY_ESC: 0,
    ecodes.KEY_F1: 9,
    ecodes.KEY_F2: 15,
    ecodes.KEY_F3: 20,
    ecodes.KEY_F4: 24,
    ecodes.KEY_F5: 35,
    ecodes.KEY_F6: 40,
    ecodes.KEY_F7: 45,
    ecodes.KEY_F8: 49,
    ecodes.KEY_F9: 54,
    ecodes.KEY_F10: 59,
    ecodes.KEY_F11: 64,
    ecodes.KEY_F12: 68,
    ecodes.KEY_GRAVE: 1,
    ecodes.KEY_1: 6,
    ecodes.KEY_2: 11,
    ecodes.KEY_3: 16,
    ecodes.KEY_4: 21,
    ecodes.KEY_5: 25,
    ecodes.KEY_6: 30,
    ecodes.KEY_7: 36,
    ecodes.KEY_8: 41,
    ecodes.KEY_9: 46,
    ecodes.KEY_0: 50,
    ecodes.KEY_MINUS: 55,
    ecodes.KEY_EQUAL: 60,
    ecodes.KEY_BACKSPACE: 65,
    ecodes.KEY_TAB: 2,
    ecodes.KEY_Q: 10,
    ecodes.KEY_W: 17,
    ecodes.KEY_E: 22,
    ecodes.KEY_R: 26,
    ecodes.KEY_T: 31,
    ecodes.KEY_Y: 37,
    ecodes.KEY_U: 42,
    ecodes.KEY_I: 47,
    ecodes.KEY_O: 51,
    ecodes.KEY_P: 56,
    ecodes.KEY_CAPSLOCK: 3,
    ecodes.KEY_A: 12,
    ecodes.KEY_S: 18,
    ecodes.KEY_D: 23,
    ecodes.KEY_F: 27,
    ecodes.KEY_G: 32,
    ecodes.KEY_H: 38,
    ecodes.KEY_J: 43,
    ecodes.KEY_K: 48,
    ecodes.KEY_L: 52,
    ecodes.KEY_ENTER: 69,
    ecodes.KEY_LEFTSHIFT: 4,
    ecodes.KEY_Z: 13,
    ecodes.KEY_X: 19,
    ecodes.KEY_C: 28,
    ecodes.KEY_V: 33,
    ecodes.KEY_B: 39,
    ecodes.KEY_N: 44,
    ecodes.KEY_M: 53,
    ecodes.KEY_RIGHTSHIFT: 71,
    ecodes.KEY_LEFTCTRL: 5,
    ecodes.KEY_LEFTALT: 14,
    ecodes.KEY_SPACE: 34,
    ecodes.KEY_RIGHTALT: 72,
    ecodes.KEY_RIGHTCTRL: 99,
}

# Effect selection keys
EFFECT_KEYS: Dict[int, str] = {
    # Audio (F1-F3)
    ecodes.KEY_F1: "audio",  # Audio Equalizer
    ecodes.KEY_F2: "audio_pulse",  # Bass Pulse
    ecodes.KEY_F3: "audio_wave",  # Audio Wave
    # Beautiful (F4-F6)
    ecodes.KEY_F4: "aurora",  # Northern Lights
    ecodes.KEY_F5: "sunset",  # Sunset
    ecodes.KEY_F6: "ocean",  # Ocean Waves
    # Useful (F7-F8)
    ecodes.KEY_F7: "clock",  # Clock Display
    ecodes.KEY_F8: "checkmk",  # CheckMK Monitoring (Default)
}


class KeyboardMapper:
    """Maps keycodes to actions and LED indices."""

    def __init__(self):
        self._keycode_to_led = KEYCODE_TO_LED
        self._effect_keys = EFFECT_KEYS

    def get_led_index(self, keycode: int) -> Optional[int]:
        """
        Get LED index for a keycode.

        Args:
            keycode: evdev keycode

        Returns:
            LED index or None if not mapped
        """
        return self._keycode_to_led.get(keycode)

    def get_action(self, keycode: int) -> Optional[KeyAction]:
        """
        Get action for a keycode.

        Args:
            keycode: evdev keycode

        Returns:
            KeyAction or None if no action mapped
        """
        # Effect selection (F1-F8)
        if keycode in self._effect_keys:
            return KeyAction(
                type=ActionType.EFFECT_CHANGE, effect_name=self._effect_keys[keycode]
            )

        # Speed control (F9/F10)
        if keycode == ecodes.KEY_F9:
            return KeyAction(type=ActionType.SPEED_ADJUST, delta=-0.2)
        if keycode == ecodes.KEY_F10:
            return KeyAction(type=ActionType.SPEED_ADJUST, delta=0.2)

        # Brightness control (F11/F12)
        if keycode == ecodes.KEY_F11:
            return KeyAction(type=ActionType.BRIGHTNESS_ADJUST, delta=-0.1)
        if keycode == ecodes.KEY_F12:
            return KeyAction(type=ActionType.BRIGHTNESS_ADJUST, delta=0.1)

        # Exit (ESC)
        if keycode == ecodes.KEY_ESC:
            return KeyAction(type=ActionType.EXIT)

        # Show hostlist (Right CTRL)
        if keycode == ecodes.KEY_RIGHTCTRL:
            return KeyAction(type=ActionType.SHOW_HOSTLIST)

        # Test animation (Space)
        if keycode == ecodes.KEY_SPACE:
            return KeyAction(type=ActionType.TEST_ANIMATION)

        return None
