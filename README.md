# EInk Display CLI Tool

A Python command-line tool for sending content to eink displays over Bluetooth Low Energy (BLE). This tool allows you to create and send custom content to OpenEPaperLink devices using YAML configuration files.

## Features

- **BLE Communication**: Direct Bluetooth communication with eink displays
- **YAML Configuration**: Declarative content definition using YAML files
- **Protocol Support**: Compatible with both ATC and OEPL firmware
- **Image Generation**: Built-in support for text, shapes, and graphics
- **Device Discovery**: Automatic discovery of nearby BLE devices
- **Standalone Operation**: No Home Assistant or WiFi AP required

## Installation

```bash
cd clitool
pip install -r requirements.txt
pip install -e .
```

## Quick Start

1. **Discover devices**:
   ```bash
   eink-cli discover
   ```

2. **Create a configuration file** (`example.yaml`):
   ```yaml
   device:
     mac_address: "AA:BB:CC:DD:EE:FF"
     protocol: "oepl"
   
   display:
     background: "white"
   
   content:
     - type: "text"
       text: "Hello World!"
       x: 10
       y: 10
       font_size: 24
       color: "black"
   ```

3. **Send content to device**:
   ```bash
   eink-cli send example.yaml
   ```

## Configuration Format

### Device Configuration
```yaml
device:
  mac_address: "AA:BB:CC:DD:EE:FF"  # Required: BLE MAC address
  protocol: "oepl"                   # Optional: "oepl" or "atc" (auto-detected)
```

### Display Settings
```yaml
display:
  background: "white"    # Background color: "white", "black", "red", "yellow"
  rotate: 0             # Rotation: 0, 90, 180, 270 degrees
```

### Content Elements

#### Text
```yaml
- type: "text"
  text: "Hello World"
  x: 10                 # X position in pixels
  y: 10                 # Y position in pixels
  font_size: 24         # Font size
  color: "black"        # Text color
  anchor: "top_left"    # Text anchor point
```

#### Rectangle
```yaml
- type: "rectangle"
  x: 50
  y: 50
  width: 100
  height: 30
  color: "red"
  filled: true          # true for filled, false for outline
```

#### Line
```yaml
- type: "line"
  x1: 0
  y1: 0
  x2: 100
  y2: 50
  color: "black"
  width: 2              # Line width in pixels
```

## Commands

### `discover`
Scan for nearby BLE devices and display their information.

```bash
eink-cli discover [--timeout SECONDS]
```

### `send`
Send content to a device using a YAML configuration file.

```bash
eink-cli send CONFIG_FILE [OPTIONS]

Options:
  --device MAC          Override device MAC address
  --protocol PROTOCOL   Override protocol (oepl/atc)
  --timeout SECONDS     Connection timeout (default: 30)
  --retries NUMBER      Number of upload retry attempts (default: 3)
  --ttl SECONDS         Time to live - how long device sleeps before next check-in (default: 0)
  --verbose            Enable verbose output
```

### `ping`
Test connectivity to a specific device.

```bash
eink-cli ping MAC_ADDRESS [--protocol PROTOCOL] [--timeout SECONDS]
```

### `generate`
Generate an image from configuration without sending to device.

```bash
eink-cli generate CONFIG_FILE --output IMAGE_FILE [--format FORMAT]
```

## Examples

See the `examples/` directory for sample configuration files:

- `simple_text.yaml` - Basic text display
- `weather_display.yaml` - Weather information layout
- `status_board.yaml` - Multi-element status display

## Supported Colors

The available colors depend on your device's color scheme:

- **Monochrome (BW)**: `black`, `white`
- **Three-color (BWR)**: `black`, `white`, `red`
- **Three-color (BWY)**: `black`, `white`, `yellow`

## Troubleshooting

### Connection Issues

**Device Not Found / Connection Failed**
- Ensure the device is powered on and in Bluetooth range (typically 10-30 feet)
- Check that Bluetooth is enabled on your system
- Verify the MAC address is correct (use `eink-cli discover` to find devices)
- Try restarting Bluetooth on your system
- Move closer to the device and try again
- Ensure no other applications are connected to the device

**"Device Disappeared" Errors**
The tool now automatically retries connections with improved logic:
- **6 connection attempts** with exponential backoff (1s, 2s, 4s, 8s, 16s delays)
- **Fresh device scanning** between retry attempts
- **Configurable upload retries** (default: 3 attempts)

To increase retry attempts:
```bash
eink-cli send config.yaml --retries 5
```

**Intermittent Connection Issues**
- BLE connections can be unreliable - the retry mechanism handles most issues automatically
- If problems persist, try:
  - Restarting the eink device
  - Moving to a different location (away from WiFi routers, microwaves)
  - Using `--verbose` flag to see detailed connection logs

### Upload Issues

**Upload Timeouts**
- Large images may take longer - increase timeout: `--timeout 60`
- The tool automatically retries failed uploads
- OEPL devices use faster "direct write" protocol

**Image Not Displaying**
- Verify the content fits within the display dimensions
- Check that colors are supported by the device
- Ensure the protocol matches your device firmware
- Try generating the image first: `eink-cli generate config.yaml -o test.png`

## Development

To contribute to this project:

1. Clone the repository
2. Install development dependencies: `pip install -r requirements.txt`
3. Run tests: `python -m pytest tests/`
4. Follow the existing code style and add tests for new features

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

This project is based on the [OpenEPaperLink Home Assistant integration](https://github.com/OpenEPaperLink/Home_Assistant_Integration) and uses components from that project under the Apache License 2.0.

## Acknowledgments

- Based on the OpenEPaperLink Home Assistant integration
- Supports ATC and OEPL firmware protocols
- Uses BLE communication libraries from the Home Assistant ecosystem