"""
AURENET - Custom Exception Classes

Defines the exception hierarchy for the application.
All custom exceptions inherit from AurenetError.
"""


class AurenetError(Exception):
    """Base exception for all AURENET errors."""

    pass


class ConfigurationError(AurenetError):
    """Raised when there are configuration issues."""

    pass


class MonitoringError(AurenetError):
    """Raised when monitoring operations fail."""

    pass


class HardwareError(AurenetError):
    """Raised when hardware operations (OpenRGB) fail."""

    pass


class AudioError(AurenetError):
    """Raised when audio capture or processing fails."""

    pass


class EffectError(AurenetError):
    """Raised when effect rendering fails."""

    pass
