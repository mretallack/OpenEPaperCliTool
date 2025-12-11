"""Simplified image generation for CLI tool."""

import io
import logging
from typing import Dict, Any, Tuple
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import numpy as np

_LOGGER = logging.getLogger(__name__)


class ImageGenerator:
    """Simplified image generator for eink displays."""
    
    def __init__(self):
        """Initialize image generator."""
        self._default_font = None
        self._fonts = {}
    
    async def generate_image(self, config: Dict[str, Any], device_info: Dict[str, Any]) -> bytes:
        """Generate image from configuration.
        
        Args:
            config: Configuration dictionary from YAML
            device_info: Device information with dimensions
            
        Returns:
            JPEG image data as bytes
        """
        width = device_info['width']
        height = device_info['height']
        color_scheme = device_info.get('color_scheme', 'bw')
        
        _LOGGER.debug(f"Generating {width}x{height} image for {color_scheme} display")
        
        # Get display settings
        display_config = config.get('display', {})
        background = display_config.get('background', 'white')
        rotate = display_config.get('rotate', 0)
        
        # Create base image
        if rotate in (90, 270):
            # Swap dimensions for rotation
            img = Image.new('RGB', (height, width), color=self._get_color(background, color_scheme))
        else:
            img = Image.new('RGB', (width, height), color=self._get_color(background, color_scheme))
        
        draw = ImageDraw.Draw(img)
        
        # Draw content elements
        content = config.get('content', [])
        for element in content:
            try:
                await self._draw_element(draw, element, color_scheme, img.size)
            except Exception as e:
                _LOGGER.error(f"Error drawing element {element.get('type', 'unknown')}: {e}")
                continue
        
        # Apply rotation if needed
        if rotate:
            img = img.rotate(-rotate, expand=True)  # PIL rotates counter-clockwise
        
        # Convert to JPEG
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=95)
        return img_byte_arr.getvalue()
    
    async def _draw_element(self, draw: ImageDraw.Draw, element: Dict[str, Any], 
                          color_scheme: str, img_size: Tuple[int, int]) -> None:
        """Draw a single element on the image.
        
        Args:
            draw: PIL ImageDraw object
            element: Element configuration
            color_scheme: Device color scheme
            img_size: Image dimensions (width, height)
        """
        element_type = element['type']
        
        if element_type == 'text':
            await self._draw_text(draw, element, color_scheme, img_size)
        elif element_type == 'rectangle':
            self._draw_rectangle(draw, element, color_scheme)
        elif element_type == 'line':
            self._draw_line(draw, element, color_scheme)
        else:
            _LOGGER.warning(f"Unknown element type: {element_type}")
    
    async def _draw_text(self, draw: ImageDraw.Draw, element: Dict[str, Any], 
                        color_scheme: str, img_size: Tuple[int, int]) -> None:
        """Draw text element."""
        text = element['text']
        x = element['x']
        y = element['y']
        font_size = element.get('font_size', 16)
        color = self._get_color(element.get('color', 'black'), color_scheme)
        anchor = element.get('anchor', 'top_left')
        
        # Get font
        font = self._get_font(font_size)
        
        # Convert anchor to PIL anchor
        pil_anchor = self._convert_anchor(anchor)
        
        # Draw text
        draw.text((x, y), text, fill=color, font=font, anchor=pil_anchor)
    
    def _draw_rectangle(self, draw: ImageDraw.Draw, element: Dict[str, Any], color_scheme: str) -> None:
        """Draw rectangle element."""
        x = element['x']
        y = element['y']
        width = element['width']
        height = element['height']
        color = self._get_color(element.get('color', 'black'), color_scheme)
        filled = element.get('filled', True)
        
        coords = [x, y, x + width, y + height]
        
        if filled:
            draw.rectangle(coords, fill=color)
        else:
            draw.rectangle(coords, outline=color, width=1)
    
    def _draw_line(self, draw: ImageDraw.Draw, element: Dict[str, Any], color_scheme: str) -> None:
        """Draw line element."""
        x1 = element['x1']
        y1 = element['y1']
        x2 = element['x2']
        y2 = element['y2']
        color = self._get_color(element.get('color', 'black'), color_scheme)
        width = element.get('width', 1)
        
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    
    def _get_color(self, color_name: str, color_scheme: str) -> Tuple[int, int, int]:
        """Get RGB color tuple for color name and scheme.
        
        Args:
            color_name: Color name ('black', 'white', 'red', 'yellow')
            color_scheme: Device color scheme
            
        Returns:
            RGB color tuple
        """
        # Basic color mapping
        colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'yellow': (255, 255, 0),
        }
        
        # Validate color is supported by scheme
        if color_scheme == 'bw' and color_name not in ['black', 'white']:
            _LOGGER.warning(f"Color '{color_name}' not supported in BW scheme, using black")
            color_name = 'black'
        elif color_scheme == 'bwr' and color_name not in ['black', 'white', 'red']:
            _LOGGER.warning(f"Color '{color_name}' not supported in BWR scheme, using black")
            color_name = 'black'
        elif color_scheme == 'bwy' and color_name not in ['black', 'white', 'yellow']:
            _LOGGER.warning(f"Color '{color_name}' not supported in BWY scheme, using black")
            color_name = 'black'
        
        return colors.get(color_name, (0, 0, 0))
    
    def _get_font(self, size: int) -> ImageFont.ImageFont:
        """Get font for given size.
        
        Args:
            size: Font size in pixels
            
        Returns:
            PIL ImageFont object
        """
        if size in self._fonts:
            return self._fonts[size]
        
        try:
            # Try to load a system font
            font = ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            try:
                # Fallback to default font
                font = ImageFont.load_default()
            except Exception:
                # Last resort - create a basic font
                font = ImageFont.load_default()
        
        self._fonts[size] = font
        return font
    
    def _convert_anchor(self, anchor: str) -> str:
        """Convert anchor name to PIL anchor format.
        
        Args:
            anchor: Anchor name
            
        Returns:
            PIL anchor string
        """
        anchor_map = {
            'top_left': 'lt',
            'top_center': 'mt',
            'top_right': 'rt',
            'center_left': 'lm',
            'center': 'mm',
            'center_right': 'rm',
            'bottom_left': 'lb',
            'bottom_center': 'mb',
            'bottom_right': 'rb',
        }
        
        return anchor_map.get(anchor, 'lt')