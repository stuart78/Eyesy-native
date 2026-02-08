# Color Wheel Mode
# Inspired by Orion Effects color wheels from the 1970s
# Two rotating layers: base layer + mask with cutouts
#
# Knob 1: Base layer speed bias
# Knob 2: Mask layer speed bias / Kaleidoscope segments (in kaleidoscope mode)
# Knob 3: Mask pattern (16 patterns):
#         triangles, spirals, diamonds, fish scales, interlocking, hexagons,
#         circles, starburst, petals, crescents, zigzag, stars, waves,
#         radial lines (15° grid), conical grid (checkerboard)
# Knob 4: Pattern density/size
# Knob 5: Base layer mode:
#         0.0-0.33: Gradient colors (9 types: rainbow, warm, cool, psychedelic, sunset, forest, neon, fire, b&w)
#         0.33-0.66: Polar-remapped images (if images folder exists)
#         0.66-1.0: Vector kaleidoscope (audio-reactive mirrored gradient segments)
#
# Audio Reactivity:
# - Kaleidoscope patterns pulse/scale with audio amplitude
# - Kaleidoscope direction reverses on loud peaks
# - Color cycling speeds up with audio
# - Pattern complexity increases with volume
# - Mask layer wobbles with audio
# - Mask darkness varies with audio (more transparent on loud sections)

import pygame
import math
import colorsys
import os

# Screen dimensions
WIDTH = 1280
HEIGHT = 720
CENTER_X = WIDTH // 2
CENTER_Y = HEIGHT // 2

# State
frame_count = 0
base_angle = 0.0
mask_angle = 0.0
# Drift states for organic movement
base_drift_phase = 0.0
mask_drift_phase = 0.0
last_audio_peak = 0
# Audio reactivity state
rotation_direction = 1
peak_cooldown = 0
# Current audio level for mask color
current_audio_level = 0.0


def get_mask_color(audio_level=0.0):
    """Get mask color that varies with audio level.

    At silence: dark gray (25, 25, 25) - 90% black
    At loud: lighter gray (60, 60, 60) - more bleed through
    """
    base = 25
    audio_boost = int(audio_level * 50)  # Up to 50 more brightness
    v = min(80, base + audio_boost)
    return (v, v, v)

# Cached polar-remapped images
polar_cache = {}  # filename -> pygame.Surface
kaleidoscope_cache = {}  # (filepath, num_segments) -> pygame.Surface
source_images = []  # List of image filenames
images_loaded = False
current_image_index = 0

# Kaleidoscope state
kaleidoscope_segments = 6  # Number of mirrored segments
kaleidoscope_zoom = 1.0
kaleidoscope_shift = 0.0  # Shift within the source image


def setup(screen, etc):
    """Initialize - load images."""
    global source_images, images_loaded

    if not images_loaded:
        # Find images folder relative to this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        images_dir = os.path.join(script_dir, 'images')

        print(f"[Color-Wheel] Looking for images in: {images_dir}")
        print(f"[Color-Wheel] Directory exists: {os.path.exists(images_dir)}")

        if os.path.exists(images_dir):
            for f in sorted(os.listdir(images_dir)):
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    full_path = os.path.join(images_dir, f)
                    source_images.append(full_path)
                    print(f"[Color-Wheel] Found image: {f}")

        print(f"[Color-Wheel] Total images loaded: {len(source_images)}")
        images_loaded = True


def load_and_polar_remap(filepath, target_size):
    """Load an image and create a polar-remapped version.

    The source image is mapped so that:
    - X axis maps to angle (0 to 2*pi)
    - Y axis maps to radius (0 to max_radius)

    This creates a disc where the left edge wraps to meet the right edge.
    """
    if filepath in polar_cache:
        return polar_cache[filepath]

    try:
        # Load source image
        src_surface = pygame.image.load(filepath)
        src_width, src_height = src_surface.get_size()

        # Create output surface (square, sized to cover screen diagonal)
        diagonal = int(math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)) + 100
        out_size = diagonal
        out_surface = pygame.Surface((out_size, out_size))

        cx = out_size // 2
        cy = out_size // 2
        max_radius = out_size // 2

        # Sample at lower resolution for speed
        sample_step = 2

        for y in range(0, out_size, sample_step):
            for x in range(0, out_size, sample_step):
                dx = x - cx
                dy = y - cy
                r = math.sqrt(dx * dx + dy * dy)

                if r < max_radius:
                    theta = math.atan2(dy, dx)

                    # Map theta (-pi to pi) to source X (0 to width)
                    src_x = int(((theta + math.pi) / (2 * math.pi)) * src_width) % src_width
                    # Map radius to source Y
                    src_y = int((r / max_radius) * src_height) % src_height

                    color = src_surface.get_at((src_x, src_y))[:3]

                    # Fill the sample block
                    for sy in range(sample_step):
                        for sx in range(sample_step):
                            if x + sx < out_size and y + sy < out_size:
                                out_surface.set_at((x + sx, y + sy), color)
                else:
                    # Outside the disc - black
                    for sy in range(sample_step):
                        for sx in range(sample_step):
                            if x + sx < out_size and y + sy < out_size:
                                out_surface.set_at((x + sx, y + sy), (0, 0, 0))

        # Cache the result
        polar_cache[filepath] = out_surface
        return out_surface

    except Exception as e:
        print(f"Error loading image {filepath}: {e}")
        return None


def get_organic_speed(base_speed, drift_phase, frame, audio_level):
    """Generate organic, less predictable rotation speed."""
    drift1 = math.sin(drift_phase * 0.7) * 0.02
    drift2 = math.sin(drift_phase * 1.3 + 1.5) * 0.015
    drift3 = math.sin(drift_phase * 2.1 + 3.0) * 0.01
    drift4 = math.sin(drift_phase * 0.3) * 0.025

    organic_drift = drift1 + drift2 + drift3 + drift4
    audio_boost = audio_level * 0.05
    wobble = math.sin(frame * 0.017) * math.sin(frame * 0.031) * 0.01

    return base_speed + organic_drift + audio_boost + wobble


