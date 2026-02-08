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

    def blit(self, source, pos, area=None):
        """Draw another surface onto this one at the given position

        Args:
            source: Source surface to blit from
            pos: (x, y) position to blit to
            area: Optional (x, y, width, height) rect to copy from source
        """
        x, y = int(pos[0]), int(pos[1])

        if hasattr(source, 'image'):
            src_img = source.image
        elif isinstance(source, Image.Image):
            src_img = source
        else:
            return

        # If area specified, crop the source first
        if area is not None:
            ax, ay, aw, ah = int(area[0]), int(area[1]), int(area[2]), int(area[3])
            src_img = src_img.crop((ax, ay, ax + aw, ay + ah))

        # Paste with alpha mask if RGBA
        mask = src_img if src_img.mode == 'RGBA' else None
        self.image.paste(src_img, (x, y), mask)

    def get_width(self):
        """Return surface width"""
        return self.width

    def get_height(self):
        """Return surface height"""
        return self.height

    def get_rect(self, **kwargs):
        """Return a rect representing the surface bounds.

        Supports keyword args like center, topleft, etc. to position the rect.
        """
        rect = Rect(0, 0, self.width, self.height)

        # Handle positioning kwargs
        if 'center' in kwargs:
            cx, cy = kwargs['center']
            rect.x = cx - self.width // 2
            rect.y = cy - self.height // 2
            rect.left = rect.x
            rect.top = rect.y
            rect.right = rect.x + rect.width
            rect.bottom = rect.y + rect.height
            rect.centerx = cx
            rect.centery = cy
        elif 'topleft' in kwargs:
            rect.x, rect.y = kwargs['topleft']
            rect.left = rect.x
            rect.top = rect.y
            rect.right = rect.x + rect.width
            rect.bottom = rect.y + rect.height
            rect.centerx = rect.x + rect.width // 2
            rect.centery = rect.y + rect.height // 2
        elif 'topright' in kwargs:
            rx, ry = kwargs['topright']
            rect.x = rx - self.width
            rect.y = ry
            rect.left = rect.x
            rect.top = rect.y
            rect.right = rx
            rect.bottom = rect.y + rect.height
            rect.centerx = rect.x + rect.width // 2
            rect.centery = rect.y + rect.height // 2

        return rect

    def convert_alpha(self):
        """Convert surface to have alpha channel - returns self for compatibility"""
        if self.image.mode != 'RGBA':
            self.image = self.image.convert('RGBA')
            self.draw = ImageDraw.Draw(self.image)
        return self

    def get_at(self, pos):
        """Get the color of a pixel at (x, y)"""
        x, y = int(pos[0]), int(pos[1])
        if 0 <= x < self.width and 0 <= y < self.height:
            pixel = self.image.getpixel((x, y))
            if isinstance(pixel, int):
                # Grayscale
                return (pixel, pixel, pixel, 255)
            elif len(pixel) == 3:
                return (pixel[0], pixel[1], pixel[2], 255)
            else:
                return pixel
        return (0, 0, 0, 255)

    def set_at(self, pos, color):
        """Set the color of a pixel at (x, y)"""
        x, y = int(pos[0]), int(pos[1])
        if 0 <= x < self.width and 0 <= y < self.height:
            if isinstance(color, (list, tuple)):
                color = tuple(color[:3]) if len(color) >= 3 else (0, 0, 0)
            self.image.putpixel((x, y), color)


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

    def __getitem__(self, index):
        """Support tuple-like access: rect[0], rect[1], etc."""
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.width
        elif index == 3:
            return self.height
        else:
            raise IndexError("Rect index out of range")

    def __iter__(self):
        """Support unpacking: x, y, w, h = rect"""
        return iter((self.x, self.y, self.width, self.height))


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
    def lines(surface, color, closed, points, width=1):
        """Draw multiple connected line segments on surface

        Args:
            surface: Target surface
            color: Line color
            closed: If True, connect last point to first
            points: List of (x, y) points
            width: Line width
        """
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            color = tuple(color[:3])

        if len(points) < 2:
            return

        # Draw line segments between consecutive points
        for i in range(len(points) - 1):
            start = (int(points[i][0]), int(points[i][1]))
            end = (int(points[i+1][0]), int(points[i+1][1]))
            surface.draw.line([start, end], fill=color, width=width)

        # Close the shape if requested
        if closed and len(points) >= 3:
            start = (int(points[-1][0]), int(points[-1][1]))
            end = (int(points[0][0]), int(points[0][1]))
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

