"""BLE-related exceptions."""


class BLEError(Exception):
    """Base class for BLE-related errors."""
    pass


class BLEConnectionError(BLEError):
    """BLE connection failed."""
    pass


class BLEProtocolError(BLEError):
    """BLE protocol error."""
    pass


class BLETimeoutError(BLEError):
    """BLE operation timeout."""
    pass


class UnsupportedProtocolError(BLEError):
    """Unsupported protocol or device."""
    pass


class ConfigValidationError(BLEError):
    """Device configuration validation error."""
    pass