def get_gradient_color(t, gradient_type, frame_offset=0):
    """Get a color from a gradient based on position t (0-1) and type."""
    if gradient_type == 0:
        # Rainbow
        r, g, b = colorsys.hsv_to_rgb(t, 0.9, 1.0)
    elif gradient_type == 1:
        # Warm colors (red-orange-yellow)
        hue = 0.0 + t * 0.15
        r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
    elif gradient_type == 2:
        # Cool colors (cyan-blue-purple)
        hue = 0.5 + t * 0.25
        r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
    elif gradient_type == 3:
        # Psychedelic (multiple hue cycles)
        hue = (t * 3 + frame_offset) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    elif gradient_type == 4:
        # Sunset (purple to orange)
        hue = 0.8 - t * 0.15
        sat = 0.7 + t * 0.3
        r, g, b = colorsys.hsv_to_rgb(hue, sat, 1.0)
    elif gradient_type == 5:
        # Forest (greens and browns)
        hue = 0.25 + math.sin(t * math.pi) * 0.1
        sat = 0.6 + t * 0.3
        val = 0.4 + t * 0.5
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    elif gradient_type == 6:
        # Neon (high saturation, shifting)
        hue = (t * 2 + frame_offset * 0.5) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    elif gradient_type == 7:
        # Fire (black to red to yellow to white)
        if t < 0.33:
            r, g, b = t * 3, 0, 0
        elif t < 0.66:
            r = 1.0
            g = (t - 0.33) * 3
            b = 0
        else:
            r = 1.0
            g = 1.0
            b = (t - 0.66) * 3
    else:
        # Black and White (gradient_type == 8)
        # Light grays for contrast with dark overlay mask
        # Range from mid-gray (0.5) to white (1.0)
        v = 0.5 + t * 0.5
        r, g, b = v, v, v

    return (int(r * 255), int(g * 255), int(b * 255))


def draw_base_gradient(screen, angle, color_mode):
    """Draw the base layer - a rotating gradient."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    radius = int(diagonal / 2) + 50

    num_segments = 36
    segment_angle = 2 * math.pi / num_segments

    # Select gradient type (0-8, 9 total gradients)
    gradient_type = int(color_mode * 9) % 9

    for i in range(num_segments):
        a1 = i * segment_angle + angle
        a2 = (i + 1) * segment_angle + angle
        t = i / num_segments

        color = get_gradient_color(t, gradient_type)

        points = [(CENTER_X, CENTER_Y)]
        steps = 5
        for j in range(steps + 1):
            a = a1 + (a2 - a1) * j / steps
            x = CENTER_X + radius * math.cos(a)
            y = CENTER_Y + radius * math.sin(a)
            points.append((int(x), int(y)))
        pygame.draw.polygon(screen, color, points)


def draw_kaleidoscope_radial(screen, angle, gradient_type, num_segments, inner_shift,
                             pulse_scale=1.0, audio_level=0.0):
    """Radial kaleidoscope - classic circular bands with audio reactivity."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    base_radius = int(diagonal / 2) + 50
    # Apply pulse scaling
    radius = int(base_radius * pulse_scale)
    segment_angle = 2 * math.pi / num_segments
    # More bands when audio is loud
    bands_per_segment = 8 + int(audio_level * 4)

    for seg in range(num_segments):
        seg_start = seg * segment_angle + angle
        is_mirrored = (seg % 2 == 1)

        for band in range(bands_per_segment):
            if is_mirrored:
                t = (bands_per_segment - 1 - band) / bands_per_segment
            else:
                t = band / bands_per_segment

            # Audio affects color cycling speed
            t_shifted = (t + inner_shift + audio_level * 0.1) % 1.0
            color = get_gradient_color(t_shifted, gradient_type, inner_shift)

            # Audio warps band positions slightly
            band_warp = math.sin(band * 0.5 + inner_shift * 3) * audio_level * 0.1
            band_start = seg_start + ((band + band_warp) / bands_per_segment) * segment_angle
            band_end = seg_start + ((band + 1 + band_warp) / bands_per_segment) * segment_angle

            points = [(CENTER_X, CENTER_Y)]
            for j in range(4):
                a = band_start + (band_end - band_start) * j / 3
                x = CENTER_X + radius * math.cos(a)
                y = CENTER_Y + radius * math.sin(a)
                points.append((int(x), int(y)))
            pygame.draw.polygon(screen, color, points)


def draw_kaleidoscope_triangles(screen, angle, gradient_type, num_segments, inner_shift,
                                pulse_scale=1.0, audio_level=0.0):
    """Fragmented triangle tessellation kaleidoscope with audio reactivity."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    base_radius = int(diagonal / 2) + 50
    radius = int(base_radius * pulse_scale)
    segment_angle = 2 * math.pi / num_segments

    # More rows when audio is loud
    num_rows = 6 + int(audio_level * 3)

    for seg in range(num_segments):
        seg_start = seg * segment_angle + angle
        is_mirrored = (seg % 2 == 1)

        for row in range(num_rows):
            # Inner and outer radius for this row - audio warps these
            row_warp = 1.0 + math.sin(row * 0.8 + inner_shift * 2) * audio_level * 0.15
            r_inner = (row / num_rows) * radius * row_warp
            r_outer = ((row + 1) / num_rows) * radius * row_warp

            # More triangles in outer rows
            tris_in_row = row + 2

            for tri in range(tris_in_row):
                # Triangle position within segment
                if is_mirrored:
                    tri_pos = (tris_in_row - 1 - tri) / tris_in_row
                else:
                    tri_pos = tri / tris_in_row

                # Color based on position - audio speeds up color cycling
                t = (row / num_rows + tri_pos / num_rows + inner_shift + audio_level * 0.15) % 1.0
                color = get_gradient_color(t, gradient_type, inner_shift)

                # Calculate triangle vertices - audio adds jitter
                jitter = audio_level * 0.05
                a1 = seg_start + (tri / tris_in_row) * segment_angle
                a2 = seg_start + ((tri + 1) / tris_in_row) * segment_angle
                a_mid = (a1 + a2) / 2 + math.sin(tri + inner_shift * 5) * jitter

                # Alternating up/down triangles
                if tri % 2 == 0:
                    # Point outward
                    p1 = (CENTER_X + r_inner * math.cos(a1), CENTER_Y + r_inner * math.sin(a1))
                    p2 = (CENTER_X + r_inner * math.cos(a2), CENTER_Y + r_inner * math.sin(a2))
                    p3 = (CENTER_X + r_outer * math.cos(a_mid), CENTER_Y + r_outer * math.sin(a_mid))
                else:
                    # Point inward
                    p1 = (CENTER_X + r_outer * math.cos(a1), CENTER_Y + r_outer * math.sin(a1))
                    p2 = (CENTER_X + r_outer * math.cos(a2), CENTER_Y + r_outer * math.sin(a2))
                    p3 = (CENTER_X + r_inner * math.cos(a_mid), CENTER_Y + r_inner * math.sin(a_mid))

                points = [(int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (int(p3[0]), int(p3[1]))]
                pygame.draw.polygon(screen, color, points)


def draw_kaleidoscope_shattered(screen, angle, gradient_type, num_segments, inner_shift,
                                pulse_scale=1.0, audio_level=0.0):
    """Shattered glass effect - irregular triangular fragments with audio reactivity."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    base_radius = int(diagonal / 2) + 50
    radius = int(base_radius * pulse_scale)
    segment_angle = 2 * math.pi / num_segments

    # Create pseudo-random but deterministic fragment points
    # More rings when audio is loud for more fragmentation
    num_rings = 5 + int(audio_level * 2)
    points_per_ring = 4

    for seg in range(num_segments):
        seg_start = seg * segment_angle + angle
        is_mirrored = (seg % 2 == 1)

        # Generate fragment vertices within this segment
        vertices = [(CENTER_X, CENTER_Y)]  # Center point

        for ring in range(1, num_rings + 1):
            # Audio makes rings pulse in and out
            ring_pulse = 1.0 + math.sin(ring * 1.5 + inner_shift * 3) * audio_level * 0.2
            r = (ring / num_rings) * radius * ring_pulse
            for p in range(points_per_ring):
                # Add some variation based on position - audio increases chaos
                chaos = 0.15 + audio_level * 0.2
                offset = math.sin((ring * 7 + p * 13 + inner_shift * 2) * 0.5) * chaos
                if is_mirrored:
                    a_pos = 1.0 - (p + 0.5 + offset) / points_per_ring
                else:
                    a_pos = (p + 0.5 + offset) / points_per_ring
                a = seg_start + a_pos * segment_angle
                vertices.append((CENTER_X + r * math.cos(a), CENTER_Y + r * math.sin(a)))

        # Connect vertices into triangles using a simple fan pattern
        # but with cross-connections for shattered look
        for ring in range(num_rings):
            ring_start = 1 + ring * points_per_ring
            next_ring_start = 1 + (ring + 1) * points_per_ring if ring < num_rings - 1 else ring_start

            for p in range(points_per_ring):
                # Get vertices for this fragment
                if ring == 0:
                    v1 = vertices[0]  # Center
                    v2 = vertices[ring_start + p]
                    v3 = vertices[ring_start + (p + 1) % points_per_ring]
                else:
                    prev_ring_start = 1 + (ring - 1) * points_per_ring
                    v1 = vertices[prev_ring_start + p]
                    v2 = vertices[ring_start + p]
                    v3 = vertices[ring_start + (p + 1) % points_per_ring]

                # Color based on ring and position - audio affects cycling
                t = (ring / num_rings + p / points_per_ring * 0.2 + inner_shift + audio_level * 0.1) % 1.0
                color = get_gradient_color(t, gradient_type, inner_shift)

                points = [(int(v1[0]), int(v1[1])), (int(v2[0]), int(v2[1])), (int(v3[0]), int(v3[1]))]
                if len(set(points)) >= 3:  # Ensure valid triangle
                    pygame.draw.polygon(screen, color, points)

                # Second triangle to fill the quad
                if ring > 0:
                    v4 = vertices[prev_ring_start + (p + 1) % points_per_ring]
                    t2 = (ring / num_rings + (p + 0.5) / points_per_ring * 0.2 + inner_shift) % 1.0
                    color2 = get_gradient_color(t2, gradient_type, inner_shift)
                    points2 = [(int(v1[0]), int(v1[1])), (int(v3[0]), int(v3[1])), (int(v4[0]), int(v4[1]))]
                    if len(set(points2)) >= 3:
                        pygame.draw.polygon(screen, color2, points2)


