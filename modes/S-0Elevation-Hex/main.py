# Elevation Hex Mode
# 3D hexagonal pillars with audio-reactive heights
# Infinite scrolling hex field with fly-over camera
#
# Knob 1: Camera elevation (0 = top view, 1 = side view)
# Knob 2: Flight speed
# Knob 3: (unused)
# Knob 4: Height multiplier + audio sensitivity
# Knob 5: Color mode (10 modes matching String Vibration)
#
# Direction changes triggered by loud sounds

import pygame
import math

# Screen dimensions
WIDTH = 1280
HEIGHT = 720

# Hex grid settings
HEX_RADIUS = 55  # Radius of each hexagon (larger = fewer hexes = faster)

# Pre-computed sin/cos for hex corners (6 corners, flat-top)
# These are the offsets from center, will be rotated by heading
HEX_CORNER_COS = [math.cos(math.pi / 3 * i) for i in range(6)]
HEX_CORNER_SIN = [math.sin(math.pi / 3 * i) for i in range(6)]

# Pre-computed sqrt(3) to avoid repeated calculation
SQRT3 = math.sqrt(3)

# State
frame_count = 0
hex_heights = {}  # Dictionary of (q, r) -> current height
heading = 0.0  # Direction of travel in radians
target_heading = 0.0  # Target heading for smooth turns
camera_x = 0.0  # Camera world position
camera_y = 0.0
last_loud_frame = -100  # Frame when last loud sound triggered direction change

# Ripple state - list of (center_x, center_y, start_frame, intensity)
# Limited to MAX_RIPPLES for performance
MAX_RIPPLES = 3
ripples = []
last_ripple_frame = -30  # Frame when last ripple was spawned


def hsv_to_rgb_fast(h, s, v):
    """Fast HSV to RGB conversion (inline, no colorsys)."""
    if s == 0:
        c = int(v * 255)
        return (c, c, c)

    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = int(v * (1 - s) * 255)
    q = int(v * (1 - f * s) * 255)
    t = int(v * (1 - (1 - f) * s) * 255)
    v = int(v * 255)

    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    return (v, p, q)


