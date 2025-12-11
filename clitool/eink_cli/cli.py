#!/usr/bin/env python3
"""Main CLI interface for eink display tool."""

import asyncio
import logging
import sys
from pathlib import Path

import click

from .config import load_config
from .device import DeviceManager
from .imagegen import ImageGenerator


# Configure logging
def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx, verbose):
    """EInk CLI Tool - Send content to eink displays over BLE."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    setup_logging(verbose)


@cli.command()
@click.option('--timeout', '-t', default=10, help='Discovery timeout in seconds')
@click.pass_context
def discover(ctx, timeout):
    """Discover nearby BLE eink devices."""
    verbose = ctx.obj['verbose']
    
    async def _discover():
        device_manager = DeviceManager()
        devices = await device_manager.discover_devices(timeout=timeout)
        
        if not devices:
            click.echo("No devices found.")
            return
        
        click.echo(f"Found {len(devices)} device(s):")
        for device in devices:
            click.echo(f"  {device['mac_address']} - {device['name']} ({device['protocol']})")
            if verbose:
                click.echo(f"    RSSI: {device.get('rssi', 'Unknown')} dBm")
                click.echo(f"    Manufacturer ID: 0x{device.get('manufacturer_id', 0):04x}")
    
    try:
        asyncio.run(_discover())
    except KeyboardInterrupt:
        click.echo("\nDiscovery cancelled.")
    except Exception as e:
        click.echo(f"Error during discovery: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True, path_type=Path))
@click.option('--device', '-d', help='Override device MAC address')
@click.option('--protocol', '-p', type=click.Choice(['oepl', 'atc']), help='Override protocol')
@click.option('--timeout', '-t', default=30, help='Connection timeout in seconds')
@click.pass_context
def send(ctx, config_file, device, protocol, timeout):
    """Send content to device using YAML configuration."""
    verbose = ctx.obj['verbose']
    
    async def _send():
        try:
            # Load configuration
            config = load_config(config_file)
            
            # Override device settings if provided
            if device:
                config['device']['mac_address'] = device
            if protocol:
                config['device']['protocol'] = protocol
            
            # Validate required fields
            if 'mac_address' not in config['device']:
                raise ValueError("Device MAC address is required")
            
            mac_address = config['device']['mac_address']
            device_protocol = config['device'].get('protocol', 'auto')
            
            click.echo(f"Connecting to device {mac_address}...")
            
            # Initialize device manager and connect
            device_manager = DeviceManager()
            device_info = await device_manager.connect_device(
                mac_address, 
                protocol=device_protocol if device_protocol != 'auto' else None,
                timeout=timeout
            )
            
            click.echo(f"Connected to {device_info['name']} ({device_info['protocol']})")
            click.echo(f"Display: {device_info['width']}x{device_info['height']} pixels")
            
            # Generate image
            click.echo("Generating image...")
            image_gen = ImageGenerator()
            image_data = await image_gen.generate_image(config, device_info)
            
            # Upload image
            click.echo("Uploading image...")
            success = await device_manager.upload_image(image_data, device_info)
            
            if success:
                click.echo("✓ Image sent successfully!")
            else:
                click.echo("✗ Failed to send image", err=True)
                sys.exit(1)
                
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    try:
        asyncio.run(_send())
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled.")
        sys.exit(1)


@cli.command()
@click.argument('mac_address')
@click.option('--protocol', '-p', type=click.Choice(['oepl', 'atc']), help='Device protocol')
@click.option('--timeout', '-t', default=10, help='Connection timeout in seconds')
@click.pass_context
def ping(ctx, mac_address, protocol, timeout):
    """Test connectivity to a specific device."""
    verbose = ctx.obj['verbose']
    
    async def _ping():
        try:
            click.echo(f"Pinging device {mac_address}...")
            
            device_manager = DeviceManager()
            device_info = await device_manager.connect_device(
                mac_address, 
                protocol=protocol,
                timeout=timeout
            )
            
            click.echo(f"✓ Device responded: {device_info['name']} ({device_info['protocol']})")
            click.echo(f"  Display: {device_info['width']}x{device_info['height']} pixels")
            click.echo(f"  Color scheme: {device_info['color_scheme']}")
            
        except Exception as e:
            click.echo(f"✗ Ping failed: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    try:
        asyncio.run(_ping())
    except KeyboardInterrupt:
        click.echo("\nPing cancelled.")
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', required=True, help='Output image file path')
@click.option('--format', '-f', default='PNG', type=click.Choice(['PNG', 'JPEG']), help='Output format')
@click.option('--width', '-w', type=int, help='Override display width')
@click.option('--height', '-h', type=int, help='Override display height')
@click.pass_context
def generate(ctx, config_file, output, format, width, height):
    """Generate image from configuration without sending to device."""
    verbose = ctx.obj['verbose']
    
    async def _generate():
        try:
            # Load configuration
            config = load_config(config_file)
            
            # Create mock device info for image generation
            device_info = {
                'width': width or 296,
                'height': height or 128,
                'color_scheme': 'bwr',
                'protocol': 'mock'
            }
            
            click.echo(f"Generating {device_info['width']}x{device_info['height']} image...")
            
            # Generate image
            image_gen = ImageGenerator()
            image_data = await image_gen.generate_image(config, device_info)
            
            # Save image
            from PIL import Image
            import io
            
            image = Image.open(io.BytesIO(image_data))
            image.save(output, format=format)
            
            click.echo(f"✓ Image saved to {output}")
            
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    try:
        asyncio.run(_generate())
    except KeyboardInterrupt:
        click.echo("\nGeneration cancelled.")
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()