def draw_kaleidoscope_crystal(screen, angle, gradient_type, num_segments, inner_shift,
                              pulse_scale=1.0, audio_level=0.0):
    """Crystalline structure - hexagonal-ish fragments that tile with audio reactivity."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    base_radius = int(diagonal / 2) + 50
    radius = int(base_radius * pulse_scale)
    segment_angle = 2 * math.pi / num_segments

    # More layers when audio is loud
    num_layers = 4 + int(audio_level * 2)

    for seg in range(num_segments):
        seg_start = seg * segment_angle + angle
        is_mirrored = (seg % 2 == 1)

        for layer in range(num_layers):
            # Audio creates breathing/pulsing per layer
            layer_pulse = 1.0 + math.sin(layer * 2 + inner_shift * 4) * audio_level * 0.15
            r_inner = (layer / num_layers) * radius * layer_pulse
            r_mid = ((layer + 0.5) / num_layers) * radius * layer_pulse
            r_outer = ((layer + 1) / num_layers) * radius * layer_pulse

            # Create diamond/kite shapes
            num_shapes = layer + 1

            for s in range(num_shapes):
                if is_mirrored:
                    s_pos = (num_shapes - s - 0.5) / num_shapes
                else:
                    s_pos = (s + 0.5) / num_shapes

                # Audio adds angular jitter
                jitter = math.sin(s * 3 + inner_shift * 6) * audio_level * 0.03
                a_center = seg_start + s_pos * segment_angle + jitter
                a_left = a_center - segment_angle / (num_shapes * 2)
                a_right = a_center + segment_angle / (num_shapes * 2)

                # Kite/diamond shape
                p_inner = (CENTER_X + r_inner * math.cos(a_center), CENTER_Y + r_inner * math.sin(a_center))
                p_left = (CENTER_X + r_mid * math.cos(a_left), CENTER_Y + r_mid * math.sin(a_left))
                p_right = (CENTER_X + r_mid * math.cos(a_right), CENTER_Y + r_mid * math.sin(a_right))
                p_outer = (CENTER_X + r_outer * math.cos(a_center), CENTER_Y + r_outer * math.sin(a_center))

                # Upper triangle - audio affects color cycling
                t1 = (layer / num_layers + s / num_shapes * 0.3 + inner_shift + audio_level * 0.1) % 1.0
                color1 = get_gradient_color(t1, gradient_type, inner_shift)
                points1 = [(int(p_inner[0]), int(p_inner[1])),
                           (int(p_left[0]), int(p_left[1])),
                           (int(p_right[0]), int(p_right[1]))]
                pygame.draw.polygon(screen, color1, points1)

                # Lower triangle (slightly different color for faceted look)
                t2 = (layer / num_layers + (s + 0.5) / num_shapes * 0.3 + inner_shift) % 1.0
                color2 = get_gradient_color(t2, gradient_type, inner_shift)
                points2 = [(int(p_left[0]), int(p_left[1])),
                           (int(p_right[0]), int(p_right[1])),
                           (int(p_outer[0]), int(p_outer[1]))]
                pygame.draw.polygon(screen, color2, points2)


def draw_kaleidoscope_mosaic(screen, angle, gradient_type, num_segments, inner_shift,
                             pulse_scale=1.0, audio_level=0.0):
    """Dense mosaic tessellation - many small fragments for B&W mode."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    base_radius = int(diagonal / 2) + 50
    radius = int(base_radius * pulse_scale)
    segment_angle = 2 * math.pi / num_segments

    # Dense tessellation - many rings and subdivisions
    num_rings = 10 + int(audio_level * 4)

    for seg in range(num_segments):
        seg_start = seg * segment_angle + angle
        is_mirrored = (seg % 2 == 1)

        for ring in range(num_rings):
            r_inner = (ring / num_rings) * radius
            r_outer = ((ring + 1) / num_rings) * radius
            r_mid = (r_inner + r_outer) / 2

            # More subdivisions in outer rings
            subdivs = 3 + ring
            sub_angle = segment_angle / subdivs

            for sub in range(subdivs):
                if is_mirrored:
                    sub_idx = subdivs - 1 - sub
                else:
                    sub_idx = sub

                a1 = seg_start + sub_idx * sub_angle
                a2 = seg_start + (sub_idx + 1) * sub_angle
                a_mid = (a1 + a2) / 2

                # Wobble based on audio
                wobble = math.sin(ring * 2 + sub * 3 + inner_shift * 4) * audio_level * 0.02

                # Create 4 triangles per cell for mosaic effect
                # Center point of the cell
                cx = CENTER_X + r_mid * math.cos(a_mid + wobble)
                cy = CENTER_Y + r_mid * math.sin(a_mid + wobble)

                # Corner points
                p_inner_left = (CENTER_X + r_inner * math.cos(a1), CENTER_Y + r_inner * math.sin(a1))
                p_inner_right = (CENTER_X + r_inner * math.cos(a2), CENTER_Y + r_inner * math.sin(a2))
                p_outer_left = (CENTER_X + r_outer * math.cos(a1), CENTER_Y + r_outer * math.sin(a1))
                p_outer_right = (CENTER_X + r_outer * math.cos(a2), CENTER_Y + r_outer * math.sin(a2))

                # 4 triangles meeting at center - each with slightly different shade
                triangles = [
                    (p_inner_left, p_inner_right, (cx, cy)),   # inner
                    (p_inner_right, p_outer_right, (cx, cy)),  # right
                    (p_outer_right, p_outer_left, (cx, cy)),   # outer
                    (p_outer_left, p_inner_left, (cx, cy)),    # left
                ]

                for i, (p1, p2, p3) in enumerate(triangles):
                    # Vary the shade for each triangle
                    t = (ring / num_rings + sub / subdivs * 0.3 + i * 0.1 + inner_shift) % 1.0
                    color = get_gradient_color(t, gradient_type, inner_shift)

                    points = [(int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (int(p3[0]), int(p3[1]))]
                    pygame.draw.polygon(screen, color, points)


def draw_kaleidoscope_gradient(screen, angle, color_mode, num_segments, inner_shift=0.0,
                               audio_level=0.0, audio_peak=False, rotation_direction=1):
    """Draw a kaleidoscope effect using vector gradients.

    Selects from multiple pattern styles based on color_mode.
    Audio reactivity: pulse scale, direction changes, pattern warping.
    """
    # Select gradient type (0-8, 9 total gradients)
    gradient_type = int(color_mode * 9) % 9

    # Select pattern style based on gradient type
    # B&W (type 8) gets the dense mosaic pattern
    if gradient_type == 8:
        pattern_style = 4  # mosaic
    else:
        pattern_style = gradient_type % 4

    # Audio-reactive modifications
    # Pulse effect - scale radius based on audio level
    pulse_scale = 1.0 + audio_level * 0.3

    # Apply rotation direction (can flip on audio peaks)
    adjusted_angle = angle * rotation_direction

    # Warp the inner_shift based on audio for crawling speed changes
    audio_shift = inner_shift + audio_level * 0.2

    if pattern_style == 0:
        draw_kaleidoscope_radial(screen, adjusted_angle, gradient_type, num_segments,
                                 audio_shift, pulse_scale, audio_level)
    elif pattern_style == 1:
        draw_kaleidoscope_triangles(screen, adjusted_angle, gradient_type, num_segments,
                                    audio_shift, pulse_scale, audio_level)
    elif pattern_style == 2:
        draw_kaleidoscope_shattered(screen, adjusted_angle, gradient_type, num_segments,
                                    audio_shift, pulse_scale, audio_level)
    elif pattern_style == 3:
        draw_kaleidoscope_crystal(screen, adjusted_angle, gradient_type, num_segments,
                                  audio_shift, pulse_scale, audio_level)
    else:
        draw_kaleidoscope_mosaic(screen, adjusted_angle, gradient_type, num_segments,
                                 audio_shift, pulse_scale, audio_level)


def create_kaleidoscope_base(src_surface, num_segments):
    """Create a kaleidoscope pattern from a source image (computed once).

    Takes a wedge from the source, mirrors it, and tiles it around the center.
    This is the expensive operation - done once per image/segment combo.
    """
    src_width, src_height = src_surface.get_size()

    # Output size - square, large enough to cover screen even when scaled
    diagonal = int(math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)) + 200
    out_size = diagonal
    out_surface = pygame.Surface((out_size, out_size))

    cx = out_size // 2
    cy = out_size // 2
    max_radius = out_size // 2

    # Angle per segment
    segment_angle = 2 * math.pi / num_segments

    # Sample step for performance
    sample_step = 2

    for y in range(0, out_size, sample_step):
        for x in range(0, out_size, sample_step):
            dx = x - cx
            dy = y - cy
            r = math.sqrt(dx * dx + dy * dy)

            if r < max_radius and r > 0:
                # Get angle of this pixel
                theta = math.atan2(dy, dx)

                # Normalize theta to 0..2pi
                theta_norm = (theta + math.pi) % (2 * math.pi)

                # Find position within segment (0 to segment_angle)
                segment_idx = int(theta_norm / segment_angle)
                pos_in_segment = theta_norm - segment_idx * segment_angle

                # Mirror every other segment for kaleidoscope effect
                if segment_idx % 2 == 1:
                    pos_in_segment = segment_angle - pos_in_segment

                # Map to source image coordinates
                # Use the full image width for the segment angle
                src_x = int((pos_in_segment / segment_angle) * src_width) % src_width
                # Radius maps to Y - use modulo for tiling effect
                src_y = int((r / max_radius) * src_height * 2) % src_height

                color = src_surface.get_at((src_x, src_y))[:3]

                # Fill the sample block
                for sy in range(sample_step):
                    for sx in range(sample_step):
                        if x + sx < out_size and y + sy < out_size:
                            out_surface.set_at((x + sx, y + sy), color)
            else:
                # Center pixel or outside - black
                for sy in range(sample_step):
                    for sx in range(sample_step):
                        if x + sx < out_size and y + sy < out_size:
                            out_surface.set_at((x + sx, y + sy), (0, 0, 0))

    return out_surface


