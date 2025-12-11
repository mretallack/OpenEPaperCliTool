#!/usr/bin/env python3
"""Test MQTT publisher for controller testing."""

import json
import sys
from datetime import datetime

import paho.mqtt.client as mqtt
import yaml


def load_settings():
    """Load settings from settings.yaml."""
    try:
        with open('settings.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: settings.yaml not found")
        sys.exit(1)


def publish_test_message():
    """Publish test message to MQTT broker."""
    settings = load_settings()
    mqtt_config = settings['mqtt']
    
    # Test message payload
    test_payload = {
        "belle_battery": "85",
        "weather_condition": "Partly Cloudy", 
        "temperature": "22",
        "rubbish_days": "3",
        "recycling_days": "10",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Create MQTT client
    client = mqtt.Client()
    
    # Set credentials if provided
    if mqtt_config.get('username') and mqtt_config.get('password'):
        client.username_pw_set(mqtt_config['username'], mqtt_config['password'])
    
    try:
        # Connect and publish
        print(f"Connecting to {mqtt_config['broker']}:{mqtt_config['port']}")
        client.connect(mqtt_config['broker'], mqtt_config['port'], 60)
        
        topic = mqtt_config['topic']
        payload = json.dumps(test_payload, indent=2)
        
        print(f"Publishing to topic: {topic}")
        print(f"Payload: {payload}")
        
        result = client.publish(topic, payload)
        
        if result.rc == 0:
            print("✓ Message published successfully")
        else:
            print(f"✗ Failed to publish message: {result.rc}")
            
        client.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    publish_test_message()