# Image Trip Mode - NumPy Version
# Loads images and applies row/column repeat effects with rotation
#
# NOTE: This version requires NumPy and will NOT work on EYESY hardware.
# Use the standard S-Image-Trip mode for hardware compatibility.
#
# Knob 1: Vertical stretch - max row repeat count (1 to 64)
# Knob 2: Horizontal stretch - max column repeat count (1 to 64)
# Knob 3: Glitch density (how often rows/columns get repeated)
# Knob 4: Image selection
# Knob 5: Effects (blur/noise intensity)

import pygame
import os
import random
import math

try:
    import numpy as np
    from PIL import Image, ImageFilter
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Screen dimensions
WIDTH = 1280
HEIGHT = 720

# State
images = []
current_image = None  # numpy array (H, W, 3)
current_image_pygame = None  # pygame Surface for display
current_image_index = -1
cached_tiled = None  # Cached 3x3 mirrored tessellation
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
PATTERN_REGEN_INTERVAL = 90


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
    """Load an image and scale it to screen size, returns numpy array"""
    img = Image.open(path).convert('RGB')

    # Scale to cover screen
    scale_w = WIDTH / img.width
    scale_h = HEIGHT / img.height
    scale = max(scale_w, scale_h)

    new_w = int(img.width * scale)
    new_h = int(img.height * scale)

    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Crop to center
    left = (new_w - WIDTH) // 2
    top = (new_h - HEIGHT) // 2
    img = img.crop((left, top, left + WIDTH, top + HEIGHT))

    return np.array(img)


def build_tiled_array(arr):
    """Build 3x3 mirrored tessellation for seamless rotation."""
    # arr shape: (H, W, 3)
    flip_h = np.fliplr(arr)
    flip_v = np.flipud(arr)
    flip_both = np.flipud(np.fliplr(arr))

    # Build rows
    row0 = np.concatenate([flip_both, flip_v, flip_both], axis=1)
    row1 = np.concatenate([flip_h, arr, flip_h], axis=1)
    row2 = np.concatenate([flip_both, flip_v, flip_both], axis=1)

    # Stack rows
    return np.concatenate([row0, row1, row2], axis=0)


