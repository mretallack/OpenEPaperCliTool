#!/usr/bin/env python3
"""MQTT Controller for EInk Display Updates."""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

import paho.mqtt.client as mqtt
import yaml


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
    
    def _send_to_device(self, config_file: str) -> bool:
        """Send configuration to device using CLI tool."""
        cli_config = self.settings['cli']
        command = cli_config['command']
        working_dir = cli_config['working_directory']
        
        # Build command
        cmd = f"{command} send {config_file}"
        
        try:
            self.logger.info(f"Executing: {cmd}")
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.logger.info("Successfully sent to device")
                return True
            else:
                self.logger.error(f"CLI command failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("CLI command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error executing CLI command: {e}")
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
            success = self._send_to_device(config_file)
            
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