def draw_base_image(screen, angle, image_index, kaleidoscope_mode=False, num_segments=6, kaleido_shift=0.0):
    """Draw an image with optional kaleidoscope effect.

    For kaleidoscope mode, we compute the pattern ONCE per image/segment combo,
    then animate using fast operations: rotation + scale (zoom pulsing).
    """
    global source_images, kaleidoscope_cache

    if not source_images:
        return False

    # Get the image
    idx = image_index % len(source_images)
    filepath = source_images[idx]

    if kaleidoscope_mode:
        # Cache key is just filepath + segments (no shift - that's animated cheaply)
        cache_key = (filepath, num_segments)

        if cache_key not in kaleidoscope_cache:
            # Load source image and create kaleidoscope (expensive, but only once)
            try:
                print(f"[Color-Wheel] Creating kaleidoscope for {os.path.basename(filepath)} with {num_segments} segments...")
                src_surface = pygame.image.load(filepath)
                kaleidoscope_cache[cache_key] = create_kaleidoscope_base(src_surface, num_segments)
                print(f"[Color-Wheel] Kaleidoscope created and cached.")

                # Limit cache size (but keep more since we're not re-generating)
                if len(kaleidoscope_cache) > 30:
                    keys = list(kaleidoscope_cache.keys())
                    for k in keys[:15]:
                        del kaleidoscope_cache[k]
            except Exception as e:
                print(f"Error creating kaleidoscope: {e}")
                return False

        surface = kaleidoscope_cache.get(cache_key)
        if surface is None:
            return False

        # Animate with zoom pulsing based on kaleido_shift
        # This creates a "breathing" or "tunnel" effect without regenerating
        zoom_factor = 1.0 + 0.3 * math.sin(kaleido_shift * 0.5)

        # Scale the surface (fast operation)
        orig_size = surface.get_size()
        new_size = (int(orig_size[0] * zoom_factor), int(orig_size[1] * zoom_factor))
        scaled = pygame.transform.scale(surface, new_size)

        # Rotate the scaled image
        angle_degrees = -angle * 180 / math.pi
        rotated = pygame.transform.rotate(scaled, angle_degrees)

    else:
        # Standard polar remap
        surface = load_and_polar_remap(filepath, (WIDTH, HEIGHT))
        if surface is None:
            return False

        # Just rotate for polar mode
        angle_degrees = -angle * 180 / math.pi
        rotated = pygame.transform.rotate(surface, angle_degrees)

    # Center on screen
    rot_rect = rotated.get_rect(center=(CENTER_X, CENTER_Y))
    screen.blit(rotated, rot_rect)

    return True


