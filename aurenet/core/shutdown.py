"""
AURENET - Shutdown Coordinator

Manages graceful shutdown of all application components.
"""

import logging
import threading
from typing import List, Protocol

logger = logging.getLogger(__name__)


class Stoppable(Protocol):
    """Protocol for components that can be stopped."""

    def stop(self) -> None:
        """Stop the component and release resources."""
        ...


class ShutdownCoordinator:
    """
    Coordinates graceful shutdown of application components.

    Ensures all components are stopped in reverse registration order
    and errors in one component don't prevent others from stopping.
    """

    def __init__(self):
        """Initialize shutdown coordinator."""
        self._components: List[Stoppable] = []
        self._shutdown_event = threading.Event()
        self._lock = threading.Lock()

    def register(self, component: Stoppable) -> None:
        """
        Register a component for shutdown.

        Args:
            component: Component to register
        """
        with self._lock:
            self._components.append(component)
            logger.debug(f"Registered component for shutdown: {type(component).__name__}")

    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown has been requested.

        Returns:
            True if shutdown was requested
        """
        return self._shutdown_event.is_set()

    def wait_for_shutdown(self, timeout: float = None) -> bool:
        """
        Wait for shutdown to be requested.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if shutdown was requested, False if timeout occurred
        """
        return self._shutdown_event.wait(timeout)

    def request_shutdown(self) -> None:
        """Request shutdown of all components."""
        logger.info("Shutdown requested")
        self._shutdown_event.set()

    def shutdown(self) -> None:
        """
        Shutdown all registered components.

        Components are stopped in reverse registration order (LIFO).
        Errors in one component do not prevent others from stopping.
        """
        logger.info("Starting shutdown sequence")
        self.request_shutdown()

        with self._lock:
            # Stop in reverse order (LIFO - last registered, first stopped)
            for component in reversed(self._components):
                component_name = type(component).__name__
                try:
                    logger.debug(f"Stopping {component_name}...")
                    component.stop()
                    logger.debug(f"{component_name} stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping {component_name}: {e}", exc_info=True)

        logger.info("Shutdown sequence complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False
