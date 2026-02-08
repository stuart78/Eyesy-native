# Image Trip Mode
# Loads images and applies row/column repeat effects with rotation
#
# Knob 1: Vertical stretch - max row repeat count (1 to 64)
# Knob 2: Horizontal stretch - max column repeat count (1 to 64)
# Knob 3: Glitch density (how often rows/columns get repeated)
# Knob 4: Image selection
# Knob 5: Resolution (0 = full 1280x720, 1 = pixelated 80x45)

import pygame
import os
import random
import math

# Screen dimensions
WIDTH = 1280
HEIGHT = 720

# Render dimensions (set dynamically based on knob 5)
render_width = WIDTH
render_height = HEIGHT

# State
images = []
current_image = None  # pygame Surface
current_image_index = -1
cached_tiled = None  # Cached 3x3 mirrored tessellation for rotation
row_pattern = None
col_pattern = None
target_row_pattern = None
target_col_pattern = None
row_morph_index = 0
col_morph_index = 0
last_params = None
frame_count = 0
pattern_regen_counter = 0
rotation_offset = random.uniform(0, 2 * math.pi)

# How often to generate a new target pattern (in frames)
PATTERN_REGEN_INTERVAL = 90  # Every 3 seconds at 30fps


def get_image_files():
    """Get list of image files in the images subdirectory"""
    mode_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(mode_dir, 'images')

    if not os.path.exists(images_dir):
        return []

    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    image_files = []

    for filename in os.listdir(images_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext in valid_extensions:
            image_files.append(os.path.join(images_dir, filename))

    return sorted(image_files)


def load_and_scale_image(path):
    """Load an image and scale it to full resolution, returns pygame Surface"""
    img = pygame.image.load(path)

    img_w = img.get_width()
    img_h = img.get_height()

    # Scale to fit full resolution
    scale_w = WIDTH / img_w
    scale_h = HEIGHT / img_h
    scale = max(scale_w, scale_h)

    new_w = int(img_w * scale)
    new_h = int(img_h * scale)

    scaled = pygame.transform.scale(img, (new_w, new_h))

    # Crop to center
    crop_x = (new_w - WIDTH) // 2
    crop_y = (new_h - HEIGHT) // 2

    cropped = pygame.Surface((WIDTH, HEIGHT))
    cropped.blit(scaled, (-crop_x, -crop_y))

    return cropped


def generate_glitch_pattern(length, max_repeat, density):
    """Generate a repeat glitch pattern for rows or columns

    Returns a list of (source_index, repeat_count) tuples that when
    expanded will produce exactly 'length' items.
    """
    pattern = []
    current_idx = 0
    items_generated = 0

    while items_generated < length and current_idx < length:
        if random.random() < density:
            repeat = random.randint(1, max(1, int(max_repeat)))
        else:
            repeat = 1

        repeat = min(repeat, length - items_generated)
        pattern.append((current_idx, repeat))
        items_generated += repeat
        current_idx += 1

    return pattern


def morph_pattern_step(current_pattern, target_pattern, morph_index, steps_per_frame=5):
    """Morph multiple elements of the pattern toward the target per frame."""
    if current_pattern is None or len(current_pattern) == 0:
        return target_pattern, 0

    if target_pattern is None or len(target_pattern) == 0:
        return current_pattern, morph_index

    # If lengths differ, use target immediately
    if len(current_pattern) != len(target_pattern):
        return target_pattern, 0

    result = list(current_pattern)
    target = list(target_pattern)

    for _ in range(steps_per_frame):
        idx = morph_index % len(result)
        result[idx] = target[idx]
        morph_index = (morph_index + 1) % len(result)

    return result, morph_index


def build_tiled_image(surface):
    """Build 3x3 mirrored tessellation for seamless rotation."""
    width = surface.get_width()
    height = surface.get_height()

    # Create flipped versions
    flip_h = pygame.transform.flip(surface, True, False)
    flip_v = pygame.transform.flip(surface, False, True)
    flip_both = pygame.transform.flip(surface, True, True)

    tiled = pygame.Surface((width * 3, height * 3))

    tiles = [
        (flip_both, 0, 0), (flip_v, 1, 0), (flip_both, 2, 0),
        (flip_h, 0, 1),    (surface, 1, 1), (flip_h, 2, 1),
        (flip_both, 0, 2), (flip_v, 1, 2), (flip_both, 2, 2),
    ]

    for tile, col, row in tiles:
        tiled.blit(tile, (col * width, row * height))

    return tiled


def rotate_image(tiled, angle_degrees, rw, rh):
    """Rotate using pre-built tiled image to avoid black edges."""
    rotated = pygame.transform.rotate(tiled, angle_degrees)

    # Crop center to render size
    center_x = rotated.get_width() // 2
    center_y = rotated.get_height() // 2
    left = center_x - rw // 2
    top = center_y - rh // 2

    cropped = pygame.Surface((rw, rh))
    cropped.blit(rotated, (-left, -top))

    return cropped


def create_mirrored_surface(surface, axis):
    """Create a mirrored version: [flipped | original | flipped] along axis."""
    width = surface.get_width()
    height = surface.get_height()

    if axis == 0:  # Vertical (rows)
        flipped = pygame.transform.flip(surface, False, True)
        result = pygame.Surface((width, height * 3))
        result.blit(flipped, (0, 0))
        result.blit(surface, (0, height))
        result.blit(flipped, (0, height * 2))
    else:  # Horizontal (columns)
        flipped = pygame.transform.flip(surface, True, False)
        result = pygame.Surface((width * 3, height))
        result.blit(flipped, (0, 0))
        result.blit(surface, (width, 0))
        result.blit(flipped, (width * 2, 0))

    return result


def apply_row_pattern(surface, pattern, v_offset, rh):
    """Apply a row-repeat pattern with mirrored panning."""
    width = surface.get_width()
    height = surface.get_height()

    mirrored = create_mirrored_surface(surface, axis=0)
    mirrored_height = mirrored.get_height()

    result = pygame.Surface((width, rh))

    output_row = 0
    for source_row, repeat in pattern:
        if output_row >= rh:
            break

        actual_row = (source_row + v_offset + height) % mirrored_height

        for _ in range(repeat):
            if output_row >= rh:
                break
            # Blit single row
            result.blit(mirrored, (0, output_row), (0, actual_row, width, 1))
            output_row += 1

    return result


def apply_col_pattern(surface, pattern, h_offset, rw):
    """Apply a column-repeat pattern with mirrored panning."""
    width = surface.get_width()
    height = surface.get_height()

    mirrored = create_mirrored_surface(surface, axis=1)
    mirrored_width = mirrored.get_width()

    result = pygame.Surface((rw, height))

    output_col = 0
    for source_col, repeat in pattern:
        if output_col >= rw:
            break

        actual_col = (source_col + h_offset + width) % mirrored_width

        for _ in range(repeat):
            if output_col >= rw:
                break
            # Blit single column
            result.blit(mirrored, (output_col, 0), (actual_col, 0, 1, height))
            output_col += 1

    return result


def setup(screen, etc):
    """Initialize - load image list"""
    global images
    images = get_image_files()


def draw(screen, etc):
    """Draw glitched image"""
    global images, current_image, current_image_index, cached_tiled
    global row_pattern, col_pattern, target_row_pattern, target_col_pattern
    global row_morph_index, col_morph_index, last_params, frame_count
    global pattern_regen_counter, render_width, render_height

    # Initialize if needed
    if not images:
        images = get_image_files()

    if not images:
        screen.fill((0, 0, 0))
        return

    # Knob 1: Vertical stretch - max row repeat (1 to 64)
    max_row_repeat = int(1 + etc.knob1 * 63)

    # Knob 2: Horizontal stretch - max column repeat (1 to 64)
    max_col_repeat = int(1 + etc.knob2 * 63)

    # Knob 3: Glitch density (0.0 to 1.0)
    density = round(etc.knob3, 2)

    # Knob 4: Image selection
    image_index = int(etc.knob4 * (len(images) - 0.01))
    image_index = max(0, min(image_index, len(images) - 1))

    # Knob 5: Downsample amount (0 = full res, 1 = 1/16 res)
    # Scale factor: 1 at knob=0, 16 at knob=1
    downsample = 1 + int(etc.knob5 * 15)  # 1 to 16
    render_width = WIDTH // downsample
    render_height = HEIGHT // downsample

    # Load new image if selection changed
    if image_index != current_image_index:
        current_image_index = image_index
        current_image = load_and_scale_image(images[image_index])
        cached_tiled = build_tiled_image(current_image)
        row_pattern = None
        col_pattern = None
        target_row_pattern = None
        target_col_pattern = None

    # Current parameters for change detection (include downsample)
    current_params = (max_row_repeat, max_col_repeat, density, int(etc.knob4 * 100), downsample)

    # Generate new target patterns periodically or when params change
    pattern_regen_counter += 1
    need_new_target = (
        target_row_pattern is None or
        target_col_pattern is None or
        current_params != last_params or
        pattern_regen_counter >= PATTERN_REGEN_INTERVAL
    )

    if need_new_target:
        last_params = current_params
        pattern_regen_counter = 0
        target_row_pattern = generate_glitch_pattern(render_height, max_row_repeat, density)
        target_col_pattern = generate_glitch_pattern(render_width, max_col_repeat, density)

    # Initialize current patterns if needed
    if row_pattern is None:
        row_pattern = target_row_pattern
        row_morph_index = 0
    if col_pattern is None:
        col_pattern = target_col_pattern
        col_morph_index = 0

    # Morph current patterns toward target gradually
    if target_row_pattern is not None:
        row_pattern, row_morph_index = morph_pattern_step(
            row_pattern, target_row_pattern, row_morph_index
        )
    if target_col_pattern is not None:
        col_pattern, col_morph_index = morph_pattern_step(
            col_pattern, target_col_pattern, col_morph_index
        )

    # Calculate panning offsets with sine waves (scaled to render size)
    v_wave = math.sin(frame_count * 0.02) * 0.5 + 0.5
    h_wave = math.sin(frame_count * 0.015 + 1.5) * 0.5 + 0.5
    v_offset = int(v_wave * render_height * 0.3)
    h_offset = int(h_wave * render_width * 0.2)

    # Calculate rotation angle - wandering rotation
    rotation_angle = (
        math.sin(frame_count * 0.006 + rotation_offset) * 25 +
        math.sin(frame_count * 0.017 + rotation_offset * 2) * 12 +
        math.sin(frame_count * 0.041 + rotation_offset * 3) * 5
    )

    # Apply glitch effects
    if current_image is not None and cached_tiled is not None:
        # Downsample source image and tiled version for processing
        if downsample > 1:
            work_img = pygame.transform.scale(current_image, (render_width, render_height))
            work_tiled = pygame.transform.scale(cached_tiled, (render_width * 3, render_height * 3))
        else:
            work_img = current_image
            work_tiled = cached_tiled

        # Apply rotation using cached tessellation
        if abs(rotation_angle) > 0.5:
            glitched = rotate_image(work_tiled, rotation_angle, render_width, render_height)
        else:
            glitched = work_img

        # Apply vertical stretch (row repeat) with panning
        glitched = apply_row_pattern(glitched, row_pattern, v_offset, render_height)

        # Apply horizontal stretch (column repeat) with panning
        glitched = apply_col_pattern(glitched, col_pattern, h_offset, render_width)

        # Upscale to full resolution
        if downsample > 1:
            final = pygame.transform.scale(glitched, (WIDTH, HEIGHT))
        else:
            final = glitched

        screen.blit(final, (0, 0))
    else:
        screen.fill((0, 0, 0))

    frame_count += 1