def draw_mask_triangles(screen, angle, density):
    """Classic triangular cutouts radiating from center."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_cutouts = int(4 + density * 14)
    segment_angle = 2 * math.pi / num_cutouts
    cutout_portion = 0.3 + (1 - density) * 0.4

    for i in range(num_cutouts):
        seg_start = i * segment_angle + angle
        cutout_half = segment_angle * cutout_portion / 2
        seg_center = seg_start + segment_angle / 2

        black_start = seg_start
        black_end = seg_center - cutout_half

        if black_end > black_start:
            points = [(CENTER_X, CENTER_Y)]
            for j in range(9):
                a = black_start + (black_end - black_start) * j / 8
                x = CENTER_X + radius * math.cos(a)
                y = CENTER_Y + radius * math.sin(a)
                points.append((int(x), int(y)))
            pygame.draw.polygon(screen, mask_color, points)

        black_start2 = seg_center + cutout_half
        black_end2 = seg_start + segment_angle

        if black_end2 > black_start2:
            points = [(CENTER_X, CENTER_Y)]
            for j in range(9):
                a = black_start2 + (black_end2 - black_start2) * j / 8
                x = CENTER_X + radius * math.cos(a)
                y = CENTER_Y + radius * math.sin(a)
                points.append((int(x), int(y)))
            pygame.draw.polygon(screen, mask_color, points)


def draw_mask_spiral(screen, angle, density):
    """Spiral arms radiating from center."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_arms = int(3 + density * 9)
    twist = 2.0 + density * 3.0

    for arm in range(num_arms):
        base_angle_arm = arm * 2 * math.pi / num_arms + angle

        points = [(CENTER_X, CENTER_Y)]

        for r in range(0, max_radius, 10):
            t = r / max_radius
            a = base_angle_arm + t * twist
            x = CENTER_X + r * math.cos(a)
            y = CENTER_Y + r * math.sin(a)
            points.append((int(x), int(y)))

        arm_width = math.pi / num_arms * 0.7

        for r in range(max_radius, -1, -10):
            t = r / max_radius
            a = base_angle_arm + t * twist + arm_width * (0.3 + t * 0.7)
            x = CENTER_X + r * math.cos(a)
            y = CENTER_Y + r * math.sin(a)
            points.append((int(x), int(y)))

        pygame.draw.polygon(screen, mask_color, points)


def draw_mask_diamonds(screen, angle, density):
    """Radiating diamond/rhombus pattern."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_spokes = int(6 + density * 12)
    num_rings = int(4 + density * 8)
    ring_spacing = max_radius / num_rings

    spoke_angle = 2 * math.pi / num_spokes

    for ring in range(num_rings):
        inner_r = ring * ring_spacing
        outer_r = (ring + 1) * ring_spacing

        for spoke in range(num_spokes):
            if (ring + spoke) % 2 == 0:
                a1 = spoke * spoke_angle + angle
                a2 = (spoke + 1) * spoke_angle + angle
                mid_a = (a1 + a2) / 2

                points = [
                    (int(CENTER_X + inner_r * math.cos(mid_a)),
                     int(CENTER_Y + inner_r * math.sin(mid_a))),
                    (int(CENTER_X + (inner_r + outer_r) / 2 * math.cos(a1)),
                     int(CENTER_Y + (inner_r + outer_r) / 2 * math.sin(a1))),
                    (int(CENTER_X + outer_r * math.cos(mid_a)),
                     int(CENTER_Y + outer_r * math.sin(mid_a))),
                    (int(CENTER_X + (inner_r + outer_r) / 2 * math.cos(a2)),
                     int(CENTER_Y + (inner_r + outer_r) / 2 * math.sin(a2))),
                ]
                pygame.draw.polygon(screen, mask_color, points)


def draw_mask_fish_scales(screen, angle, density):
    """Overlapping arc pattern like fish scales."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_spokes = int(8 + density * 16)
    num_rings = int(5 + density * 10)
    ring_spacing = max_radius / num_rings

    spoke_angle = 2 * math.pi / num_spokes

    for ring in range(num_rings):
        r = (ring + 0.5) * ring_spacing
        offset = spoke_angle / 2 if ring % 2 == 1 else 0

        for spoke in range(num_spokes):
            base_a = spoke * spoke_angle + angle + offset

            scale_size = ring_spacing * 0.5 * (0.6 + ring * 0.1)
            points = []

            for j in range(13):
                arc_a = base_a + math.pi - math.pi * 0.4 + math.pi * 0.8 * j / 12
                px = CENTER_X + r * math.cos(base_a) + scale_size * math.cos(arc_a)
                py = CENTER_Y + r * math.sin(base_a) + scale_size * math.sin(arc_a)
                points.append((int(px), int(py)))

            if len(points) >= 3:
                pygame.draw.polygon(screen, mask_color, points)


