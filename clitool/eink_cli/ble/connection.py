"""Simplified BLE connection management for CLI tool."""

import asyncio
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache, BleakNotFoundError

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
        """Establish BLE connection and initialize protocol with improved retry logic."""
        max_retries = 6
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                _LOGGER.debug(f"Connection attempt {attempt + 1}/{max_retries} for {self.mac_address}")
                
                # Find device with longer timeout on later attempts
                scan_timeout = min(60.0 + attempt * 2.0, 60.0)
                
                # On retry attempts, do a fresh scan to handle "device disappeared" errors
                if attempt > 0:
                    _LOGGER.debug(f"Performing fresh device scan for {self.mac_address}...")
                    # Clear any cached device info
                    await asyncio.sleep(0.5)  # Brief pause before scanning
                
                device = await BleakScanner.find_device_by_address(self.mac_address, timeout=scan_timeout)
                
                if not device:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        _LOGGER.warning(f"Device {self.mac_address} not found, retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        continue
                    raise BLEConnectionError(f"Device {self.mac_address} not found after {max_retries} attempts")
                
                # Establish connection with retry-specific timeout
                connection_timeout = min(10.0 + attempt * 5.0, 30.0)
                self.client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    f"CLI-{self.mac_address}",
                    self._disconnected_callback,
                    timeout=connection_timeout,
                    max_attempts=2,  # Reduce bleak_retry_connector attempts since we handle retries here
                )
                
                # Resolve characteristic
                if not self._resolve_characteristic():
                    await self.client.disconnect()
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        _LOGGER.warning(f"Could not resolve characteristic, retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        continue
                    raise BLEConnectionError(
                        f"Could not resolve characteristic for service {self.service_uuid}"
                    )
                
                # Enable notifications
                await self.client.start_notify(self.write_char, self._notification_callback)
                self._notification_active = True
                
                # Protocol initialization
                await self.protocol.initialize_connection(self)
                
                _LOGGER.info(f"Successfully connected to {self.mac_address} on attempt {attempt + 1}")
                return self
                
            except (BleakNotFoundError, BLEConnectionError, asyncio.TimeoutError) as e:
                await self._cleanup()
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s, 8s, 16s
                    _LOGGER.warning(
                        f"Connection attempt {attempt + 1} failed for {self.mac_address}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    _LOGGER.error(f"All {max_retries} connection attempts failed for {self.mac_address}")
                    raise BLEConnectionError(
                        f"Failed to connect to {self.mac_address} after {max_retries} attempts: {e}"
                    )
            except Exception as e:
                await self._cleanup()
                _LOGGER.error(f"Unexpected error connecting to {self.mac_address}: {e}")
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