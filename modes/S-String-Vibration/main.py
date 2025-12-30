# String Vibration Mode
# Vertical strings projected in 3D space with rotation around X and Z axes
# Strings vibrate along the Z-axis (into/out of screen)
#
# AUDIO REACTIVE: When audio is present, strings display a scrolling oscilloscope view
# - Each string shows the audio waveform at a different point in time
# - Sound "fingerprint" scrolls across the field of strings from left to right
# - Without audio, strings animate with a gentle sine wave pattern
#
# Knob 1: Number of strings (8 to 64)
# Knob 2: Vibration amplitude AND smoothness (0 = still + max smooth, 1 = max displacement + no smooth)
# Knob 3: X-axis rotation angle (-90 to +90 degrees) - tilts strings forward/back
# Knob 4: Z-axis rotation angle (-90 to +90 degrees) - rotates strings clockwise/counter-clockwise
# Knob 5: Color mode (10 modes across 0-1 range):
#   0.0 = white
#   0.1 = rainbow (per-string hue)
#   0.2 = audio-reactive hue shift
#   0.3 = green
#   0.4 = red
#   0.5 = green to purple gradient
#   0.6 = white to black gradient
#   0.7 = light pink to light blue gradient
#   0.8 = warm cream to hot pink (#f5e6ad to #f13c77)
#   0.9+ = pastel trio (#f2f3e2 to #b2e5f8 to #f4b3ef)

import math
import random
import colorsys

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

# Screen dimensions
WIDTH = 1280
HEIGHT = 720

# String state
strings = []
frame_count = 0
phase_offsets = []  # Random phase offset per string for variety
audio_history = []  # Rolling buffer of audio frames for scrolling effect
AUDIO_HISTORY_SIZE = 64  # Number of audio frames to keep (one per string at max)
last_audio_update_frame = -1  # Track when we last updated history

def setup(screen, etc):
    """Initialize strings with random phase offsets"""
    global strings, phase_offsets, audio_history

    # We'll recalculate string positions each frame based on knob1
    # But we need persistent phase offsets for smooth animation
    max_strings = 64
    phase_offsets = [random.uniform(0, 2 * math.pi) for _ in range(max_strings)]

    # Initialize audio history with silence
    audio_history = []