def draw_mask_interlocking(screen, angle, density):
    """Interlocking curved shapes."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_arms = int(4 + density * 8)
    arm_angle = 2 * math.pi / num_arms

    for arm in range(num_arms):
        if arm % 2 == 0:
            base_a = arm * arm_angle + angle

            points = [(CENTER_X, CENTER_Y)]

            for r in range(0, max_radius, 8):
                t = r / max_radius
                wobble = math.sin(t * math.pi * (3 + density * 4)) * arm_angle * 0.15
                a = base_a + wobble
                x = CENTER_X + r * math.cos(a)
                y = CENTER_Y + r * math.sin(a)
                points.append((int(x), int(y)))

            for r in range(max_radius, -1, -20):
                a = base_a + arm_angle
                x = CENTER_X + r * math.cos(a)
                y = CENTER_Y + r * math.sin(a)
                points.append((int(x), int(y)))

            pygame.draw.polygon(screen, mask_color, points)


def draw_mask_hexagons(screen, angle, density):
    """Hexagonal pattern in concentric rings from center."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    hex_size = 25 + (1 - density) * 40

    ring_spacing = hex_size * 1.8
    num_rings = int(max_radius / ring_spacing) + 1

    for ring in range(num_rings):
        if ring == 0:
            points = []
            for i in range(6):
                ha = i * math.pi / 3 + angle
                hx = CENTER_X + hex_size * 0.85 * math.cos(ha)
                hy = CENTER_Y + hex_size * 0.85 * math.sin(ha)
                points.append((int(hx), int(hy)))
            pygame.draw.polygon(screen, mask_color, points)
        else:
            num_hexes = ring * 6
            r = ring * ring_spacing

            for i in range(num_hexes):
                hex_angle = (i / num_hexes) * 2 * math.pi + angle
                if ring % 2 == 1:
                    hex_angle += math.pi / num_hexes

                if i % 2 == 0:
                    cx = CENTER_X + r * math.cos(hex_angle)
                    cy = CENTER_Y + r * math.sin(hex_angle)

                    points = []
                    for j in range(6):
                        ha = j * math.pi / 3 + angle
                        hx = cx + hex_size * 0.85 * math.cos(ha)
                        hy = cy + hex_size * 0.85 * math.sin(ha)
                        points.append((int(hx), int(hy)))
                    pygame.draw.polygon(screen, mask_color, points)


def draw_mask_circles(screen, angle, density):
    """Concentric circles with radial gaps - creates a bullseye effect."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_rings = int(6 + density * 12)
    num_gaps = int(4 + density * 8)
    ring_width = max_radius / num_rings
    gap_angle = 2 * math.pi / num_gaps
    gap_size = 0.15 + (1 - density) * 0.25  # Portion of segment that's a gap

    for ring in range(num_rings):
        if ring % 2 == 0:
            inner_r = ring * ring_width
            outer_r = (ring + 1) * ring_width

            for gap in range(num_gaps):
                # Draw arc segment (the mask part, not the gap)
                arc_start = gap * gap_angle + angle + gap_angle * gap_size / 2
                arc_end = (gap + 1) * gap_angle + angle - gap_angle * gap_size / 2

                # Build arc as polygon
                points = []
                steps = 12
                for i in range(steps + 1):
                    a = arc_start + (arc_end - arc_start) * i / steps
                    points.append((int(CENTER_X + inner_r * math.cos(a)),
                                   int(CENTER_Y + inner_r * math.sin(a))))
                for i in range(steps, -1, -1):
                    a = arc_start + (arc_end - arc_start) * i / steps
                    points.append((int(CENTER_X + outer_r * math.cos(a)),
                                   int(CENTER_Y + outer_r * math.sin(a))))

                if len(points) >= 3:
                    pygame.draw.polygon(screen, mask_color, points)


def draw_mask_starburst(screen, angle, density):
    """Sharp triangular rays emanating from center like a starburst."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_rays = int(8 + density * 16)
    ray_angle = 2 * math.pi / num_rays

    for ray in range(num_rays):
        if ray % 2 == 0:
            # Alternating rays are mask
            base_a = ray * ray_angle + angle
            # Sharp triangular ray
            tip_a = base_a + ray_angle / 2

            # Ray tapers from wide at center to point at edge
            inner_width = ray_angle * 0.4
            outer_width = ray_angle * 0.05

            points = [
                (int(CENTER_X + 20 * math.cos(base_a - inner_width / 2)),
                 int(CENTER_Y + 20 * math.sin(base_a - inner_width / 2))),
                (int(CENTER_X + 20 * math.cos(base_a + inner_width / 2)),
                 int(CENTER_Y + 20 * math.sin(base_a + inner_width / 2))),
                (int(CENTER_X + max_radius * math.cos(tip_a + outer_width / 2)),
                 int(CENTER_Y + max_radius * math.sin(tip_a + outer_width / 2))),
                (int(CENTER_X + max_radius * math.cos(tip_a - outer_width / 2)),
                 int(CENTER_Y + max_radius * math.sin(tip_a - outer_width / 2))),
            ]
            pygame.draw.polygon(screen, mask_color, points)


def draw_mask_petals(screen, angle, density):
    """Flower petal shapes radiating outward."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_petals = int(5 + density * 10)
    petal_angle = 2 * math.pi / num_petals

    for petal in range(num_petals):
        base_a = petal * petal_angle + angle

        # Create petal shape using bezier-like curve
        points = [(CENTER_X, CENTER_Y)]

        # Left edge of petal (curves out then in)
        for i in range(20):
            t = i / 19
            # Petal width varies along length
            width = math.sin(t * math.pi) * petal_angle * 0.4
            r = t * max_radius
            a = base_a - width
            points.append((int(CENTER_X + r * math.cos(a)),
                           int(CENTER_Y + r * math.sin(a))))

        # Right edge of petal (curves back)
        for i in range(19, -1, -1):
            t = i / 19
            width = math.sin(t * math.pi) * petal_angle * 0.4
            r = t * max_radius
            a = base_a + width
            points.append((int(CENTER_X + r * math.cos(a)),
                           int(CENTER_Y + r * math.sin(a))))

        pygame.draw.polygon(screen, mask_color, points)


def draw_mask_crescents(screen, angle, density):
    """Crescent moon shapes in concentric rings."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_rings = int(4 + density * 6)
    crescents_per_ring = int(6 + density * 6)
    ring_spacing = max_radius / num_rings

    for ring in range(num_rings):
        r = (ring + 0.5) * ring_spacing
        crescent_size = ring_spacing * 0.4

        for c in range(crescents_per_ring):
            # Offset alternating rings
            offset = (math.pi / crescents_per_ring) if ring % 2 == 1 else 0
            ca = c * 2 * math.pi / crescents_per_ring + angle + offset

            # Center of crescent
            cx = CENTER_X + r * math.cos(ca)
            cy = CENTER_Y + r * math.sin(ca)

            # Crescent is made of two overlapping circles
            # Outer arc
            points = []
            for i in range(15):
                a = ca - math.pi / 2 + math.pi * i / 14
                points.append((int(cx + crescent_size * math.cos(a)),
                               int(cy + crescent_size * math.sin(a))))

            # Inner arc (offset to create crescent)
            inner_offset = crescent_size * 0.4
            inner_cx = cx + inner_offset * math.cos(ca)
            inner_cy = cy + inner_offset * math.sin(ca)
            for i in range(14, -1, -1):
                a = ca - math.pi / 2 + math.pi * i / 14
                points.append((int(inner_cx + crescent_size * 0.8 * math.cos(a)),
                               int(inner_cy + crescent_size * 0.8 * math.sin(a))))

            if len(points) >= 3:
                pygame.draw.polygon(screen, mask_color, points)


