"""
pygame compatibility shim for Eyesy simulator
Renders pygame commands to PIL Image instead of display
"""

from PIL import Image, ImageDraw
import math
import numpy as np

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