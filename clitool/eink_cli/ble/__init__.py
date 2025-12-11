"""BLE communication modules for eink displays."""

from .connection import BLEConnection
from .protocols import get_protocol_by_manufacturer_id, get_protocol_by_name
from .discovery import discover_devices, find_device_by_mac
from .exceptions import BLEError, BLEConnectionError, BLEProtocolError
from .color_scheme import ColorScheme

__all__ = [
    'BLEConnection',
    'get_protocol_by_manufacturer_id',
    'get_protocol_by_name', 
    'discover_devices',
    'find_device_by_mac',
    'BLEError',
    'BLEConnectionError',
    'BLEProtocolError',
    'ColorScheme',
]