def draw_mask_zigzag(screen, angle, density):
    """Zigzag/chevron pattern radiating from center."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_arms = int(6 + density * 10)
    zigzags_per_arm = int(8 + density * 12)
    arm_angle = 2 * math.pi / num_arms

    for arm in range(num_arms):
        if arm % 2 == 0:
            base_a = arm * arm_angle + angle

            # Build zigzag shape
            points = [(CENTER_X, CENTER_Y)]

            zag_size = arm_angle * 0.3
            segment_len = max_radius / zigzags_per_arm

            # Left edge with zigs
            for z in range(zigzags_per_arm):
                r = (z + 1) * segment_len
                # Alternate left/right
                offset = zag_size if z % 2 == 0 else -zag_size * 0.3
                a = base_a + offset
                points.append((int(CENTER_X + r * math.cos(a)),
                               int(CENTER_Y + r * math.sin(a))))

            # Right edge with zags (mirror)
            for z in range(zigzags_per_arm - 1, -1, -1):
                r = (z + 1) * segment_len
                offset = zag_size if z % 2 == 0 else -zag_size * 0.3
                a = base_a + arm_angle - offset
                points.append((int(CENTER_X + r * math.cos(a)),
                               int(CENTER_Y + r * math.sin(a))))

            pygame.draw.polygon(screen, mask_color, points)


def draw_mask_stars(screen, angle, density):
    """Star shapes scattered in rings from center."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_rings = int(4 + density * 6)
    stars_base = int(4 + density * 4)
    ring_spacing = max_radius / num_rings

    for ring in range(num_rings):
        r = (ring + 0.5) * ring_spacing
        star_size = ring_spacing * (0.3 + density * 0.2)
        num_stars = stars_base + ring * 2

        for s in range(num_stars):
            offset = (math.pi / num_stars) if ring % 2 == 1 else 0
            sa = s * 2 * math.pi / num_stars + angle + offset

            # Center of star
            cx = CENTER_X + r * math.cos(sa)
            cy = CENTER_Y + r * math.sin(sa)

            # 5-pointed star
            points = []
            for i in range(10):
                # Alternate between outer and inner points
                if i % 2 == 0:
                    sr = star_size
                else:
                    sr = star_size * 0.4
                a = sa + i * math.pi / 5
                points.append((int(cx + sr * math.cos(a)),
                               int(cy + sr * math.sin(a))))

            pygame.draw.polygon(screen, mask_color, points)


def draw_mask_waves(screen, angle, density):
    """Wavy concentric rings."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    num_rings = int(5 + density * 8)
    wave_freq = int(6 + density * 10)
    ring_spacing = max_radius / num_rings
    wave_amp = ring_spacing * 0.3

    for ring in range(num_rings):
        if ring % 2 == 0:
            base_r = ring * ring_spacing

            # Build wavy ring
            points = []
            steps = 60

            # Outer wavy edge
            for i in range(steps + 1):
                a = i * 2 * math.pi / steps + angle
                wave = math.sin(a * wave_freq + ring) * wave_amp
                r = base_r + ring_spacing + wave
                points.append((int(CENTER_X + r * math.cos(a)),
                               int(CENTER_Y + r * math.sin(a))))

            # Inner wavy edge
            for i in range(steps, -1, -1):
                a = i * 2 * math.pi / steps + angle
                wave = math.sin(a * wave_freq + ring + math.pi) * wave_amp * 0.5
                r = base_r + wave
                points.append((int(CENTER_X + r * math.cos(a)),
                               int(CENTER_Y + r * math.sin(a))))

            if len(points) >= 3:
                pygame.draw.polygon(screen, mask_color, points)


def draw_mask_radial_lines(screen, angle, density, audio_level=0.0):
    """Concentric rings crossed by radial lines at 15° intervals."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    # Radial lines at 15° (24 total) - density affects line thickness
    num_lines = 24  # Fixed at 15° intervals
    line_width = int(3 + density * 8 + audio_level * 4)

    for i in range(num_lines):
        if i % 2 == 0:  # Alternating lines
            a = i * (math.pi / 12) + angle  # 15° = pi/12

            # Draw as thick polygon
            half_width = math.pi / 120 * (1 + density) + audio_level * 0.02
            points = [
                (CENTER_X, CENTER_Y),
                (int(CENTER_X + max_radius * math.cos(a - half_width)),
                 int(CENTER_Y + max_radius * math.sin(a - half_width))),
                (int(CENTER_X + max_radius * math.cos(a + half_width)),
                 int(CENTER_Y + max_radius * math.sin(a + half_width))),
            ]
            pygame.draw.polygon(screen, mask_color, points)

    # Concentric rings
    num_rings = int(4 + density * 8)
    ring_spacing = max_radius / num_rings
    ring_width = ring_spacing * (0.2 + density * 0.3 + audio_level * 0.1)

    for ring in range(num_rings):
        if ring % 2 == 1:
            r = ring * ring_spacing
            inner_r = max(0, r - ring_width / 2)
            outer_r = r + ring_width / 2

            # Draw ring as polygon segments
            steps = 60
            points = []
            for j in range(steps + 1):
                a = j * 2 * math.pi / steps
                points.append((int(CENTER_X + outer_r * math.cos(a)),
                               int(CENTER_Y + outer_r * math.sin(a))))
            for j in range(steps, -1, -1):
                a = j * 2 * math.pi / steps
                points.append((int(CENTER_X + inner_r * math.cos(a)),
                               int(CENTER_Y + inner_r * math.sin(a))))

            if len(points) >= 3:
                pygame.draw.polygon(screen, mask_color, points)


def draw_mask_conical_grid(screen, angle, density, audio_level=0.0):
    """Conical/polar grid with alternating black and clear cells."""
    diagonal = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)
    max_radius = int(diagonal / 2) + 50
    mask_color = get_mask_color(current_audio_level)

    # Number of radial divisions and ring divisions
    num_radial = int(8 + density * 16)  # Angular divisions
    num_rings = int(5 + density * 10)   # Radial divisions
    ring_spacing = max_radius / num_rings
    radial_angle = 2 * math.pi / num_radial

    for ring in range(num_rings):
        inner_r = ring * ring_spacing
        outer_r = (ring + 1) * ring_spacing

        # Audio can pulse the rings
        pulse = 1.0 + math.sin(ring * 0.5 + audio_level * 10) * audio_level * 0.1

        for radial in range(num_radial):
            # Checkerboard pattern - alternating cells
            if (ring + radial) % 2 == 0:
                a1 = radial * radial_angle + angle
                a2 = (radial + 1) * radial_angle + angle

                # Build cell polygon
                points = []
                steps = 4
                # Inner arc
                for j in range(steps + 1):
                    a = a1 + (a2 - a1) * j / steps
                    r = inner_r * pulse
                    points.append((int(CENTER_X + r * math.cos(a)),
                                   int(CENTER_Y + r * math.sin(a))))
                # Outer arc (reverse)
                for j in range(steps, -1, -1):
                    a = a1 + (a2 - a1) * j / steps
                    r = outer_r * pulse
                    points.append((int(CENTER_X + r * math.cos(a)),
                                   int(CENTER_Y + r * math.sin(a))))

                if len(points) >= 3:
                    pygame.draw.polygon(screen, mask_color, points)


