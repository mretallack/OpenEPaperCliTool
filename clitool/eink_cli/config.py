"""Configuration file parser for YAML input."""

import yaml
from pathlib import Path
from typing import Dict, Any, List


class ConfigError(Exception):
    """Configuration validation error."""
    pass


def load_config(config_file: Path) -> Dict[str, Any]:
    """Load and validate YAML configuration file.
    
    Args:
        config_file: Path to YAML configuration file
        
    Returns:
        Dict containing validated configuration
        
    Raises:
        ConfigError: If configuration is invalid
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML syntax: {e}")
    except FileNotFoundError:
        raise ConfigError(f"Configuration file not found: {config_file}")
    except Exception as e:
        raise ConfigError(f"Error reading configuration file: {e}")
    
    if not isinstance(config, dict):
        raise ConfigError("Configuration must be a YAML object/dictionary")
    
    # Validate and set defaults
    config = _validate_config(config)
    
    return config


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration structure and set defaults.
    
    Args:
        config: Raw configuration dictionary
        
    Returns:
        Validated configuration with defaults applied
        
    Raises:
        ConfigError: If configuration is invalid
    """
    # Ensure required sections exist
    if 'device' not in config:
        raise ConfigError("Missing required 'device' section")
    
    # Validate device section
    device = config['device']
    if not isinstance(device, dict):
        raise ConfigError("'device' section must be an object")
    
    if 'mac_address' not in device:
        raise ConfigError("Device MAC address is required")
    
    # Validate MAC address format
    mac = device['mac_address'].upper()
    if not _is_valid_mac(mac):
        raise ConfigError(f"Invalid MAC address format: {device['mac_address']}")
    device['mac_address'] = mac
    
    # Set device defaults
    device.setdefault('protocol', 'auto')
    
    # Validate protocol if specified
    if device['protocol'] not in ['auto', 'oepl', 'atc']:
        raise ConfigError(f"Invalid protocol: {device['protocol']}. Must be 'auto', 'oepl', or 'atc'")
    
    # Validate display section
    display = config.setdefault('display', {})
    if not isinstance(display, dict):
        raise ConfigError("'display' section must be an object")
    
    # Set display defaults
    display.setdefault('background', 'white')
    display.setdefault('rotate', 0)
    
    # Validate display settings
    if display['background'] not in ['white', 'black', 'red', 'yellow']:
        raise ConfigError(f"Invalid background color: {display['background']}")
    
    if display['rotate'] not in [0, 90, 180, 270]:
        raise ConfigError(f"Invalid rotation: {display['rotate']}. Must be 0, 90, 180, or 270")
    
    # Validate content section
    content = config.setdefault('content', [])
    if not isinstance(content, list):
        raise ConfigError("'content' section must be a list")
    
    # Validate each content element
    for i, element in enumerate(content):
        try:
            _validate_element(element)
        except ConfigError as e:
            raise ConfigError(f"Content element {i + 1}: {e}")
    
    return config


def _validate_element(element: Dict[str, Any]) -> None:
    """Validate a single content element.
    
    Args:
        element: Content element dictionary
        
    Raises:
        ConfigError: If element is invalid
    """
    if not isinstance(element, dict):
        raise ConfigError("Content element must be an object")
    
    if 'type' not in element:
        raise ConfigError("Content element missing required 'type' field")
    
    element_type = element['type']
    
    # Validate based on element type
    if element_type == 'text':
        _validate_text_element(element)
    elif element_type == 'rectangle':
        _validate_rectangle_element(element)
    elif element_type == 'line':
        _validate_line_element(element)
    else:
        raise ConfigError(f"Unknown element type: {element_type}")


def _validate_text_element(element: Dict[str, Any]) -> None:
    """Validate text element."""
    required_fields = ['text', 'x', 'y']
    for field in required_fields:
        if field not in element:
            raise ConfigError(f"Text element missing required field: {field}")
    
    # Set defaults
    element.setdefault('font_size', 16)
    element.setdefault('color', 'black')
    element.setdefault('anchor', 'top_left')
    
    # Validate types
    if not isinstance(element['text'], str):
        raise ConfigError("Text field must be a string")
    
    if not isinstance(element['x'], (int, float)):
        raise ConfigError("X coordinate must be a number")
    
    if not isinstance(element['y'], (int, float)):
        raise ConfigError("Y coordinate must be a number")
    
    if not isinstance(element['font_size'], (int, float)) or element['font_size'] <= 0:
        raise ConfigError("Font size must be a positive number")


def _validate_rectangle_element(element: Dict[str, Any]) -> None:
    """Validate rectangle element."""
    required_fields = ['x', 'y', 'width', 'height']
    for field in required_fields:
        if field not in element:
            raise ConfigError(f"Rectangle element missing required field: {field}")
    
    # Set defaults
    element.setdefault('color', 'black')
    element.setdefault('filled', True)
    
    # Validate types
    for field in required_fields:
        if not isinstance(element[field], (int, float)) or element[field] < 0:
            raise ConfigError(f"Rectangle {field} must be a non-negative number")


def _validate_line_element(element: Dict[str, Any]) -> None:
    """Validate line element."""
    required_fields = ['x1', 'y1', 'x2', 'y2']
    for field in required_fields:
        if field not in element:
            raise ConfigError(f"Line element missing required field: {field}")
    
    # Set defaults
    element.setdefault('color', 'black')
    element.setdefault('width', 1)
    
    # Validate types
    for field in required_fields:
        if not isinstance(element[field], (int, float)):
            raise ConfigError(f"Line {field} must be a number")
    
    if not isinstance(element['width'], (int, float)) or element['width'] <= 0:
        raise ConfigError("Line width must be a positive number")


def _is_valid_mac(mac: str) -> bool:
    """Check if MAC address format is valid.
    
    Args:
        mac: MAC address string
        
    Returns:
        True if valid MAC address format
    """
    import re
    # Accept formats: AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF
    pattern = r'^([0-9A-F]{2}[:-]){5}([0-9A-F]{2})$'
    return bool(re.match(pattern, mac))


def create_example_config() -> Dict[str, Any]:
    """Create an example configuration for reference.
    
    Returns:
        Example configuration dictionary
    """
    return {
        'device': {
            'mac_address': 'AA:BB:CC:DD:EE:FF',
            'protocol': 'oepl'
        },
        'display': {
            'background': 'white',
            'rotate': 0
        },
        'content': [
            {
                'type': 'text',
                'text': 'Hello World!',
                'x': 10,
                'y': 10,
                'font_size': 24,
                'color': 'black'
            },
            {
                'type': 'rectangle',
                'x': 50,
                'y': 50,
                'width': 100,
                'height': 30,
                'color': 'red',
                'filled': True
            },
            {
                'type': 'line',
                'x1': 0,
                'y1': 0,
                'x2': 100,
                'y2': 50,
                'color': 'black',
                'width': 2
            }
        ]
    }