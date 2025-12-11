"""Simplified BLE connection management for CLI tool."""

import asyncio
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

from .exceptions import BLEConnectionError, BLEProtocolError, BLETimeoutError

if TYPE_CHECKING:
    from .protocols import BLEProtocol

_LOGGER = logging.getLogger(__name__)


class BLEConnection:
    """Simplified BLE connection manager for CLI tool."""
    
    def __init__(self, mac_address: str, service_uuid: str, protocol: "BLEProtocol"):
        """Initialize BLE connection manager.
        
        Args:
            mac_address: Device MAC address
            service_uuid: Protocol-specific BLE service UUID
            protocol: Protocol instance for this device
        """
        self.mac_address = mac_address
        self.service_uuid = service_uuid
        self.protocol = protocol
        self.client: BleakClient | None = None
        self.write_char = None
        self._response_queue = asyncio.Queue()
        self._notification_active = False
    
    async def __aenter__(self):
        """Establish BLE connection and initialize protocol."""
        try:
            # Find device
            device = await BleakScanner.find_device_by_address(self.mac_address)
            if not device:
                raise BLEConnectionError(f"Device {self.mac_address} not found")
            
            # Establish connection
            self.client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                f"CLI-{self.mac_address}",
                self._disconnected_callback,
                timeout=15.0,
            )
            
            # Resolve characteristic
            if not self._resolve_characteristic():
                await self.client.disconnect()
                raise BLEConnectionError(
                    f"Could not resolve characteristic for service {self.service_uuid}"
                )
            
            # Enable notifications
            await self.client.start_notify(self.write_char, self._notification_callback)
            self._notification_active = True
            
            # Protocol initialization
            await self.protocol.initialize_connection(self)
            
            return self
            
        except Exception as e:
            await self._cleanup()
            if isinstance(e, BLEConnectionError):
                raise
            raise BLEConnectionError(f"Failed to connect to {self.mac_address}: {e}")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up BLE connection."""
        await self._cleanup()
    
    async def _cleanup(self):
        """Clean up connection resources."""
        if self.client and self.client.is_connected:
            if self._notification_active:
                try:
                    await self.client.stop_notify(self.write_char)
                except Exception:
                    pass
                finally:
                    self._notification_active = False
            try:
                await self.client.disconnect()
            except Exception:
                pass
    
    def _resolve_characteristic(self) -> bool:
        """Resolve BLE characteristic for the protocol-specific service."""
        try:
            if not self.client or not self.client.services:
                return False
            
            char = self.client.services.get_characteristic(self.service_uuid)
            if char:
                self.write_char = char
                _LOGGER.debug(f"Resolved characteristic for service {self.service_uuid}")
                return True
            
            _LOGGER.error(f"Could not find characteristic for service {self.service_uuid}")
            return False
            
        except Exception as e:
            _LOGGER.error(f"Error resolving characteristic: {e}")
            return False
    
    def _notification_callback(self, sender, data: bytearray) -> None:
        """Handle notification from device."""
        try:
            self._response_queue.put_nowait(bytes(data))
        except asyncio.QueueFull:
            _LOGGER.warning(f"Response queue full for {self.mac_address}")
    
    async def write_command_with_response(self, command: bytes, timeout: float = 10.0) -> bytes:
        """Write command and wait for response."""
        # Clear pending responses
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        await self._write_raw(command)
        
        try:
            response = await asyncio.wait_for(self._response_queue.get(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            raise BLETimeoutError(f"No response from {self.mac_address} within {timeout}s")
    
    async def write_command(self, data: bytes) -> None:
        """Write command without expecting response."""
        await self._write_raw(data)
    
    async def _write_raw(self, data: bytes) -> None:
        """Write raw data to device characteristic."""
        if not self.write_char:
            raise BLEProtocolError("Write characteristic not available")
        
        await self.client.write_gatt_char(self.write_char, data, response=False)
    
    def _disconnected_callback(self, client: BleakClient) -> None:
        """Handle disconnection event."""
        _LOGGER.debug(f"Device {self.mac_address} disconnected")