def generate_glitch_pattern(length, max_repeat, density):
    """Generate a repeat glitch pattern for rows or columns.

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


def expand_pattern_to_indices(pattern, length):
    """Expand (source, repeat) pattern to flat index array."""
    indices = []
    for source_idx, repeat in pattern:
        indices.extend([source_idx] * repeat)

    # Ensure exact length
    if len(indices) < length:
        last_idx = indices[-1] if indices else 0
        indices.extend([last_idx] * (length - len(indices)))

    return np.array(indices[:length], dtype=np.int32)


def morph_pattern_step(current_pattern, target_pattern, morph_index, steps_per_frame=5):
    """Morph pattern tuples toward target gradually."""
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


def apply_row_pattern(arr, pattern, v_offset, out_height):
    """Apply row repeat pattern using numpy indexing."""
    h, w, c = arr.shape

    # Create mirrored version for seamless panning
    mirrored = np.concatenate([np.flipud(arr), arr, np.flipud(arr)], axis=0)
    mirrored_h = mirrored.shape[0]

    # Expand pattern to indices
    indices = expand_pattern_to_indices(pattern, out_height)

    # Offset the indices for panning effect
    offset_indices = (indices + v_offset + h) % mirrored_h

    return mirrored[offset_indices, :, :]


def apply_col_pattern(arr, pattern, h_offset, out_width):
    """Apply column repeat pattern using numpy indexing."""
    h, w, c = arr.shape

    # Create mirrored version for seamless panning
    mirrored = np.concatenate([np.fliplr(arr), arr, np.fliplr(arr)], axis=1)
    mirrored_w = mirrored.shape[1]

    # Expand pattern to indices
    indices = expand_pattern_to_indices(pattern, out_width)

    # Offset the indices for panning effect
    offset_indices = (indices + h_offset + w) % mirrored_w

    return mirrored[:, offset_indices, :]


def rotate_array(tiled, angle_degrees, out_h, out_w):
    """Rotate tiled array and crop center."""
    pil_img = Image.fromarray(tiled)
    rotated = pil_img.rotate(angle_degrees, resample=Image.Resampling.BILINEAR, expand=False)

    # Crop center
    cx, cy = rotated.width // 2, rotated.height // 2
    left = cx - out_w // 2
    top = cy - out_h // 2

    cropped = rotated.crop((left, top, left + out_w, top + out_h))
    return np.array(cropped)


def apply_effects(arr, intensity):
    """Apply blur and noise effects based on intensity (0-1)."""
    if intensity < 0.01:
        return arr

    pil_img = Image.fromarray(arr)

    # Blur (max radius 5.6 at intensity 1.0)
    blur_radius = intensity * 5.6
    if blur_radius > 0.5:
        pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    result = np.array(pil_img)

    # Add noise
    noise_intensity = intensity * 56
    if noise_intensity > 1:
        noise = np.random.randint(-int(noise_intensity), int(noise_intensity) + 1,
                                   result.shape, dtype=np.int16)
        result = np.clip(result.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return result


def setup(screen, etc):
    """Initialize - load image list"""
    global images
    images = get_image_files()


def draw(screen, etc):
    """Draw glitched image"""
    global images, current_image, current_image_pygame, current_image_index
    global cached_tiled, row_pattern, col_pattern
    global target_row_pattern, target_col_pattern
    global row_morph_index, col_morph_index, last_params, frame_count
    global pattern_regen_counter

    if not HAS_NUMPY:
        screen.fill((80, 0, 0))
        return

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

    # Knob 5: Effect intensity (blur + noise)
    effect_intensity = etc.knob5

    # Load new image if selection changed
    if image_index != current_image_index:
        current_image_index = image_index
        current_image = load_and_scale_image(images[image_index])
        cached_tiled = build_tiled_array(current_image)
        row_pattern = None
        col_pattern = None
        target_row_pattern = None
        target_col_pattern = None

    # Current parameters for change detection
    current_params = (max_row_repeat, max_col_repeat, density, int(etc.knob4 * 100))

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
        target_row_pattern = generate_glitch_pattern(HEIGHT, max_row_repeat, density)
        target_col_pattern = generate_glitch_pattern(WIDTH, max_col_repeat, density)

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

    # Calculate panning offsets
    v_wave = math.sin(frame_count * 0.02) * 0.5 + 0.5
    h_wave = math.sin(frame_count * 0.015 + 1.5) * 0.5 + 0.5
    v_offset = int(v_wave * HEIGHT * 0.3)
    h_offset = int(h_wave * WIDTH * 0.2)

    # Calculate rotation angle
    rotation_angle = (
        math.sin(frame_count * 0.006 + rotation_offset) * 25 +
        math.sin(frame_count * 0.017 + rotation_offset * 2) * 12 +
        math.sin(frame_count * 0.041 + rotation_offset * 3) * 5
    )

    # Apply effects
    if current_image is not None and cached_tiled is not None:
        # Apply rotation using cached tessellation
        if abs(rotation_angle) > 0.5:
            glitched = rotate_array(cached_tiled, rotation_angle, HEIGHT, WIDTH)
        else:
            glitched = current_image.copy()

        # Apply row pattern (vertical stretch)
        glitched = apply_row_pattern(glitched, row_pattern, v_offset, HEIGHT)

        # Apply column pattern (horizontal stretch)
        glitched = apply_col_pattern(glitched, col_pattern, h_offset, WIDTH)

        # Apply blur/noise effects
        glitched = apply_effects(glitched, effect_intensity)

        # Ensure output is correct size
        if glitched.shape[0] != HEIGHT or glitched.shape[1] != WIDTH:
            pil_image = Image.fromarray(glitched.astype(np.uint8))
            pil_image = pil_image.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST)
        else:
            pil_image = Image.fromarray(glitched.astype(np.uint8))

        # Blit to screen
        screen.blit(pil_image, (0, 0))
    else:
        screen.fill((0, 0, 0))

    frame_count += 1
