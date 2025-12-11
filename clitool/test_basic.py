#!/usr/bin/env python3
"""Basic test of CLI tool functionality."""

import asyncio
import sys
from pathlib import Path

# Add the package to path
sys.path.insert(0, str(Path(__file__).parent))

from eink_cli.config import load_config, create_example_config
from eink_cli.imagegen import ImageGenerator


async def test_config_loading():
    """Test configuration loading."""
    print("Testing configuration loading...")
    
    # Create example config
    example_config = create_example_config()
    print(f"Example config: {example_config}")
    
    # Test image generation
    print("Testing image generation...")
    image_gen = ImageGenerator()
    
    # Mock device info
    device_info = {
        'width': 296,
        'height': 128,
        'color_scheme': 'bwr',
        'protocol': 'test'
    }
    
    try:
        image_data = await image_gen.generate_image(example_config, device_info)
        print(f"Generated image: {len(image_data)} bytes")
        
        # Save test image
        with open('test_output.jpg', 'wb') as f:
            f.write(image_data)
        print("Test image saved as test_output.jpg")
        
    except Exception as e:
        print(f"Error generating image: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_config_loading())