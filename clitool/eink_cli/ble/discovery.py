"""BLE device discovery for eink displays."""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from bleak import BleakScanner
from bleak.backends.device import BLEDevice

from .exceptions import BLEError

_LOGGER = logging.getLogger(__name__)

# Known manufacturer IDs for eink displays
KNOWN_MANUFACTURER_IDS = {
    0x1337: 'atc',   # ATC firmware (4919 decimal)
    0x2446: 'oepl',  # OEPL firmware (9286 decimal)
}


async def discover_devices(timeout: float = 10.0) -> List[Dict[str, Any]]:
    """Discover BLE eink devices.
    
    Args:
        timeout: Discovery timeout in seconds
        
    Returns:
        List of discovered device information dictionaries
        
    Raises:
        BLEError: If discovery fails
    """
    _LOGGER.info(f"Starting BLE discovery (timeout: {timeout}s)")
    
    try:
        devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
        eink_devices = []
        
        for device_address, (device, adv_data) in devices.items():
            device_info = _parse_device(device, adv_data)
            if device_info:
                eink_devices.append(device_info)
                _LOGGER.debug(f"Found eink device: {device_info}")
        
        _LOGGER.info(f"Discovery completed, found {len(eink_devices)} eink devices")
        return eink_devices
        
    except Exception as e:
        raise BLEError(f"Device discovery failed: {e}")


def _parse_device(device: BLEDevice, adv_data) -> Optional[Dict[str, Any]]:
    """Parse BLE device advertisement data.
    
    Args:
        device: BLE device object
        adv_data: Advertisement data
        
    Returns:
        Device information dictionary if it's an eink device, None otherwise
    """
    # Check manufacturer data for known eink device IDs
    manufacturer_data = adv_data.manufacturer_data
    
    for mfg_id, protocol in KNOWN_MANUFACTURER_IDS.items():
        if mfg_id in manufacturer_data:
            return {
                'mac_address': device.address.upper(),
                'name': device.name or f"EInk Device ({protocol.upper()})",
                'protocol': protocol,
                'manufacturer_id': mfg_id,
                'rssi': adv_data.rssi,
                'device': device,
                'adv_data': manufacturer_data[mfg_id]
            }
    
    return None


async def find_device_by_mac(mac_address: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """Find a specific device by MAC address.
    
    Args:
        mac_address: Target device MAC address
        timeout: Discovery timeout in seconds
        
    Returns:
        Device information dictionary if found, None otherwise
    """
    mac_address = mac_address.upper()
    _LOGGER.debug(f"Searching for device {mac_address}")
    
    devices = await discover_devices(timeout)
    
    for device in devices:
        if device['mac_address'] == mac_address:
            _LOGGER.debug(f"Found target device: {device}")
            return device
    
    _LOGGER.warning(f"Device {mac_address} not found")
    return None