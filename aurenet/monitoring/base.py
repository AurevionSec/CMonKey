"""
AURENET - Monitoring Provider Interface

Defines the interface for monitoring providers (CheckMK, Prometheus, etc.).
"""

from abc import ABC, abstractmethod
from typing import List
from aurenet.core.types import HostState, AnimationEvent


class MonitoringProvider(ABC):
    """
    Interface for monitoring providers.

    Monitoring providers fetch host status from monitoring systems
    and track animation events (supernova, phoenix, etc.).
    """

    @abstractmethod
    def get_hosts(self) -> List[HostState]:
        """
        Get current host states (thread-safe).

        Returns:
            List of HostState objects representing current monitored hosts
        """
        pass

    @abstractmethod
    def get_animation_events(self) -> List[AnimationEvent]:
        """
        Get triggered animation events.

        Returns animation events (supernova, phoenix, blackhole, etc.)
        that should be rendered in the current frame.

        Returns:
            List of AnimationEvent objects
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """Start the monitoring thread/process."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the monitoring thread/process."""
        pass

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