def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB colors"""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )


def lerp_color_3(c1, c2, c3, t):
    """Interpolate through 3 colors: c1 at t=0, c2 at t=0.5, c3 at t=1"""
    if t < 0.5:
        return lerp_color(c1, c2, t * 2)
    else:
        return lerp_color(c2, c3, (t - 0.5) * 2)


def get_hex_color(color_mode, ring, num_rings, frame_count):
    """Get color for a hex based on color mode and ring position.

    Returns (base_color, highlight_color, shadow_color, top_color, edge_color)
    """
    # Use ring position for gradient modes (0 = center, 1 = outer edge)
    ring_t = ring / max(1, num_rings)

    # Default edge color is black
    edge_color = (0, 0, 0)

    if color_mode < 0.09:
        # White/Gray
        base = (180, 180, 180)
    elif color_mode < 0.18:
        # Rainbow - each ring gets a different hue
        base = hsv_to_rgb_fast(ring_t, 0.8, 1.0)
    elif color_mode < 0.27:
        # Shifting hue over time
        hue = (frame_count * 0.01 + ring_t * 0.3) % 1.0
        base = hsv_to_rgb_fast(hue, 0.8, 1.0)
    elif color_mode < 0.36:
        # Green
        base = (0, 255, 100)
    elif color_mode < 0.45:
        # Red
        base = (255, 50, 50)
    elif color_mode < 0.54:
        # Green to purple gradient
        green = (0, 255, 100)
        purple = (180, 0, 255)
        base = lerp_color(green, purple, ring_t)
    elif color_mode < 0.63:
        # White to dark gradient (inner bright, outer dark)
        white = (255, 255, 255)
        dark = (40, 40, 40)
        base = lerp_color(white, dark, ring_t)
    elif color_mode < 0.72:
        # Light pink to light blue gradient
        light_pink = (255, 182, 193)
        light_blue = (173, 216, 230)
        base = lerp_color(light_pink, light_blue, ring_t)
    elif color_mode < 0.81:
        # Warm cream to hot pink
        cream = (245, 230, 173)
        hot_pink = (241, 60, 119)
        base = lerp_color(cream, hot_pink, ring_t)
    elif color_mode < 0.90:
        # Pastel trio
        pastel_cream = (242, 243, 226)
        pastel_blue = (178, 229, 248)
        pastel_pink = (244, 179, 239)
        base = lerp_color_3(pastel_cream, pastel_blue, pastel_pink, ring_t)
    else:
        # Wireframe - black pillars with white edges
        base = (5, 5, 10)
        edge_color = (255, 255, 255)

    # Generate highlight, shadow, and top colors from base
    highlight = tuple(min(255, int(c * 1.3)) for c in base)
    shadow = tuple(int(c * 0.4) for c in base)
    top = tuple(min(255, int(c * 1.1)) for c in base)

    return (base, highlight, shadow, top, edge_color)


def axial_to_pixel(q, r, hex_size):
    """Convert axial hex coordinates to pixel coordinates."""
    x = hex_size * 1.5 * q
    y = hex_size * (SQRT3 * 0.5 * q + SQRT3 * r)
    return x, y


def pixel_to_axial(x, y, hex_size):
    """Convert pixel coordinates to axial hex coordinates (returns fractional)."""
    q = (2.0 / 3.0 * x) / hex_size
    r = (-1.0 / 3.0 * x + SQRT3 / 3.0 * y) / hex_size
    return q, r


def axial_round(q, r):
    """Round fractional axial coordinates to nearest hex."""
    s = -q - r
    rq = round(q)
    rr = round(r)
    rs = round(s)

    q_diff = abs(rq - q)
    r_diff = abs(rr - r)
    s_diff = abs(rs - s)

    if q_diff > r_diff and q_diff > s_diff:
        rq = -rr - rs
    elif r_diff > s_diff:
        rr = -rq - rs

    return int(rq), int(rr)


def get_visible_hexes(camera_x, camera_y, hex_size, scale=1.0):
    """Get all hex coordinates visible from camera position.

    Returns hexes that could be visible on screen plus a small margin.
    Simplified for performance.
    """
    # Calculate visible world-space range (accounting for scale)
    # Reduced margin for better performance
    margin = 2
    world_half_width = (WIDTH / 2) / scale + hex_size * margin
    world_half_height = (HEIGHT / 2) / scale + hex_size * margin

    # Just sample corners to find bounds (faster than 8 points)
    min_q, max_q = float('inf'), float('-inf')
    min_r, max_r = float('inf'), float('-inf')

    for dx in (-world_half_width, world_half_width):
        for dy in (-world_half_height, world_half_height):
            q, r = pixel_to_axial(camera_x + dx, camera_y + dy, hex_size)
            q, r = axial_round(q, r)
            if q < min_q: min_q = q
            if q > max_q: max_q = q
            if r < min_r: min_r = r
            if r > max_r: max_r = r

    # Generate all hexes in the bounding box
    visible = []
    for q in range(int(min_q) - 1, int(max_q) + 2):
        for r in range(int(min_r) - 1, int(max_r) + 2):
            visible.append((q, r))

    return visible


def get_hex_distance(q, r):
    """Get distance from origin in hex coordinates."""
    return max(abs(q), abs(r), abs(-q - r))


def project_3d_to_2d(x, y, z, camera_pitch, scale=1.0):
    """Project 3D point to 2D screen coordinates.

    camera_pitch: angle in radians (0 = looking straight down, pi/2 = horizontal)
    """
    cos_p = math.cos(camera_pitch)
    sin_p = math.sin(camera_pitch)

    # Orthographic projection with pitch rotation around X axis
    # X stays the same, Y and Z mix based on pitch
    screen_x = x * scale
    screen_y = (y * cos_p - z * sin_p) * scale

    return screen_x + WIDTH // 2, screen_y + HEIGHT // 2


def draw_hex_pillar(screen, rx, ry, height, hex_size, camera_pitch, rotation, colors, scale):
    """Draw a single hexagonal pillar (optimized).

    rx, ry are pre-rotated world coordinates.
    camera_pitch: angle in radians
    """
    base_color, highlight_color, shadow_color, top_color, edge_color = colors

    # Effective hex size
    effective_size = hex_size * 0.9

    # Pre-compute rotation values
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)

    # Pre-compute projection values
    cos_p = math.cos(camera_pitch)
    sin_p = math.sin(camera_pitch)
    half_w = WIDTH // 2
    half_h = HEIGHT // 2

    # Get corners using pre-computed unit circle values, rotated
    top_corners_2d = []
    bottom_corners_2d = []

    for i in range(6):
        # Rotate pre-computed corner offsets
        uc = HEX_CORNER_COS[i]
        us = HEX_CORNER_SIN[i]
        cx = rx + effective_size * (uc * cos_r - us * sin_r)
        cy = ry + effective_size * (uc * sin_r + us * cos_r)

        # Inline projection (avoid function call overhead)
        sx_top = int(cx * scale + half_w)
        sy_top = int((cy * cos_p - height * sin_p) * scale + half_h)
        sx_bot = int(cx * scale + half_w)
        sy_bot = int(cy * cos_p * scale + half_h)

        top_corners_2d.append((sx_top, sy_top))
        bottom_corners_2d.append((sx_bot, sy_bot))

    # Draw sides - only if camera has some pitch (not pure top-down)
    if camera_pitch > 0.05:
        # Draw faces without sorting (good enough for most views)
        # Pre-compute light direction dot products
        light_angle = -2.356  # -pi * 0.75

        for i in range(6):
            next_i = (i + 1) % 6

            # Build quad
            quad = [
                bottom_corners_2d[i],
                bottom_corners_2d[next_i],
                top_corners_2d[next_i],
                top_corners_2d[i]
            ]

            # Quick backface culling using cross product
            e1x = quad[1][0] - quad[0][0]
            e1y = quad[1][1] - quad[0][1]
            e2x = quad[3][0] - quad[0][0]
            e2y = quad[3][1] - quad[0][1]

            if e1x * e2y - e1y * e2x > 0:
                # Choose color based on face index (approximates lighting)
                # Faces 0,1 are front-ish, 2,3 are side, 4,5 are back-ish
                face_idx = (i - int(rotation * 0.955)) % 6  # 6/2pi ≈ 0.955
                if face_idx in (0, 1):
                    face_color = highlight_color
                elif face_idx in (2, 5):
                    face_color = base_color
                else:
                    face_color = shadow_color

                pygame.draw.polygon(screen, face_color, quad)

    # Draw top face
    pygame.draw.polygon(screen, top_color, top_corners_2d)


def get_hex_phase(q, r):
    """Get a deterministic phase value for any hex coordinate."""
    # Use a hash-like function to get consistent random-ish values
    return ((q * 127 + r * 311) % 1000) / 1000.0 * 2 * math.pi


def setup(screen, etc):
    """Initialize - nothing to do for infinite field."""
    pass


def draw(screen, etc):
    """Main draw function."""
    global frame_count, hex_heights, heading, target_heading
    global camera_x, camera_y, last_loud_frame
    global ripples, last_ripple_frame

    # Get knob values
    camera_angle = etc.knob1  # 0 = top view, 1 = side view
    flight_speed = 1.0 + etc.knob2 * 12.0  # 1 to 13
    # Knob 3 is now unused (direction is audio-triggered)
    # Knob 4 controls both height and audio sensitivity
    height_mult = 50 + etc.knob4 * 250
    audio_sensitivity = 0.5 + etc.knob4 * 2.0
    color_mode = etc.knob5  # 10 color modes (0.0 - 1.0)

    # Get audio data and compute amplitude level (need this early for direction changes)
    audio_data = getattr(etc, 'audio_in', None)
    audio_level = 0.0

    if audio_data and len(audio_data) > 0:
        # Calculate RMS-like amplitude (average of absolute values)
        total = 0.0
        for sample in audio_data:
            total += abs(sample)
        audio_level = total / len(audio_data) / 32768.0  # Normalize to 0-1 range

    # Apply sensitivity for direction change detection
    audio_level_scaled = min(1.0, audio_level * audio_sensitivity * 3)

    # Trigger direction change on loud sounds (with cooldown)
    loud_threshold = 0.5
    cooldown_frames = 45  # Minimum frames between direction changes
    if audio_level_scaled > loud_threshold and (frame_count - last_loud_frame) > cooldown_frames:
        # Turn left or right by 30-60 degrees
        turn_amount = math.pi / 6 + (frame_count % 3) * math.pi / 18  # 30-60 degrees
        if (frame_count // 7) % 2 == 0:
            target_heading += turn_amount
        else:
            target_heading -= turn_amount
        last_loud_frame = frame_count

    # Spawn ripples on audio peaks (more frequent than direction changes)
    ripple_threshold = 0.25
    ripple_cooldown = 20  # Slightly longer cooldown
    if audio_level_scaled > ripple_threshold and (frame_count - last_ripple_frame) > ripple_cooldown:
        # Spawn ripple at a random position near camera
        offset_x = ((frame_count * 127) % 400) - 200
        offset_y = ((frame_count * 311) % 400) - 200
        ripple_x = camera_x + offset_x
        ripple_y = camera_y + offset_y
        ripple_intensity = audio_level_scaled * height_mult

        # Limit total ripples for performance
        if len(ripples) >= MAX_RIPPLES:
            ripples.pop(0)  # Remove oldest
        ripples.append((ripple_x, ripple_y, frame_count, ripple_intensity))
        last_ripple_frame = frame_count

    # Remove old ripples (shorter lifetime for performance)
    ripples = [(rx, ry, sf, intensity) for rx, ry, sf, intensity in ripples
               if frame_count - sf < 80]

    # Smoothly interpolate heading toward target (faster interpolation for snappier turns)
    heading += (target_heading - heading) * 0.1

    # Camera flight - move forward in current heading direction
    # Pillars should appear from top and move down, so camera moves in -Y world direction
    # when heading=0, and rotates from there
    camera_x -= math.sin(heading) * flight_speed
    camera_y -= math.cos(heading) * flight_speed

    # Scale based on camera angle (need this early for visibility calc)
    scale = 0.8 + 0.4 * (1 - camera_angle)

    # Get visible hexes based on camera position and scale
    visible_hexes = get_visible_hexes(camera_x, camera_y, HEX_RADIUS, scale)

    # Apply audio sensitivity to level
    audio_level = min(1.0, audio_level * audio_sensitivity * 3)

    # Clear screen first
    screen.fill((10, 10, 20))

    # Pre-compute values used in the loop
    time_var = frame_count * 0.08
    cos_h = math.cos(heading)
    sin_h = math.sin(heading)
    camera_pitch = camera_angle * 1.47  # ~pi/2 - 0.1

    # Pre-compute ripple data (age, radius, fade for each ripple)
    ripple_data = []
    for ripple_x, ripple_y, start_frame, intensity in ripples:
        ripple_age = frame_count - start_frame
        ripple_radius = ripple_age * 8
        fade = 1.0 - ripple_age * 0.0125  # 1/80
        if fade > 0:
            ripple_data.append((ripple_x, ripple_y, ripple_radius, intensity, fade))

    # Single pass: calculate heights, positions, and sort key
    hex_render_data = []

    for q, r in visible_hexes:
        # Get phase (cached calculation)
        phase = ((q * 127 + r * 311) % 1000) * 0.00628318  # 2*pi/1000

        # Get world position
        px = HEX_RADIUS * 1.5 * q - camera_x
        py = HEX_RADIUS * (SQRT3 * 0.5 * q + SQRT3 * r) - camera_y

        # Rotate by heading
        rx = px * cos_h - py * sin_h
        ry = px * sin_h + py * cos_h

        # Simplified variation (one wave instead of three)
        variation = 0.85 + 0.35 * math.sin(phase + time_var)

        # Calculate ripple contribution (simplified)
        ripple_height = 0.0
        if ripple_data:
            hex_wx = px + camera_x  # World position for ripple
            hex_wy = py + camera_y
            for rip_x, rip_y, rip_radius, rip_intensity, rip_fade in ripple_data:
                dx = hex_wx - rip_x
                dy = hex_wy - rip_y
                dist_sq = dx * dx + dy * dy
                # Use squared distance to avoid sqrt when possible
                rip_radius_sq = rip_radius * rip_radius
                # Quick check before sqrt
                diff_sq = dist_sq - rip_radius_sq
                if abs(diff_sq) < rip_radius_sq * 0.5:  # Rough width check
                    dist = math.sqrt(dist_sq)
                    dist_from_wave = abs(dist - rip_radius)
                    if dist_from_wave < 80:
                        wave_pos = (1.0 - dist_from_wave * 0.0125) * 3.14159
                        ripple_height += math.sin(wave_pos) * rip_intensity * rip_fade

        # Calculate target height
        if audio_level > 0.01 or ripple_height > 0:
            target = audio_level * height_mult * variation * 0.5 + ripple_height
        else:
            target = (25 + 20 * math.sin(phase + time_var * 0.5)) * variation

        target = max(5, target)

        # Get/update current height
        key = (q, r)
        current = hex_heights.get(key, target * 0.5)

        # Simplified interpolation (fixed speed)
        if target > current:
            current = current + (target - current) * 0.18
        else:
            current = current + (target - current) * 0.1
        hex_heights[key] = current

        # Calculate sort key (screen Y)
        screen_y = ry * math.cos(camera_pitch) * scale + HEIGHT // 2

        # Get color (simplified - use q for ring approximation)
        ring = abs(q) % 10

        # Store for rendering
        hex_render_data.append((screen_y, q, r, rx, ry, current, ring))

    # Sort by screen Y (far to near)
    hex_render_data.sort(key=lambda x: x[0])

    # Draw all hex pillars
    for screen_y, q, r, rx, ry, height, ring in hex_render_data:
        if height > 1 or camera_angle < 0.1:
            colors = get_hex_color(color_mode, ring, 10, frame_count)
            draw_hex_pillar(screen, rx, ry, height, HEX_RADIUS, camera_pitch, heading, colors, scale)

    # Cleanup old hexes (less frequently)
    if frame_count % 120 == 0:
        visible_set = set(visible_hexes)
        hex_heights = {k: v for k, v in hex_heights.items() if k in visible_set}

    frame_count += 1
