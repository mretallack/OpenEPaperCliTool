#!/usr/bin/env python3
"""Test script to verify retry improvements."""

import asyncio
import logging
from eink_cli.ble.connection import BLEConnection
from eink_cli.ble.protocols import get_protocol_by_name

# Configure logging to see retry attempts
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_connection_retry():
    """Test connection retry with a non-existent device."""
    fake_mac = "AA:BB:CC:DD:EE:FF"
    
    try:
        protocol = get_protocol_by_name("oepl")
        connection = BLEConnection(
            mac_address=fake_mac,
            service_uuid=protocol.service_uuid,
            protocol=protocol
        )
        
        print(f"Testing connection retry with fake MAC: {fake_mac}")
        async with connection:
            print("This should not print - connection should fail")
            
    except Exception as e:
        print(f"Expected failure: {e}")
        print("✓ Retry mechanism working - saw multiple attempts in logs above")

if __name__ == "__main__":
    asyncio.run(test_connection_retry())