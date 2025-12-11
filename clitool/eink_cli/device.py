"""Device management for eink displays."""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from .ble import discover_devices, find_device_by_mac, BLEConnection, get_protocol_by_name
from .ble.exceptions import BLEError, BLEConnectionError, UnsupportedProtocolError

_LOGGER = logging.getLogger(__name__)


class DeviceManager:
    """Manages BLE eink device connections and operations."""
    
    def __init__(self):
        """Initialize device manager."""
        self._connections = {}
    
    async def discover_devices(self, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Discover nearby BLE eink devices.
        
        Args:
            timeout: Discovery timeout in seconds
            
        Returns:
            List of discovered device information
        """
        return await discover_devices(timeout)
    
    async def connect_device(
        self, 
        mac_address: str, 
        protocol: Optional[str] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Connect to a device and get its capabilities.
        
        Args:
            mac_address: Device MAC address
            protocol: Protocol name ('oepl' or 'atc'), auto-detected if None
            timeout: Connection timeout in seconds
            
        Returns:
            Device information dictionary with capabilities
            
        Raises:
            BLEConnectionError: If connection fails
            UnsupportedProtocolError: If protocol is not supported
        """
        mac_address = mac_address.upper()
        _LOGGER.info(f"Connecting to device {mac_address}")
        
        # Find device if protocol not specified
        if not protocol:
            device_info = await find_device_by_mac(mac_address, timeout=min(timeout, 10.0))
            if not device_info:
                raise BLEConnectionError(f"Device {mac_address} not found during discovery")
            protocol = device_info['protocol']
            _LOGGER.info(f"Auto-detected protocol: {protocol}")
        
        # Get protocol handler
        try:
            protocol_handler = get_protocol_by_name(protocol)
        except UnsupportedProtocolError as e:
            raise UnsupportedProtocolError(f"Protocol '{protocol}' not supported: {e}")
        
        # Create connection
        connection = BLEConnection(
            mac_address=mac_address,
            service_uuid=protocol_handler.service_uuid,
            protocol=protocol_handler
        )
        
        try:
            # Connect and interrogate device
            async with connection:
                _LOGGER.info(f"Connected to {mac_address}, interrogating device...")
                capabilities = await protocol_handler.interrogate_device(connection)
                
                device_info = {
                    'mac_address': mac_address,
                    'protocol': protocol,
                    'name': f"EInk Device ({protocol.upper()})",
                    'width': capabilities.width,
                    'height': capabilities.height,
                    'color_scheme': capabilities.color_scheme,
                    'connection': connection,
                    'protocol_handler': protocol_handler,
                    'capabilities': capabilities
                }
                
                _LOGGER.info(
                    f"Device {mac_address}: {capabilities.width}x{capabilities.height}, "
                    f"color_scheme={capabilities.color_scheme}"
                )
                
                return device_info
                
        except Exception as e:
            raise BLEConnectionError(f"Failed to connect to {mac_address}: {e}")
    
    async def upload_image(self, image_data: bytes, device_info: Dict[str, Any]) -> bool:
        """Upload image to device.
        
        Args:
            image_data: JPEG image data
            device_info: Device information from connect_device()
            
        Returns:
            True if upload succeeded, False otherwise
        """
        mac_address = device_info['mac_address']
        protocol = device_info['protocol']
        protocol_handler = device_info['protocol_handler']
        capabilities = device_info['capabilities']
        
        _LOGGER.info(f"Uploading image to {mac_address} ({len(image_data)} bytes)")
        
        # Create new connection for upload
        connection = BLEConnection(
            mac_address=mac_address,
            service_uuid=protocol_handler.service_uuid,
            protocol=protocol_handler
        )
        
        try:
            async with connection:
                # Create metadata object for upload
                from .ble.metadata import BLEDeviceMetadata
                metadata = BLEDeviceMetadata({
                    'width': capabilities.width,
                    'height': capabilities.height,
                    'color_scheme': capabilities.color_scheme,
                    'hw_type': 0,  # Default hw_type for CLI tool
                    'rotatebuffer': capabilities.rotatebuffer  # Use device's rotation requirement
                })
                
                # Create uploader and upload image
                from .ble.image_upload import BLEImageUploader
                uploader = BLEImageUploader(connection, mac_address)
                
                # Use appropriate upload method based on protocol
                if protocol == 'oepl':
                    # OEPL supports direct write (faster)
                    success = await uploader.upload_direct_write(
                        image_data, metadata, compressed=True, dither=2
                    )
                else:
                    # ATC uses block-based upload
                    success = await uploader.upload_image(
                        image_data, metadata, protocol_type=protocol, dither=2
                    )
                
                if success:
                    _LOGGER.info(f"Image uploaded successfully to {mac_address}")
                else:
                    _LOGGER.error(f"Image upload failed to {mac_address}")
                
                return success
                
        except Exception as e:
            _LOGGER.error(f"Upload error for {mac_address}: {e}")
            return False