def draw(screen, etc):
    """Main draw function."""
    global frame_count, base_angle, mask_angle
    global base_drift_phase, mask_drift_phase, last_audio_peak
    global current_image_index, kaleidoscope_shift
    global rotation_direction, peak_cooldown
    global current_audio_level

    # Ensure setup has run
    setup(screen, etc)

    # Get knob values
    base_speed_bias = (etc.knob1 - 0.5) * 0.08
    knob2_value = etc.knob2
    pattern_select = etc.knob3
    density = etc.knob4
    base_mode = etc.knob5  # 0-0.33 = gradients, 0.33-0.66 = images, 0.66-1.0 = kaleidoscope

    # Determine if we're in kaleidoscope mode
    kaleidoscope_mode = base_mode >= 0.66

    # In kaleidoscope mode, knob2 controls segments instead of mask speed
    if kaleidoscope_mode:
        num_segments = int(3 + knob2_value * 9)  # 3 to 12 segments
        mask_speed_bias = 0.02  # Fixed slow mask rotation
    else:
        num_segments = 6
        mask_speed_bias = (knob2_value - 0.5) * 0.08

    # Get audio level
    audio_data = getattr(etc, 'audio_in', None)
    audio_level = 0.0
    if audio_data and len(audio_data) > 0:
        total = 0.0
        for sample in audio_data:
            total += abs(sample)
        audio_level = min(1.0, total / len(audio_data) / 32768.0 * 3)

    # Update global for mask color reactivity
    current_audio_level = audio_level

    # Track audio peaks for direction changes
    audio_peak = False

    if peak_cooldown > 0:
        peak_cooldown -= 1

    # Detect strong audio peak - flip rotation direction
    if audio_level > 0.7 and peak_cooldown == 0:
        audio_peak = True
        rotation_direction *= -1
        peak_cooldown = 30  # Cooldown to prevent rapid flipping

    # Update drift phases
    base_drift_phase += 0.02 + audio_level * 0.05
    mask_drift_phase += 0.025 + audio_level * 0.03

    # Audio peaks cause momentary speed bursts
    if audio_level > 0.6 and frame_count - last_audio_peak > 15:
        last_audio_peak = frame_count
        if (frame_count // 20) % 2 == 0:
            base_drift_phase += 0.5
        else:
            mask_drift_phase += 0.5

    # Calculate organic speeds
    base_speed = get_organic_speed(base_speed_bias, base_drift_phase, frame_count, audio_level)
    mask_speed = get_organic_speed(mask_speed_bias, mask_drift_phase + 10, frame_count, audio_level * 0.7)

    # Update rotation angles
    base_angle += base_speed
    mask_angle += mask_speed

    base_angle = base_angle % (2 * math.pi)
    mask_angle = mask_angle % (2 * math.pi)

    # Update kaleidoscope shift (animated crawl through the source image)
    # Audio makes it crawl faster
    kaleidoscope_shift += 0.015 + audio_level * 0.08

    # Clear screen
    screen.fill((0, 0, 0))

    # Draw base layer
    if base_mode < 0.33:
        # Gradient mode (0.0 - 0.33)
        draw_base_gradient(screen, base_angle, base_mode * 3)  # Scale to 0-1
    elif base_mode < 0.66:
        # Polar image mode (0.33 - 0.66)
        if source_images:
            img_t = (base_mode - 0.33) * 3  # Scale to 0-1
            current_image_index = int(img_t * len(source_images)) % len(source_images)
            if not draw_base_image(screen, base_angle, current_image_index,
                                   kaleidoscope_mode=False):
                draw_base_gradient(screen, base_angle, 0)
        else:
            draw_base_gradient(screen, base_angle, 0)
    else:
        # Kaleidoscope mode (0.66 - 1.0) - vector-based, instant!
        # Map 0.66-1.0 to gradient types (0-1 range for 9 gradient types)
        gradient_select = (base_mode - 0.66) * 3  # 0 to 1
        draw_kaleidoscope_gradient(screen, base_angle, gradient_select,
                                   num_segments, kaleidoscope_shift,
                                   audio_level, audio_peak, rotation_direction)

    # Draw mask layer based on pattern selection (16 patterns)
    # Map knob3 (0-1) to pattern index (0-15)
    pattern_idx = int(pattern_select * 16) % 16

    # Audio-reactive mask angle - adds wobble on beats
    reactive_mask_angle = mask_angle + math.sin(frame_count * 0.1) * audio_level * 0.1

    if pattern_idx == 0:
        draw_mask_triangles(screen, reactive_mask_angle, density)
    elif pattern_idx == 1:
        draw_mask_spiral(screen, reactive_mask_angle, density)
    elif pattern_idx == 2:
        draw_mask_diamonds(screen, reactive_mask_angle, density)
    elif pattern_idx == 3:
        draw_mask_fish_scales(screen, reactive_mask_angle, density)
    elif pattern_idx == 4:
        draw_mask_interlocking(screen, reactive_mask_angle, density)
    elif pattern_idx == 5:
        draw_mask_hexagons(screen, reactive_mask_angle, density)
    elif pattern_idx == 6:
        draw_mask_circles(screen, reactive_mask_angle, density)
    elif pattern_idx == 7:
        draw_mask_starburst(screen, reactive_mask_angle, density)
    elif pattern_idx == 8:
        draw_mask_petals(screen, reactive_mask_angle, density)
    elif pattern_idx == 9:
        draw_mask_crescents(screen, reactive_mask_angle, density)
    elif pattern_idx == 10:
        draw_mask_zigzag(screen, reactive_mask_angle, density)
    elif pattern_idx == 11:
        draw_mask_stars(screen, reactive_mask_angle, density)
    elif pattern_idx == 12:
        draw_mask_waves(screen, reactive_mask_angle, density)
    elif pattern_idx == 13:
        draw_mask_radial_lines(screen, reactive_mask_angle, density, audio_level)
    elif pattern_idx == 14:
        draw_mask_conical_grid(screen, reactive_mask_angle, density, audio_level)
    else:
        draw_mask_hexagons(screen, reactive_mask_angle, density)  # fallback

    frame_count += 1
