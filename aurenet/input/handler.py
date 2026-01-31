"""
AURENET - Input Handler

Handles keyboard input and emits events to the event bus.
"""

import logging
import threading
import time
from typing import Optional, Set

from evdev import InputDevice, ecodes, list_devices

from aurenet.core.events import Event, EventBus, EventType
from aurenet.input.keyboard_mapping import ActionType, KeyboardMapper

logger = logging.getLogger(__name__)


class InputHandler:
    """
    Handles keyboard input and publishes events.

    Decoupled from configuration and effects - only publishes events.
    Runs in a separate thread to monitor evdev keyboard input.
    """

    def __init__(
        self,
        event_bus: EventBus,
        keyboard_mapper: KeyboardMapper,
        device_name: str = "AT Translated Set 2 keyboard",
        esc_hold_duration: float = 1.0,
    ):
        """
        Initialize input handler.

        Args:
            event_bus: Event bus for publishing events
            keyboard_mapper: Keyboard mapping for actions and LED indices
            device_name: Name of keyboard device to monitor
            esc_hold_duration: How long ESC must be held to trigger shutdown (seconds)
        """
        self._event_bus = event_bus
        self._mapper = keyboard_mapper
        self._device_name = device_name
        self._esc_hold_duration = esc_hold_duration

        # State
        self._device: Optional[InputDevice] = None
        self._pressed_keys: Set[int] = set()
        self._esc_press_time: Optional[float] = None
        self._rctrl_pressed = False

        # Threading
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    @property
    def pressed_keys(self) -> Set[int]:
        """Get currently pressed keys (thread-safe)."""
        with self._lock:
            return self._pressed_keys.copy()

    def _find_keyboard_device(self) -> Optional[InputDevice]:
        """
        Find keyboard device by name.

        Returns:
            InputDevice or None if not found
        """
        devices = [InputDevice(path) for path in list_devices()]
        for device in devices:
            if self._device_name in device.name:
                logger.info(f"Found keyboard device: {device.name} at {device.path}")
                return device

        logger.warning(f"Keyboard device '{self._device_name}' not found")
        return None

    def handle_key(self, keycode: int, pressed: bool) -> None:
        """
        Handle a keypress or key release.

        Args:
            keycode: evdev keycode
            pressed: True if pressed, False if released
        """
        if pressed:
            self._handle_key_press(keycode)
        else:
            self._handle_key_release(keycode)

    def _handle_key_press(self, keycode: int) -> None:
        """Handle key press event."""
        # Track pressed keys
        with self._lock:
            self._pressed_keys.add(keycode)

        action = self._mapper.get_action(keycode)

        if not action:
            # Still publish key press for reactive effects
            led_index = self._mapper.get_led_index(keycode)
            if led_index is not None:
                self._event_bus.publish(
                    Event.create(
                        EventType.KEY_PRESSED,
                        led_index=led_index,
                        keycode=keycode,
                        rctrl_pressed=self._rctrl_pressed,
                    )
                )
            return

        # Handle action
        if action.type == ActionType.EFFECT_CHANGE:
            self._event_bus.publish(
                Event.create(EventType.EFFECT_CHANGED, effect=action.effect_name)
            )
            print(f"🎨 Effekt: {action.effect_name}")

        elif action.type == ActionType.SPEED_ADJUST:
            self._event_bus.publish(Event.create(EventType.SPEED_CHANGED, delta=action.delta))

        elif action.type == ActionType.BRIGHTNESS_ADJUST:
            self._event_bus.publish(Event.create(EventType.BRIGHTNESS_CHANGED, delta=action.delta))

        elif action.type == ActionType.EXIT:
            self._esc_press_time = time.time()

        elif action.type == ActionType.SHOW_HOSTLIST:
            self._rctrl_pressed = True
            # Publish event for hostlist GUI
            self._event_bus.publish(Event.create(EventType.KEY_PRESSED, action="show_hostlist"))

        elif action.type == ActionType.TEST_ANIMATION:
            # Publish test animation event
            self._event_bus.publish(
                Event.create(EventType.ANIMATION_TRIGGERED, animation_type="test_supernova")
            )

        # Publish key press for reactive effects
        led_index = self._mapper.get_led_index(keycode)
        if led_index is not None:
            self._event_bus.publish(
                Event.create(
                    EventType.KEY_PRESSED,
                    led_index=led_index,
                    keycode=keycode,
                    rctrl_pressed=self._rctrl_pressed,
                )
            )

    def _handle_key_release(self, keycode: int) -> None:
        """Handle key release event."""
        # Track pressed keys
        with self._lock:
            self._pressed_keys.discard(keycode)

        if keycode == ecodes.KEY_RIGHTCTRL:
            self._rctrl_pressed = False

        elif keycode == ecodes.KEY_ESC and self._esc_press_time:
            # Long press ESC to exit
            if time.time() - self._esc_press_time > self._esc_hold_duration:
                print("👋 Beende...")
                self._event_bus.publish(Event.create(EventType.SHUTDOWN_REQUESTED))
            self._esc_press_time = None

        # Publish key release
        led_index = self._mapper.get_led_index(keycode)
        if led_index is not None:
            self._event_bus.publish(
                Event.create(EventType.KEY_RELEASED, led_index=led_index, keycode=keycode)
            )

    def _input_loop(self) -> None:
        """Main input loop (runs in separate thread)."""
        logger.info("Input handler thread started")

        while self._running:
            if self._device is None:
                # Try to find device
                self._device = self._find_keyboard_device()
                if self._device is None:
                    time.sleep(1.0)
                    continue

            try:
                # Read events with timeout
                event = self._device.read_one()
                if event is None:
                    time.sleep(0.01)
                    continue

                # Only process key events
                if event.type != ecodes.EV_KEY:
                    continue

                # Handle key press/release
                if event.value == 1:  # Key press
                    self.handle_key(event.code, True)
                elif event.value == 0:  # Key release
                    self.handle_key(event.code, False)

            except OSError as e:
                logger.error(f"Device error: {e}")
                self._device = None
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Unexpected error in input loop: {e}", exc_info=True)
                time.sleep(0.1)

        logger.info("Input handler thread stopped")

    def start(self) -> None:
        """Start input handling."""
        if self._running:
            logger.warning("Input handler already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._input_loop, daemon=True)
        self._thread.start()
        logger.info("Input handler started")

    def stop(self) -> None:
        """Stop input handling."""
        if not self._running:
            return

        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._device is not None:
            self._device.close()
            self._device = None

        logger.info("Input handler stopped")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
