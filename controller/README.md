# EInk MQTT Controller

MQTT-based controller for updating eink displays. Listens for MQTT messages and automatically generates and sends content to eink displays.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure settings:**
   Edit `settings.yaml` with your MQTT broker details and device settings.

3. **Create template:**
   Edit `template.yaml` with your display layout and placeholders.

## Configuration

### settings.yaml
```yaml
mqtt:
  broker: "localhost"
  port: 1883
  topic: "eink/display/update"

cli:
  command: "python3 -m eink_cli.cli"
  working_directory: "../clitool"

files:
  template: "template.yaml"
  output: "device.yaml"
```

### template.yaml
Use `{key}` placeholders that will be replaced with MQTT message data:
```yaml
device:
  mac_address: "{mac_address}"
  protocol: "{protocol}"

content:
  - type: "text"
    text: "{title}"
    x: 10
    y: 10
```

## Usage

1. **Start the controller:**
   ```bash
   python3 mqtt_controller.py
   ```

2. **Send MQTT message:**
   ```bash
   mosquitto_pub -h localhost -t "eink/display/update" -m '{
     "mac_address": "74:C8:C6:CB:05:72",
     "protocol": "atc",
     "title": "Hello World",
     "message": "MQTT Update",
     "timestamp": "2024-01-01 12:00:00"
   }'
   ```

## Message Format

Send JSON messages to the configured MQTT topic with key-value pairs that match your template placeholders:

```json
{
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "protocol": "oepl",
  "title": "Status Update",
  "message": "System Online",
  "timestamp": "2024-01-01 12:00:00"
}
```

## How It Works

1. Controller connects to MQTT broker
2. Subscribes to configured topic
3. Receives JSON message
4. Replaces placeholders in template with message data
5. Writes generated config to `device.yaml`
6. Calls eink CLI tool to send image to device