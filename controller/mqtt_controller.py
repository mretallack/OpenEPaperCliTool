#!/usr/bin/env python3
"""MQTT Controller for EInk Display Updates with Home Assistant MQTT Discovery."""

import json
import logging
import os
import sys
import time
import threading

import asyncio

from pathlib import Path
from typing import Dict, Any

import paho.mqtt.client as mqtt
import yaml

# Add clitool to path for importing
sys.path.insert(0, '../clitool')
from eink_cli.config import load_config
from eink_cli.device import DeviceManager
from eink_cli.imagegen import ImageGenerator
from eink_cli.ble import get_protocol_by_manufacturer_id, discover_devices


class EInkController:
    """MQTT controller for eink display updates."""
    
    def __init__(self, settings_file: str = "settings.yaml"):
        """Initialize controller with settings."""
        self.settings = self._load_settings(settings_file)
        self.template = self._load_template()
        self.client = None
        self.last_update_time = 0
        self.min_update_interval = 30  # Minimum 30 seconds between updates
        self.max_retries = self.settings.get('device', {}).get('max_retries', 5)
        self.ttl_seconds = self.settings.get('device', {}).get('ttl_seconds', 0)
        
        # BLE lock - prevents battery scan and display update from conflicting
        self.ble_lock = threading.Lock()
        
        # HA Discovery settings
        self.discovery_prefix = self.settings.get('homeassistant', {}).get('discovery_prefix', 'homeassistant')
        self.mac_address = self.settings.get('device', {}).get('mac_address', '').upper()
        self.device_id = self.mac_address.replace(':', '').lower()
        self.state_topic = f"eink/{self.device_id}/state"
        self.availability_topic = f"eink/{self.device_id}/availability"
        self.command_topic = f"eink/{self.device_id}/refresh/set"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _load_settings(self, settings_file: str) -> Dict[str, Any]:
        """Load settings from YAML file."""
        try:
            with open(settings_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Settings file {settings_file} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing settings file: {e}")
            sys.exit(1)
    
    def _load_template(self) -> str:
        """Load template file as string."""
        template_file = self.settings['files']['template']
        try:
            with open(template_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Template file {template_file} not found")
            sys.exit(1)
    
    def _publish_ha_discovery(self):
        """Publish Home Assistant MQTT auto-discovery config."""
        device_name = self.settings.get('homeassistant', {}).get('device_name', 'EInk Display')
        
        discovery_payload = {
            "dev": {
                "ids": [self.device_id],
                "name": device_name,
                "mf": "OpenEPaperLink",
                "mdl": "EInk BLE Display",
                "sw": "1.0",
                "connections": [["mac", self.mac_address]]
            },
            "o": {
                "name": "eink-mqtt-controller",
                "sw": "1.0",
                "url": "https://github.com/OpenEPaperLink"
            },
            "cmps": {
                "battery": {
                    "p": "sensor",
                    "name": "Battery",
                    "device_class": "battery",
                    "unit_of_measurement": "%",
                    "state_topic": self.state_topic,
                    "value_template": "{{ value_json.battery_pct }}",
                    "unique_id": f"{self.device_id}_battery"
                },
                "battery_voltage": {
                    "p": "sensor",
                    "name": "Battery Voltage",
                    "device_class": "voltage",
                    "unit_of_measurement": "mV",
                    "state_topic": self.state_topic,
                    "value_template": "{{ value_json.battery_mv }}",
                    "unique_id": f"{self.device_id}_battery_mv"
                },
                "temperature": {
                    "p": "sensor",
                    "name": "Temperature",
                    "device_class": "temperature",
                    "unit_of_measurement": "°C",
                    "state_topic": self.state_topic,
                    "value_template": "{{ value_json.temperature }}",
                    "unique_id": f"{self.device_id}_temperature"
                },
                "last_update": {
                    "p": "sensor",
                    "name": "Last Update",
                    "device_class": "timestamp",
                    "state_topic": self.state_topic,
                    "value_template": "{{ value_json.last_update }}",
                    "unique_id": f"{self.device_id}_last_update"
                },
                "refresh": {
                    "p": "button",
                    "name": "Refresh Display",
                    "command_topic": self.command_topic,
                    "payload_press": "PRESS",
                    "unique_id": f"{self.device_id}_refresh",
                    "icon": "mdi:refresh"
                }
            },
            "availability_topic": self.availability_topic,
            "state_topic": self.state_topic
        }
        
        topic = f"{self.discovery_prefix}/device/{self.device_id}/config"
        self.client.publish(topic, json.dumps(discovery_payload), retain=True)
        self.logger.info(f"Published HA discovery config to {topic}")
        
        # Mark device as online
        self.client.publish(self.availability_topic, "online", retain=True)
    
    def _replace_placeholders(self, template: str, data: Dict[str, Any]) -> str:
        """Replace placeholders in template with data values."""
        result = template
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def _write_device_config(self, config_content: str) -> str:
        """Write device configuration to file."""
        output_file = self.settings['files']['output']
        with open(output_file, 'w') as f:
            f.write(config_content)
        self.logger.info(f"Generated device config: {output_file}")
        return output_file
    
    async def _send_to_device(self, config_file: str) -> bool:
        """Send configuration to device using CLI modules with retry."""
        try:
            self.logger.info(f"Loading config: {config_file}")
            config = load_config(Path(config_file))
            
            mac_address = config['device']['mac_address']
            protocol = config['device'].get('protocol', 'auto')
            
            self.logger.info(f"Connecting to device {mac_address}...")
            
            device_manager = DeviceManager()
            device_info = await device_manager.connect_device(
                mac_address, 
                protocol=protocol if protocol != 'auto' else None,
                timeout=60
            )
            
            self.logger.info(f"Connected to {device_info['name']} ({device_info['protocol']})")
            
            # Generate image
            self.logger.info("Generating image...")
            image_gen = ImageGenerator()
            image_data = await image_gen.generate_image(config, device_info)
            
            # Upload image with retries
            self.logger.info(f"Uploading image with retry (max {self.max_retries} attempts)...")
            success = await device_manager.upload_image(image_data, device_info, max_retries=self.max_retries, ttl_seconds=self.ttl_seconds)
            
            if success:
                self.logger.info("Successfully sent to device")
                return True
            else:
                self.logger.error("Failed to send image after retries")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending to device: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to HA status topic for re-discovery on HA restart
            ha_status_topic = f"{self.discovery_prefix}/status"
            client.subscribe(ha_status_topic)
            self.logger.info(f"Subscribed to HA status: {ha_status_topic}")
            
            # Subscribe to data update topic
            topic = self.settings['mqtt']['topic']
            client.subscribe(topic)
            self.logger.info(f"Subscribed to data topic: {topic}")
            
            # Subscribe to refresh button command topic
            client.subscribe(self.command_topic)
            self.logger.info(f"Subscribed to command topic: {self.command_topic}")
            
            # Publish discovery
            self._publish_ha_discovery()
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for MQTT message received."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            self.logger.info(f"Received message on {topic}: {payload}")
            
            # Handle HA birth message - re-publish discovery
            ha_status_topic = f"{self.discovery_prefix}/status"
            if topic == ha_status_topic and payload == "online":
                self.logger.info("Home Assistant came online, re-publishing discovery")
                self._publish_ha_discovery()
                return
            
            # Handle refresh button press
            if topic == self.command_topic:
                self.logger.info("Refresh button pressed, triggering display update")
                threading.Thread(target=self._run_async_send, args=(self.settings['files']['output'],)).start()
                return
            
            # Handle data update message
            current_time = time.time()
            if current_time - self.last_update_time < self.min_update_interval:
                remaining = self.min_update_interval - (current_time - self.last_update_time)
                self.logger.info(f"Skipping update, cooldown active ({remaining:.1f}s remaining)")
                return
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                self.logger.error("Invalid JSON in message payload")
                return
            
            self.last_update_time = current_time
            
            # Replace placeholders in template
            config_content = self._replace_placeholders(self.template, data)
            
            # Write device configuration
            config_file = self._write_device_config(config_content)
            
            # Send to device in a thread
            threading.Thread(target=self._run_async_send, args=(config_file,)).start()
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _run_async_send(self, config_file):
        """Helper to bridge thread to async without blocking MQTT."""
        with self.ble_lock:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._send_to_device(config_file))
            loop.close()

    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection."""
        self.logger.info("Disconnected from MQTT broker")

    def _battery_publish_loop(self):
        """Periodically scan for device and publish battery status via HA state topic."""
        battery_config = self.settings.get('battery', {})
        if not battery_config.get('enabled', False):
            return

        interval = battery_config.get('interval', 300)
        max_retries = 3
        initial_backoff = 20  # seconds

        self.logger.info(f"Battery publisher started: interval={interval}s")

        while True:
            success = False
            for attempt in range(max_retries):
                if not self.ble_lock.acquire(timeout=5):
                    self.logger.info("BLE busy (display update in progress), skipping battery scan")
                    break
                try:
                    loop = asyncio.new_event_loop()
                    devices = loop.run_until_complete(discover_devices(timeout=10))
                    loop.close()

                    for device in devices:
                        if self.mac_address and device['mac_address'] != self.mac_address:
                            continue
                        adv_bytes = device.get('adv_data')
                        mfg_id = device.get('manufacturer_id')
                        if adv_bytes and mfg_id:
                            protocol = get_protocol_by_manufacturer_id(mfg_id)
                            adv = protocol.parse_advertising_data(adv_bytes)
                            from datetime import datetime, timezone
                            state_payload = json.dumps({
                                "battery_pct": adv.battery_pct,
                                "battery_mv": adv.battery_mv,
                                "temperature": adv.temperature,
                                "last_update": datetime.now(timezone.utc).isoformat()
                            })
                            if self.client:
                                self.client.publish(self.state_topic, state_payload, retain=True)
                                self.logger.info(f"Published state: {adv.battery_pct}% ({adv.battery_mv}mV) {adv.temperature}°C")
                            success = True
                            break

                except Exception as e:
                    self.logger.error(f"Battery scan error: {e}")
                finally:
                    self.ble_lock.release()

                if success:
                    break

                backoff = initial_backoff * (2 ** attempt)
                self.logger.warning(f"Device not found, retry {attempt + 1}/{max_retries} in {backoff}s")
                time.sleep(backoff)

            if not success:
                self.logger.warning(f"Battery scan failed after {max_retries} attempts, will retry next interval")

            time.sleep(interval)
    
    def start(self):
        """Start the MQTT controller."""
        mqtt_config = self.settings['mqtt']
        
        # Create MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Set LWT so HA marks device offline if we disconnect
        self.client.will_set(self.availability_topic, "offline", retain=True)
        
        # Set credentials if provided
        if mqtt_config.get('username') and mqtt_config.get('password'):
            self.client.username_pw_set(
                mqtt_config['username'], 
                mqtt_config['password']
            )
        
        try:
            self.logger.info(f"Connecting to MQTT broker: {mqtt_config['broker']}:{mqtt_config['port']}")
            self.client.connect(
                mqtt_config['broker'], 
                mqtt_config['port'], 
                60
            )
            
            # Start battery publisher thread
            battery_thread = threading.Thread(target=self._battery_publish_loop, daemon=True)
            battery_thread.start()

            # Start loop
            self.logger.info("Starting MQTT controller...")
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            if self.client:
                self.client.publish(self.availability_topic, "offline", retain=True)
                self.client.disconnect()
        except Exception as e:
            self.logger.error(f"Error starting controller: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    controller = EInkController()
    controller.start()


if __name__ == '__main__':
    main()