def update_audio_history(etc, num_points):
    """
    Update the audio history buffer once per frame.
    Must be called at the start of each frame before get_audio_sample.
    """
    global audio_history, last_audio_update_frame

    # Only update once per frame
    if last_audio_update_frame == frame_count:
        return
    last_audio_update_frame = frame_count

    # Get current audio buffer
    audio_in = getattr(etc, 'audio_in', None)
    if audio_in is None or len(audio_in) == 0:
        return

    # Downsample audio to num_points samples
    step = max(1, len(audio_in) // num_points)
    current_frame = []
    for i in range(num_points):
        idx = i * step
        if idx < len(audio_in):
            sample = audio_in[idx]
            # Normalize to -1 to 1 range
            if isinstance(sample, (int, float)):
                # Audio comes in as signed values (roughly -32768 to 32767)
                normalized = sample / 32768.0
                current_frame.append(max(-1.0, min(1.0, normalized)))
            else:
                current_frame.append(0.0)
        else:
            current_frame.append(0.0)

    # Add to history (newest at the end)
    audio_history.append(current_frame)

    # Keep history at fixed size
    while len(audio_history) > AUDIO_HISTORY_SIZE:
        audio_history.pop(0)


def get_audio_sample(etc, string_index, num_strings, point_index, num_points):
    """
    Get audio sample for a specific string and point.
    Creates a scrolling oscilloscope effect where:
    - Each string shows audio from a different time offset (horizontal = time)
    - Each point along the string shows the waveform amplitude (vertical = frequency content)
    - String 0 (leftmost) = oldest audio, String N (rightmost) = newest audio

    Returns a value between -1 and 1.
    """
    global audio_history

    # Need enough history to show scrolling effect
    if len(audio_history) < 2:
        return 0.0

    # Map string index to a position in the audio history
    # String 0 = oldest audio (history[0]), String N-1 = newest audio (history[-1])
    # Use float mapping for smooth interpolation across history
    history_pos = (string_index / max(1, num_strings - 1)) * (len(audio_history) - 1)
    history_index = int(history_pos)
    history_index = max(0, min(history_index, len(audio_history) - 1))

    # Get the audio frame for this string
    audio_frame = audio_history[history_index]

    # Get the sample at this point along the string
    if point_index < len(audio_frame):
        return audio_frame[point_index]

    return 0.0

def smooth_points(points, iterations=1):
    """
    Apply simple smoothing to a list of (x, y) points.
    Uses a 3-point weighted average: 25% previous, 50% current, 25% next.
    Preserves endpoints to keep strings anchored.
    """
    if len(points) < 3:
        return points

    for _ in range(iterations):
        smoothed = [points[0]]  # Keep first point unchanged

        for i in range(1, len(points) - 1):
            prev_x, prev_y = points[i - 1]
            curr_x, curr_y = points[i]
            next_x, next_y = points[i + 1]

            # Weighted average: 25% prev, 50% current, 25% next
            new_x = prev_x * 0.25 + curr_x * 0.5 + next_x * 0.25
            new_y = prev_y * 0.25 + curr_y * 0.5 + next_y * 0.25

            smoothed.append((int(new_x), int(new_y)))

        smoothed.append(points[-1])  # Keep last point unchanged
        points = smoothed

    return points


def project_3d_to_2d(x, y, z, rotation_x, rotation_z, center_x, center_y):
    """
    Project a 3D point to 2D screen coordinates.
    Rotation is around X axis (tilts forward/backward) and Z axis (spins clockwise/counter-clockwise).
    Simple perspective projection.
    """
    # First rotate around Z axis (affects X and Y - spins in screen plane)
    cos_z = math.cos(rotation_z)
    sin_z = math.sin(rotation_z)

    rx1 = (x - center_x) * cos_z - (y - center_y) * sin_z
    ry1 = (x - center_x) * sin_z + (y - center_y) * cos_z
    rz1 = z

    # Then rotate around X axis (affects Y and Z - tilts forward/back)
    cos_x = math.cos(rotation_x)
    sin_x = math.sin(rotation_x)

    rx2 = rx1
    ry2 = ry1 * cos_x - rz1 * sin_x
    rz2 = ry1 * sin_x + rz1 * cos_x

    # Perspective projection
    # Distance from viewer (larger = further back)
    focal_length = 800
    perspective_scale = focal_length / (focal_length - rz2)

    # Apply perspective to X and Y
    final_x = center_x + rx2 * perspective_scale
    final_y = center_y + ry2 * perspective_scale

    return final_x, final_y

def draw(screen, etc):
    """Draw vibrating strings with 3D projection"""
    global frame_count

    # Initialize if needed
    if not phase_offsets:
        setup(screen, etc)

    # Clear screen to black
    screen.fill((0, 0, 0))

    # Get knob values from etc object (Eyesy hardware API)
    knob1 = etc.knob1
    knob2 = etc.knob2
    knob3 = etc.knob3
    knob4 = etc.knob4
    knob5 = etc.knob5

    # Knob 1: Number of strings (8 to 64)
    num_strings = int(8 + knob1 * 56)

    # Number of points per string (for audio sampling)
    num_points = 50

    # Update audio history once per frame (before sampling)
    update_audio_history(etc, num_points + 1)

    # Knob 2: Vibration amplitude (0 to 100 pixels max displacement)
    amplitude = knob2 * 100

    # Knob 3: X-axis rotation (-90 to +90 degrees) - tilts forward/back
    rotation_x = (knob3 - 0.5) * math.pi  # -pi/2 to +pi/2

    # Knob 4: Z-axis rotation (-90 to +90 degrees) - spins clockwise/counter-clockwise
    rotation_z = (knob4 - 0.5) * math.pi  # -pi/2 to +pi/2

    # Fixed vibration speed (could be tied to audio later)
    speed = 0.08

    # Knob 5: Color mode
    color_mode = knob5

    # Center of screen for rotation
    center_x = WIDTH / 2
    center_y = HEIGHT / 2

    # Calculate string spacing
    # Strings are evenly distributed across the width
    margin = 100
    available_width = WIDTH - 2 * margin
    string_spacing = available_width / (num_strings - 1) if num_strings > 1 else 0

    # Collect all string data first for proper draw ordering
    all_strings = []

    for i in range(num_strings):
        # Base X position (before rotation)
        base_x = margin + i * string_spacing

        # Get phase offset for this string
        phase = phase_offsets[i % len(phase_offsets)]

        # Determine color based on mode (10 modes)
        # Use string position for gradient modes (0 = first string, 1 = last string)
        string_t = i / max(1, num_strings - 1)

        if color_mode < 0.1:
            # White
            color = (255, 255, 255)
        elif color_mode < 0.2:
            # Rainbow - each string gets a different hue
            hue = i / num_strings
            r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
            color = (int(r * 255), int(g * 255), int(b * 255))
        elif color_mode < 0.3:
            # Audio-reactive hue (placeholder - shifts over time)
            hue = (frame_count * 0.01 + i * 0.1) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
            color = (int(r * 255), int(g * 255), int(b * 255))
        elif color_mode < 0.4:
            # Green
            color = (0, 255, 100)
        elif color_mode < 0.5:
            # Red
            color = (255, 50, 50)
        elif color_mode < 0.6:
            # Green to purple gradient
            green = (0, 255, 100)
            purple = (180, 0, 255)
            color = lerp_color(green, purple, string_t)
        elif color_mode < 0.7:
            # White to black gradient
            white = (255, 255, 255)
            black = (20, 20, 20)
            color = lerp_color(white, black, string_t)
        elif color_mode < 0.8:
            # Light pink to light blue gradient
            light_pink = (255, 182, 193)
            light_blue = (173, 216, 230)
            color = lerp_color(light_pink, light_blue, string_t)
        elif color_mode < 0.9:
            # Warm cream to hot pink (#f5e6ad to #f13c77)
            cream = (0xf5, 0xe6, 0xad)  # (245, 230, 173)
            hot_pink = (0xf1, 0x3c, 0x77)  # (241, 60, 119)
            color = lerp_color(cream, hot_pink, string_t)
        else:
            # Pastel trio: #f2f3e2 to #b2e5f8 to #f4b3ef
            pastel_cream = (0xf2, 0xf3, 0xe2)  # (242, 243, 226)
            pastel_blue = (0xb2, 0xe5, 0xf8)   # (178, 229, 248)
            pastel_pink = (0xf4, 0xb3, 0xef)   # (244, 179, 239)
            color = lerp_color_3(pastel_cream, pastel_blue, pastel_pink, string_t)

        # Draw string as a series of connected points
        # More points = smoother curve
        num_points = 50
        displaced_points = []  # Points at current z displacement
        rest_points = []       # Points at z=0 (resting position)
        avg_z = 0  # Track average z for depth sorting

        for j in range(num_points + 1):
            # Y position along the string (0 = top, 1 = bottom)
            t = j / num_points
            y = t * HEIGHT

            # Envelope: max displacement at center, zero at ends (like a plucked string)
            envelope = math.sin(t * math.pi)

            # Try to get audio sample for this string/point
            audio_sample = get_audio_sample(etc, i, num_strings, j, num_points + 1)

            # Check if we have audio history (meaning audio is playing)
            has_audio = len(audio_history) >= 2

            if has_audio:
                # Audio-reactive mode: use audio sample directly
                # The audio sample already represents the waveform
                displacement = amplitude * envelope * audio_sample
            else:
                # Fallback: sine wave animation when no audio
                wave_y = math.sin(t * math.pi)  # Fundamental
                wave_time = math.sin(frame_count * speed + phase)

                # Add second harmonic for more interesting motion
                wave_y2 = math.sin(t * math.pi * 2) * 0.3
                wave_time2 = math.sin(frame_count * speed * 1.5 + phase + 0.5)

                displacement = amplitude * envelope * (wave_y * wave_time + wave_y2 * wave_time2)

            # 3D coordinates for displaced position
            x_3d = base_x
            y_3d = y
            z_3d = displacement

            # Project displaced position to 2D
            x_2d, y_2d = project_3d_to_2d(x_3d, y_3d, z_3d, rotation_x, rotation_z, center_x, center_y)
            displaced_points.append((int(x_2d), int(y_2d)))

            # Project resting position (z=0) to 2D
            x_rest, y_rest = project_3d_to_2d(x_3d, y_3d, 0, rotation_x, rotation_z, center_x, center_y)
            rest_points.append((int(x_rest), int(y_rest)))

            # Accumulate z for sorting (use rotated z position)
            # After rotation, get the effective depth
            cos_z = math.cos(rotation_z)
            sin_z = math.sin(rotation_z)
            rx1 = (x_3d - center_x) * cos_z - (y_3d - center_y) * sin_z
            ry1 = (x_3d - center_x) * sin_z + (y_3d - center_y) * cos_z
            cos_x = math.cos(rotation_x)
            sin_x = math.sin(rotation_x)
            rz2 = ry1 * sin_x + z_3d * cos_x
            avg_z += rz2

        avg_z /= (num_points + 1)

        # Apply smoothing based on knob2 (0 = max smooth, 1 = no smooth)
        # At knob2=0: 4 iterations, at knob2=1: 0 iterations
        smooth_iterations = int((1.0 - etc.knob2) * 4)
        if smooth_iterations > 0:
            displaced_points = smooth_points(displaced_points, iterations=smooth_iterations)
            rest_points = smooth_points(rest_points, iterations=smooth_iterations)

        # Create fill color (darker version of main color)
        fill_color = (color[0] // 4, color[1] // 4, color[2] // 4)

        # Build polygon points
        polygon_points = displaced_points + rest_points[::-1] if len(displaced_points) >= 2 else []

        all_strings.append({
            'displaced_points': displaced_points,
            'polygon_points': polygon_points,
            'color': color,
            'fill_color': fill_color,
            'avg_z': avg_z,
            'base_x': base_x
        })

    # Sort strings by depth (back to front - lower z values first)
    all_strings.sort(key=lambda s: s['avg_z'])

    # Draw all fill polygons first (back to front)
    for string_data in all_strings:
        if string_data['polygon_points']:
            pygame.draw.polygon(screen, string_data['fill_color'], string_data['polygon_points'], 0)

    # Draw all string lines on top (back to front)
    for string_data in all_strings:
        displaced_points = string_data['displaced_points']
        color = string_data['color']
        for j in range(len(displaced_points) - 1):
            pygame.draw.line(screen, color, displaced_points[j], displaced_points[j + 1], 1)

    frame_count += 1
