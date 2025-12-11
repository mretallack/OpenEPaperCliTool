# EInk Display CLI Tool Design

## Overview
A Python CLI tool for sending content to eink displays over BLE, based on the Home Assistant OpenEPaperLink integration. The tool accepts YAML configuration files describing what to render and sends the generated images to displays via Bluetooth Low Energy.

## Architecture

### Core Components

1. **CLI Interface** (`cli.py`)
   - Argument parsing for YAML file input
   - Device discovery and selection
   - Main orchestration logic

2. **YAML Configuration Parser** (`config.py`)
   - Parse YAML files describing display content
   - Validate configuration structure
   - Convert to internal representation

3. **BLE Communication** (`ble/`)
   - Reuse existing BLE modules from HA integration
   - Device discovery and connection management
   - Protocol handling (ATC/OEPL firmware support)

4. **Image Generation** (`imagegen.py`)
   - Simplified version of HA integration's image generation
   - Support for text, shapes, and basic elements
   - No Home Assistant dependencies

5. **Device Management** (`device.py`)
   - Device metadata handling
   - Color scheme and capability detection
   - Display dimension management

### Key Features

- **BLE-only support**: No WiFi/AP mode dependencies
- **YAML-driven**: Declarative configuration for display content
- **Protocol support**: Both ATC and OEPL firmware protocols
- **Minimal dependencies**: Standalone operation without Home Assistant
- **Image generation**: Text, shapes, basic graphics support

## YAML Configuration Format

```yaml
device:
  mac_address: "AA:BB:CC:DD:EE:FF"  # BLE MAC address
  protocol: "oepl"  # or "atc"
  
display:
  width: 296
  height: 128
  color_scheme: "bwr"  # black/white/red
  background: "white"
  rotate: 0

content:
  - type: "text"
    text: "Hello World"
    x: 10
    y: 10
    font_size: 24
    color: "black"
    
  - type: "rectangle"
    x: 50
    y: 50
    width: 100
    height: 30
    color: "red"
    filled: true
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. Set up project structure and dependencies
2. Extract and adapt BLE modules from HA integration
3. Create basic CLI interface with argument parsing
4. Implement YAML configuration parser

### Phase 2: Image Generation
1. Create simplified image generation engine
2. Support basic elements: text, rectangles, lines
3. Handle color schemes and device capabilities
4. Generate PIL images for BLE transmission

### Phase 3: BLE Integration
1. Integrate BLE connection management
2. Support device discovery and interrogation
3. Implement image upload protocols
4. Handle both ATC and OEPL firmware types

### Phase 4: Testing & Documentation
1. Test with real devices
2. Create comprehensive README
3. Add example YAML configurations
4. Error handling and validation

## Dependencies

### Core Dependencies
- `bleak` - BLE communication
- `bleak-retry-connector` - Connection reliability
- `Pillow` - Image processing
- `numpy` - Array operations for image data
- `PyYAML` - YAML parsing
- `click` - CLI interface

### Optional Dependencies
- `qrcode[pil]` - QR code generation
- `python-resize-image` - Image resizing utilities

## File Structure

```
clitool/
├── README.md
├── requirements.txt
├── setup.py
├── eink_cli/
│   ├── __init__.py
│   ├── cli.py              # Main CLI interface
│   ├── config.py           # YAML configuration parser
│   ├── device.py           # Device management
│   ├── imagegen.py         # Image generation engine
│   └── ble/                # BLE communication modules
│       ├── __init__.py
│       ├── connection.py   # BLE connection management
│       ├── protocols.py    # Protocol implementations
│       ├── image_upload.py # Image upload handling
│       └── discovery.py    # Device discovery
├── examples/
│   ├── simple_text.yaml
│   ├── weather_display.yaml
│   └── status_board.yaml
└── tests/
    ├── test_config.py
    ├── test_imagegen.py
    └── test_ble.py
```

## Usage Examples

### Basic Usage
```bash
# Send content to device
eink-cli send config.yaml

# Discover devices
eink-cli discover

# Test connection
eink-cli ping AA:BB:CC:DD:EE:FF
```

### Advanced Usage
```bash
# Override device settings
eink-cli send config.yaml --device AA:BB:CC:DD:EE:FF --protocol oepl

# Generate image only (no send)
eink-cli generate config.yaml --output image.png

# Verbose output
eink-cli send config.yaml --verbose
```

## Error Handling

- Validate YAML configuration before processing
- Check device connectivity before image generation
- Provide clear error messages for common issues
- Graceful handling of BLE connection failures
- Timeout handling for device operations

## Future Enhancements

- Support for more complex graphics elements
- Template system for reusable configurations
- Batch operations for multiple devices
- Configuration validation schemas
- Interactive device setup wizard