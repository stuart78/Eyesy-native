"""
pygame compatibility shim for Eyesy simulator
Renders pygame commands to PIL Image instead of display
"""

from PIL import Image, ImageDraw, ImageFont
import math
import numpy as np
import os

class Surface:
    def __init__(self, size):
        self.width, self.height = size
        self.image = Image.new('RGB', size, (0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    def fill(self, color):
        """Fill surface with solid color"""
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            # Create new image with the fill color
            self.image = Image.new('RGB', (self.width, self.height), tuple(color[:3]))
            # Create new ImageDraw object
            self.draw = ImageDraw.Draw(self.image)

    def get_size(self):
        """Return surface dimensions"""
        return (self.width, self.height)

    def get_image(self):
        """Get PIL Image for export"""
        return self.image

    def blit(self, source, pos):
        """Draw another surface onto this one at the given position"""
        if hasattr(source, 'image'):
            # It's another Surface
            x, y = int(pos[0]), int(pos[1])
            self.image.paste(source.image, (x, y), source.image if source.image.mode == 'RGBA' else None)
        elif isinstance(source, Image.Image):
            x, y = int(pos[0]), int(pos[1])
            self.image.paste(source, (x, y), source if source.mode == 'RGBA' else None)

    def get_width(self):
        """Return surface width"""
        return self.width

    def get_height(self):
        """Return surface height"""
        return self.height

    def get_rect(self):
        """Return a rect representing the surface bounds"""
        return Rect(0, 0, self.width, self.height)

    def convert_alpha(self):
        """Convert surface to have alpha channel - returns self for compatibility"""
        if self.image.mode != 'RGBA':
            self.image = self.image.convert('RGBA')
            self.draw = ImageDraw.Draw(self.image)
        return self


class Rect:
    """Simple pygame Rect implementation"""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.left = x
        self.top = y
        self.right = x + width
        self.bottom = y + height
        self.centerx = x + width // 2
        self.centery = y + height // 2


class Font:
    """pygame.font.Font compatible class using PIL ImageFont"""

    def __init__(self, path, size):
        """Load a font from a file path

        Args:
            path: Path to TTF font file, or None for default font
            size: Font size in pixels
        """
        self.size = size
        try:
            if path is None:
                # Use default font
                self.font = ImageFont.load_default()
            else:
                self.font = ImageFont.truetype(path, size)
        except (IOError, OSError):
            # Fall back to default font if file not found
            print(f"Warning: Could not load font '{path}', using default")
            self.font = ImageFont.load_default()

    def render(self, text, antialias, color, background=None):
        """Render text to a new Surface

        Args:
            text: String to render
            antialias: Boolean (ignored in PIL, always antialiased)
            color: RGB tuple for text color
            background: Optional RGB tuple for background color

        Returns:
            Surface containing the rendered text
        """
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        # Get text bounding box
        bbox = self.font.getbbox(text) if hasattr(self.font, 'getbbox') else (0, 0, len(text) * self.size, self.size)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        # Create surface with alpha channel for transparency
        if background is None:
            surface = Surface((width, height))
            surface.image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            surface.draw = ImageDraw.Draw(surface.image)
        else:
            if isinstance(background, (list, tuple)) and len(background) >= 3:
                background = tuple(background[:3])
            surface = Surface((width, height))
            surface.image = Image.new('RGB', (width, height), background)
            surface.draw = ImageDraw.Draw(surface.image)

        # Draw text
        surface.draw.text((-bbox[0], -bbox[1]), text, font=self.font, fill=color)

        return surface

    def size_text(self, text):
        """Get the size of rendered text without rendering

        Args:
            text: String to measure

        Returns:
            (width, height) tuple
        """
        bbox = self.font.getbbox(text) if hasattr(self.font, 'getbbox') else (0, 0, len(text) * self.size, self.size)
        return (bbox[2] - bbox[0], bbox[3] - bbox[1])

    def get_height(self):
        """Get the font height"""
        return self.size


class SysFont:
    """Create a Font from system fonts"""

    def __new__(cls, name, size, bold=False, italic=False):
        """Load a system font by name

        Note: PIL doesn't have great system font support, so this
        falls back to default font in most cases.
        """
        # Try common system font locations
        font_paths = []

        if os.name == 'nt':  # Windows
            font_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
            font_paths = [
                os.path.join(font_dir, f"{name}.ttf"),
                os.path.join(font_dir, f"{name.lower()}.ttf"),
            ]
        elif os.name == 'posix':
            # macOS and Linux
            font_paths = [
                f"/System/Library/Fonts/{name}.ttf",
                f"/System/Library/Fonts/{name}.ttc",
                f"/Library/Fonts/{name}.ttf",
                f"/usr/share/fonts/truetype/{name.lower()}/{name.lower()}.ttf",
                f"/usr/share/fonts/TTF/{name}.ttf",
                os.path.expanduser(f"~/Library/Fonts/{name}.ttf"),
            ]

        for path in font_paths:
            if os.path.exists(path):
                return Font(path, size)

        # Fall back to default font
        return Font(None, size)


class PygameFont:
    """pygame.font module implementation"""

    Font = Font
    SysFont = SysFont

    @staticmethod
    def init():
        """Initialize font module (no-op for PIL)"""
        pass

    @staticmethod
    def get_init():
        """Check if font module is initialized"""
        return True

    @staticmethod
    def get_fonts():
        """Get list of available fonts (limited support)"""
        return ['arial', 'helvetica', 'times', 'courier']


class PygameDraw:
    @staticmethod
    def circle(surface, color, pos, radius, width=0):
        """Draw circle on surface"""
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        x, y = pos
        left = x - radius
        top = y - radius
        right = x + radius
        bottom = y + radius

        if width == 0:
            # Filled circle
            surface.draw.ellipse([left, top, right, bottom], fill=color)
        else:
            # Circle outline
            surface.draw.ellipse([left, top, right, bottom], outline=color, width=width)

    @staticmethod
    def rect(surface, color, rect, width=0):
        """Draw rectangle on surface"""
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        if len(rect) == 4:
            x, y, w, h = rect
            left, top, right, bottom = x, y, x + w, y + h
        else:
            left, top, right, bottom = rect

        if width == 0:
            # Filled rectangle
            surface.draw.rectangle([left, top, right, bottom], fill=color)
        else:
            # Rectangle outline
            surface.draw.rectangle([left, top, right, bottom], outline=color, width=width)

    @staticmethod
    def line(surface, color, start, end, width=1):
        """Draw line on surface"""
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        surface.draw.line([start, end], fill=color, width=width)

    @staticmethod
    def polygon(surface, color, points, width=0):
        """Draw polygon on surface"""
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        # Convert points to flat list of coordinates
        flat_points = []
        for point in points:
            flat_points.extend([point[0], point[1]])

        if width == 0:
            # Filled polygon
            surface.draw.polygon(flat_points, fill=color)
        else:
            # Polygon outline
            surface.draw.polygon(flat_points, outline=color, width=width)

    @staticmethod
    def ellipse(surface, color, rect, width=0):
        """Draw ellipse on surface"""
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        if len(rect) == 4:
            x, y, w, h = rect
            left, top, right, bottom = x, y, x + w, y + h
        else:
            left, top, right, bottom = rect

        if width == 0:
            # Filled ellipse
            surface.draw.ellipse([left, top, right, bottom], fill=color)
        else:
            # Ellipse outline
            surface.draw.ellipse([left, top, right, bottom], outline=color, width=width)

    @staticmethod
    def arc(surface, color, rect, start_angle, stop_angle, width=1):
        """Draw arc on surface"""
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        if len(rect) == 4:
            x, y, w, h = rect
            left, top, right, bottom = x, y, x + w, y + h
        else:
            left, top, right, bottom = rect

        # Convert radians to degrees
        start_deg = math.degrees(start_angle)
        stop_deg = math.degrees(stop_angle)

        surface.draw.arc([left, top, right, bottom], start_deg, stop_deg, fill=color, width=width)

# Create pygame module structure with common pygame constants and methods
class PygameModule:
    def __init__(self):
        self.draw = PygameDraw()
        self.font = PygameFont()

        # Color constants
        self.SRCALPHA = 1

        # Key constants (dummy values)
        self.K_SPACE = 32
        self.K_LEFT = 276
        self.K_RIGHT = 275
        self.K_UP = 273
        self.K_DOWN = 274

        # Event constants
        self.QUIT = 256
        self.KEYDOWN = 2
        self.KEYUP = 3

    def Surface(self, size, flags=0, depth=32):
        return Surface(size)

    def init(self):
        """Mock pygame.init() - does nothing but prevents errors"""
        pass

    def quit(self):
        """Mock pygame.quit() - does nothing but prevents errors"""
        pass

    def get_init(self):
        """Mock pygame.get_init() - always returns True"""
        return True

# Export pygame interface
pygame = PygameModule()