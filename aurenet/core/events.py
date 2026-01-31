"""
AURENET - Event System

Event bus for decoupled communication between components.
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events that can be published."""

    KEY_PRESSED = "key_pressed"
    KEY_RELEASED = "key_released"
    EFFECT_CHANGED = "effect_changed"
    THEME_CHANGED = "theme_changed"
    SPEED_CHANGED = "speed_changed"
    BRIGHTNESS_CHANGED = "brightness_changed"
    MONITORING_UPDATE = "monitoring_update"
    ANIMATION_TRIGGERED = "animation_triggered"
    SHUTDOWN_REQUESTED = "shutdown_requested"


@dataclass
class Event:
    """Event data structure."""

    type: EventType
    data: Dict[str, Any]
    timestamp: float

    @classmethod
    def create(cls, event_type: EventType, **kwargs) -> "Event":
        """
        Create an event with current timestamp.

        Args:
            event_type: Type of event
            **kwargs: Event data

        Returns:
            Event instance
        """
        return cls(type=event_type, data=kwargs, timestamp=time.time())


class EventBus:
    """
    Event bus for publish-subscribe communication.

    Allows components to communicate without direct coupling.
    Thread-safe for concurrent subscribe/publish operations.
    """

    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to listen for
            handler: Callable that receives Event objects
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                except ValueError:
                    pass

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish

        Note:
            Errors in handlers are caught and logged to prevent
            one handler from breaking others.
            Handlers are copied under lock, then called outside lock
            to avoid holding lock during handler execution.
        """
        with self._lock:
            handlers = list(self._handlers.get(event.type, []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.type}: {e}", exc_info=True)

    def clear(self) -> None:
        """Clear all event handlers."""
        with self._lock:
            self._handlers.clear()
