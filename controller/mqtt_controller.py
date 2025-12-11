#!/usr/bin/env python3
"""MQTT Controller for EInk Display Updates."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

import paho.mqtt.client as mqtt
import yaml

# Add clitool to path for importing
sys.path.insert(0, '../clitool')
from eink_cli.config import load_config
from eink_cli.device import DeviceManager
from eink_cli.imagegen import ImageGenerator


class EInkController:
    """MQTT controller for eink display updates."""
    
    def __init__(self, settings_file: str = "settings.yaml"):
        """Initialize controller with settings."""
        self.settings = self._load_settings(settings_file)
        self.template = self._load_template()
        self.client = None
        
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
            self.logger.error(f"Settings file {settings_file} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing settings file: {e}")
            sys.exit(1)
    
    def _load_template(self) -> str:
        """Load template file as string."""
        template_file = self.settings['files']['template']
        try:
            with open(template_file, 'r') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Template file {template_file} not found")
            sys.exit(1)
    
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
        """Send configuration to device using CLI modules."""
        try:
            self.logger.info(f"Loading config: {config_file}")
            config = load_config(Path(config_file))
            
            mac_address = config['device']['mac_address']
            protocol = config['device'].get('protocol', 'auto')
            
            self.logger.info(f"Connecting to device {mac_address}...")
            
            # Initialize device manager and connect
            device_manager = DeviceManager()
            device_info = await device_manager.connect_device(
                mac_address, 
                protocol=protocol if protocol != 'auto' else None,
                timeout=30
            )
            
            self.logger.info(f"Connected to {device_info['name']} ({device_info['protocol']})")
            
            # Generate image
            self.logger.info("Generating image...")
            image_gen = ImageGenerator()
            image_data = await image_gen.generate_image(config, device_info)
            
            # Upload image
            self.logger.info("Uploading image...")
            success = await device_manager.upload_image(image_data, device_info)
            
            if success:
                self.logger.info("Successfully sent to device")
                return True
            else:
                self.logger.error("Failed to send image")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending to device: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            topic = self.settings['mqtt']['topic']
            client.subscribe(topic)
            self.logger.info(f"Subscribed to topic: {topic}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for MQTT message received."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            self.logger.info(f"Received message on {topic}: {payload}")
            
            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                self.logger.error("Invalid JSON in message payload")
                return
            
            # Replace placeholders in template
            config_content = self._replace_placeholders(self.template, data)
            
            # Write device configuration
            config_file = self._write_device_config(config_content)
            
            # Send to device
            import asyncio
            success = asyncio.run(self._send_to_device(config_file))
            
            if success:
                self.logger.info("Display update completed successfully")
            else:
                self.logger.error("Display update failed")
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection."""
        self.logger.info("Disconnected from MQTT broker")
    
    def start(self):
        """Start the MQTT controller."""
        mqtt_config = self.settings['mqtt']
        
        # Create MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Set credentials if provided
        if mqtt_config.get('username') and mqtt_config.get('password'):
            self.client.username_pw_set(
                mqtt_config['username'], 
                mqtt_config['password']
            )
        
        try:
            # Connect to broker
            self.logger.info(f"Connecting to MQTT broker: {mqtt_config['broker']}:{mqtt_config['port']}")
            self.client.connect(
                mqtt_config['broker'], 
                mqtt_config['port'], 
                60
            )
            
            # Start loop
            self.logger.info("Starting MQTT controller...")
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            if self.client:
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