class PygameImage:
    """pygame.image module implementation"""

    @staticmethod
    def load(path):
        """Load an image from a file path and return a Surface"""
        try:
            pil_image = Image.open(path)
            # Convert to RGB or RGBA
            if pil_image.mode == 'RGBA':
                pass  # Keep RGBA
            elif pil_image.mode == 'LA' or (pil_image.mode == 'P' and 'transparency' in pil_image.info):
                pil_image = pil_image.convert('RGBA')
            else:
                pil_image = pil_image.convert('RGB')

            # Create Surface from image
            surface = Surface(pil_image.size)
            surface.image = pil_image
            surface.draw = ImageDraw.Draw(surface.image)
            return surface
        except Exception as e:
            print(f"Error loading image '{path}': {e}")
            # Return a small placeholder surface
            return Surface((1, 1))

    @staticmethod
    def save(surface, path):
        """Save a surface to a file"""
        if hasattr(surface, 'image'):
            surface.image.save(path)

    @staticmethod
    def fromstring(data, size, format):
        """Create a Surface from a string of raw pixel data"""
        pil_image = Image.frombytes(format, size, data)
        surface = Surface(size)
        surface.image = pil_image
        surface.draw = ImageDraw.Draw(surface.image)
        return surface


class PygameSurfarray:
    """pygame.surfarray module implementation for pixel manipulation"""

    @staticmethod
    def array3d(surface):
        """Get a 3D numpy array (height, width, 3) from a surface"""
        if hasattr(surface, 'image'):
            img = surface.image
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            return np.array(img)
        return np.zeros((1, 1, 3), dtype=np.uint8)

    @staticmethod
    def pixels3d(surface):
        """Get a 3D numpy array reference to surface pixels (height, width, 3)

        Note: In real pygame this returns a reference that modifies the surface.
        Our implementation returns a copy - use make_surface() to apply changes.
        """
        return PygameSurfarray.array3d(surface)

    @staticmethod
    def make_surface(array):
        """Create a Surface from a 3D numpy array (height, width, 3)"""
        if len(array.shape) == 3 and array.shape[2] >= 3:
            # Ensure uint8
            if array.dtype != np.uint8:
                array = np.clip(array, 0, 255).astype(np.uint8)

            # Create PIL image from array
            if array.shape[2] == 3:
                pil_image = Image.fromarray(array, 'RGB')
            else:
                pil_image = Image.fromarray(array[:, :, :4], 'RGBA')

            surface = Surface((pil_image.width, pil_image.height))
            surface.image = pil_image
            surface.draw = ImageDraw.Draw(surface.image)
            return surface

        return Surface((1, 1))


class PygameTransform:
    """pygame.transform module implementation"""

    @staticmethod
    def scale(surface, size):
        """Scale a surface to a new size (nearest neighbor)"""
        if hasattr(surface, 'image'):
            new_size = (int(size[0]), int(size[1]))
            scaled_image = surface.image.resize(new_size, Image.Resampling.NEAREST)
            new_surface = Surface(new_size)
            new_surface.image = scaled_image
            new_surface.draw = ImageDraw.Draw(new_surface.image)
            return new_surface
        return Surface(size)

    @staticmethod
    def smoothscale(surface, size):
        """Scale a surface with smooth filtering"""
        return PygameTransform.scale(surface, size)

    @staticmethod
    def rotate(surface, angle):
        """Rotate a surface by angle degrees counter-clockwise"""
        if hasattr(surface, 'image'):
            rotated = surface.image.rotate(angle, expand=True, resample=Image.Resampling.BILINEAR)
            new_surface = Surface(rotated.size)
            new_surface.image = rotated
            new_surface.draw = ImageDraw.Draw(new_surface.image)
            return new_surface
        return surface

    @staticmethod
    def flip(surface, flip_x, flip_y):
        """Flip a surface horizontally and/or vertically"""
        if hasattr(surface, 'image'):
            img = surface.image
            if flip_x:
                img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if flip_y:
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            new_surface = Surface(img.size)
            new_surface.image = img
            new_surface.draw = ImageDraw.Draw(new_surface.image)
            return new_surface
        return surface


# Create pygame module structure with common pygame constants and methods
class PygameModule:
    def __init__(self):
        self.draw = PygameDraw()
        self.font = PygameFont()
        self.image = PygameImage()
        self.surfarray = PygameSurfarray()
        self.transform = PygameTransform()

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