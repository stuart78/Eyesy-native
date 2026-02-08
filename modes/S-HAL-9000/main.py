# HAL 9000 Display Mode
# Recreates the iconic computer displays from 2001: A Space Odyssey
#
# Knob 1: Display type (system status, circular graph, oscilloscope, etc.)
# Knob 2: Animation speed
# Knob 3: Color scheme (different HAL system colors)
# Knob 4: Graph complexity / detail level
# Knob 5: Audio reactivity (how much audio affects the display)

import pygame
import math
import random

# Screen dimensions
WIDTH = 1280
HEIGHT = 720

# HAL 9000 color schemes based on actual film displays
# Format: (background, primary, secondary, accent)
HAL_COLORS = [
    # COM - Communications (purple)
    ((40, 20, 60), (200, 150, 255), (150, 100, 200), (255, 200, 255)),
    # VEH/NAV - Vehicle/Navigation (dark blue)
    ((20, 30, 60), (100, 150, 255), (80, 120, 200), (150, 200, 255)),
    # ATM/LIF - Atmosphere/Life support (red)
    ((60, 20, 20), (255, 100, 100), (200, 80, 80), (255, 150, 150)),
    # CNT/HIB - Count/Hibernation (green)
    ((20, 40, 20), (100, 255, 100), (80, 200, 80), (150, 255, 150)),
    # DMG - Damage (bright red)
    ((80, 20, 20), (255, 50, 50), (200, 40, 40), (255, 100, 100)),
    # MEM - Memory (blue)
    ((20, 20, 50), (100, 100, 255), (80, 80, 200), (150, 150, 255)),
    # NUC - Nuclear (dark blue/cyan)
    ((20, 40, 50), (100, 200, 255), (80, 160, 200), (150, 220, 255)),
]

# System acronyms from the film
SYSTEM_CODES = [
    ("COM", "COMMUNICATIONS"),
    ("VEH", "VEHICLE STATUS"),
    ("NAV", "NAVIGATION"),
    ("GDE", "GUIDANCE"),
    ("CNT", "COUNTER"),
    ("NUC", "NUCLEAR"),
    ("ATM", "ATMOSPHERE"),
    ("HIB", "HIBERNATION"),
    ("DMG", "DAMAGE CONTROL"),
    ("LIF", "LIFE SUPPORT"),
    ("MEM", "MEMORY BANK"),
    ("FLX", "FLUX MONITOR"),
]

# Simple 5x7 bitmap font for HAL aesthetic
# Each character is a list of 7 rows, each row is 5 bits
FONT_5X7 = {
    'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'B': [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    'C': [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    'D': [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
    'E': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    'F': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    'G': [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110],
    'H': [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'I': [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    'J': [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    'K': [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    'L': [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    'M': [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    'N': [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    'O': [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'P': [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    'Q': [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
    'R': [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    'S': [0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
    'T': [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    'U': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'V': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    'W': [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    'X': [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    'Y': [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    'Z': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    '0': [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    '2': [0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
    '3': [0b01110, 0b10001, 0b00001, 0b00110, 0b00001, 0b10001, 0b01110],
    '4': [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    '6': [0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    '8': [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    '9': [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110],
    ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    ':': [0b00000, 0b00100, 0b00100, 0b00000, 0b00100, 0b00100, 0b00000],
    '-': [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
    '.': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b00100],
    '%': [0b11000, 0b11001, 0b00010, 0b00100, 0b01000, 0b10011, 0b00011],
    '+': [0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000],
}

# State variables
frame_count = 0
current_display = 0
graph_data = []
oscilloscope_history = []
circular_segments = []
last_trigger = False

# Display modes
DISPLAY_SYSTEM_STATUS = 0
DISPLAY_CIRCULAR_GRAPH = 1
DISPLAY_OSCILLOSCOPE = 2
DISPLAY_BAR_GRAPH = 3
DISPLAY_RADAR = 4
DISPLAY_SPIRAL = 5


def setup(screen, etc):
    """Initialize HAL display state"""
    global graph_data, oscilloscope_history, circular_segments

    # Initialize graph data with random values
    graph_data = [random.uniform(0.3, 0.9) for _ in range(16)]

    # Oscilloscope history buffer
    oscilloscope_history = [0.5] * 200

    # Circular graph segments
    circular_segments = [random.uniform(0.2, 1.0) for _ in range(12)]


def draw_char(screen, char, x, y, scale, color):
    """Draw a single character using bitmap font"""
    char = char.upper()
    if char not in FONT_5X7:
        return

    bitmap = FONT_5X7[char]
    pixel_size = scale

    for row_idx, row in enumerate(bitmap):
        for col in range(5):
            if row & (1 << (4 - col)):
                px = int(x + col * pixel_size)
                py = int(y + row_idx * pixel_size)
                pygame.draw.rect(screen, color, (px, py, pixel_size, pixel_size))


def draw_text(screen, text, x, y, scale, color):
    """Draw text string using bitmap font"""
    char_width = 6 * scale  # 5 pixels + 1 spacing
    for i, char in enumerate(text):
        draw_char(screen, char, x + i * char_width, y, scale, color)


def draw_text_centered(screen, text, cx, cy, scale, color):
    """Draw centered text"""
    char_width = 6 * scale
    total_width = len(text) * char_width
    char_height = 7 * scale
    x = cx - total_width // 2
    y = cy - char_height // 2
    draw_text(screen, text, x, y, scale, color)


def draw_system_status(screen, colors, code_idx, frame, detail):
    """Draw HAL system status screen with three-letter acronym"""
    bg, primary, secondary, accent = colors
    code, description = SYSTEM_CODES[code_idx % len(SYSTEM_CODES)]

    screen.fill(bg)

    # Draw subtle grid lines
    grid_color = (bg[0] + 20, bg[1] + 20, bg[2] + 20)
    for x in range(0, WIDTH, 80):
        pygame.draw.line(screen, grid_color, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 60):
        pygame.draw.line(screen, grid_color, (0, y), (WIDTH, y), 1)

    # Main three-letter code - centered below middle (large scale)
    code_y = HEIGHT // 2 + 20
    draw_text_centered(screen, code, WIDTH // 2, code_y, 16, primary)

    # Secondary identifier above
    secondary_y = HEIGHT // 2 - 80
    identifier = f"{code}: {random.randint(10,99)} - {random.randint(10,99)}"
    draw_text_centered(screen, identifier, WIDTH // 2, secondary_y, 3, secondary)

    # Description at top
    draw_text_centered(screen, description, WIDTH // 2, 50, 2, secondary)

    # Status indicators on sides
    num_indicators = int(4 + detail * 6)
    for i in range(num_indicators):
        # Left side indicators
        y = 120 + i * 50
        if y < HEIGHT - 100:
            # Blinking based on frame
            blink = math.sin(frame * 0.1 + i * 0.7) > 0
            ind_color = accent if blink else secondary
            pygame.draw.rect(screen, ind_color, (40, y, 10, 10))
            label = f"SYS {i+1:02d}"
            draw_text(screen, label, 60, y, 2, secondary)

            # Right side - values
            value = f"{random.randint(0, 999):03d}"
            draw_text(screen, value, WIDTH - 120, y, 2, primary)
            pygame.draw.rect(screen, secondary, (WIDTH - 50, y, 10, 10))

    # Bottom status bar
    pygame.draw.rect(screen, secondary, (100, HEIGHT - 50, WIDTH - 200, 2))
    status_text = "NOMINAL" if random.random() > 0.1 else "ACTIVE"
    draw_text_centered(screen, status_text, WIDTH // 2, HEIGHT - 30, 2, accent)


def draw_circular_graph(screen, colors, frame, detail, audio_level):
    """Draw circular/radial graph display"""
    global circular_segments

    bg, primary, secondary, accent = colors
    screen.fill(bg)

    center_x = WIDTH // 2
    center_y = HEIGHT // 2
    max_radius = min(WIDTH, HEIGHT) // 2 - 80

    # Number of concentric rings
    num_rings = int(3 + detail * 5)

    # Update segments based on audio
    for i in range(len(circular_segments)):
        target = 0.3 + audio_level * 0.7 + math.sin(frame * 0.02 + i * 0.5) * 0.2
        circular_segments[i] += (target - circular_segments[i]) * 0.1

    # Draw concentric rings
    for ring in range(num_rings):
        ring_radius = int(max_radius * (ring + 1) / num_rings)
        pygame.draw.circle(screen, secondary, (center_x, center_y), ring_radius, 1)

        # Segmented data on outer rings
        if ring >= num_rings // 2:
            num_segments = 12
            for seg in range(num_segments):
                angle = (seg / num_segments) * 2 * math.pi - math.pi / 2
                angle += frame * 0.005  # Slow rotation

                seg_value = circular_segments[seg % len(circular_segments)]
                inner_r = ring_radius - 20
                outer_r = ring_radius - 20 + seg_value * 40

                x1 = center_x + math.cos(angle) * inner_r
                y1 = center_y + math.sin(angle) * inner_r
                x2 = center_x + math.cos(angle) * outer_r
                y2 = center_y + math.sin(angle) * outer_r

                pygame.draw.line(screen, primary, (int(x1), int(y1)), (int(x2), int(y2)), 3)

    # Center element - pulsing
    pulse = 0.7 + 0.3 * math.sin(frame * 0.1)
    center_radius = int(30 * pulse + audio_level * 20)
    pygame.draw.circle(screen, accent, (center_x, center_y), center_radius, 2)
    pygame.draw.circle(screen, primary, (center_x, center_y), max(1, center_radius // 2))

    # Radial lines from center
    num_radials = int(8 + detail * 8)
    for i in range(num_radials):
        angle = (i / num_radials) * 2 * math.pi + frame * 0.01
        x = center_x + math.cos(angle) * max_radius
        y = center_y + math.sin(angle) * max_radius
        pygame.draw.line(screen, (bg[0]+30, bg[1]+30, bg[2]+30),
                        (center_x, center_y), (int(x), int(y)), 1)

    # Corner labels
    draw_text(screen, "RADIAL SCAN", 40, 40, 2, secondary)
    draw_text(screen, f"CYCLE: {frame % 1000:04d}", WIDTH - 180, 40, 2, secondary)


def draw_oscilloscope(screen, colors, frame, detail, audio_data, audio_level):
    """Draw oscilloscope waveform display"""
    global oscilloscope_history

    bg, primary, secondary, accent = colors
    screen.fill(bg)

    # Update history with new audio sample
    if audio_data and len(audio_data) > 0:
        sample_idx = int(len(audio_data) * 0.5)
        new_sample = audio_data[sample_idx] if sample_idx < len(audio_data) else 0
        new_sample = 0.5 + new_sample * 0.5
    else:
        new_sample = 0.5 + 0.3 * math.sin(frame * 0.2) + 0.1 * math.sin(frame * 0.7)

    oscilloscope_history.append(new_sample)
    if len(oscilloscope_history) > 200:
        oscilloscope_history.pop(0)

    # Draw grid
    margin = 80
    graph_width = WIDTH - margin * 2
    graph_height = HEIGHT - margin * 2

    # Horizontal grid lines
    for i in range(5):
        y = margin + (graph_height * i) // 4
        pygame.draw.line(screen, secondary, (margin, y), (WIDTH - margin, y), 1)

    # Vertical grid lines
    for i in range(9):
        x = margin + (graph_width * i) // 8
        pygame.draw.line(screen, secondary, (x, margin), (x, HEIGHT - margin), 1)

    # Draw waveform - draw line segments individually
    for i in range(len(oscilloscope_history) - 1):
        x1 = margin + (i / len(oscilloscope_history)) * graph_width
        y1 = margin + (1 - oscilloscope_history[i]) * graph_height
        x2 = margin + ((i + 1) / len(oscilloscope_history)) * graph_width
        y2 = margin + (1 - oscilloscope_history[i + 1]) * graph_height
        pygame.draw.line(screen, primary, (int(x1), int(y1)), (int(x2), int(y2)), 2)

    # Center line
    center_y = margin + graph_height // 2
    pygame.draw.line(screen, accent, (margin, center_y), (WIDTH - margin, center_y), 1)

    # Labels
    draw_text(screen, "AUDIO WAVEFORM", margin, 30, 2, secondary)
    draw_text(screen, f"LEVEL: {int(audio_level * 100):02d}%", WIDTH - 180, 30, 2, primary)

    # Scale markers
    draw_text(screen, "+1.0", 20, margin - 5, 1, secondary)
    draw_text(screen, " 0.0", 20, center_y - 5, 1, secondary)
    draw_text(screen, "-1.0", 20, HEIGHT - margin - 5, 1, secondary)


def draw_bar_graph(screen, colors, frame, detail, audio_level):
    """Draw vertical bar graph display"""
    global graph_data

    bg, primary, secondary, accent = colors
    screen.fill(bg)

    margin = 80
    num_bars = int(8 + detail * 12)
    bar_width = (WIDTH - margin * 2) // num_bars - 4
    max_height = HEIGHT - margin * 2

    # Update graph data
    for i in range(len(graph_data)):
        target = 0.2 + audio_level * 0.6 + random.uniform(-0.1, 0.1)
        target += 0.2 * math.sin(frame * 0.05 + i * 0.3)
        graph_data[i] += (target - graph_data[i]) * 0.15
        graph_data[i] = max(0.1, min(1.0, graph_data[i]))

    # Extend graph_data if needed
    while len(graph_data) < num_bars:
        graph_data.append(random.uniform(0.3, 0.8))

    # Draw bars
    for i in range(num_bars):
        x = margin + i * (bar_width + 4)
        height = int(graph_data[i % len(graph_data)] * max_height)
        y = HEIGHT - margin - height

        # Bar fill
        pygame.draw.rect(screen, primary, (x, y, bar_width, height))

        # Highlight at top
        pygame.draw.rect(screen, accent, (x, y, bar_width, min(4, height)))

        # Label
        if bar_width >= 20:
            label = f"{int(graph_data[i % len(graph_data)] * 100):02d}"
            draw_text(screen, label, x + 2, HEIGHT - margin + 10, 1, secondary)

    # Title and axes
    draw_text(screen, "SYSTEM METRICS", margin, 30, 2, secondary)
    pygame.draw.line(screen, secondary, (margin - 10, margin), (margin - 10, HEIGHT - margin), 1)
    pygame.draw.line(screen, secondary, (margin - 10, HEIGHT - margin), (WIDTH - margin, HEIGHT - margin), 1)


def draw_radar(screen, colors, frame, detail, audio_level):
    """Draw radar sweep display"""
    bg, primary, secondary, accent = colors
    screen.fill(bg)

    center_x = WIDTH // 2
    center_y = HEIGHT // 2
    max_radius = min(WIDTH, HEIGHT) // 2 - 60

    # Concentric circles
    num_rings = int(4 + detail * 4)
    for ring in range(1, num_rings + 1):
        radius = max_radius * ring // num_rings
        pygame.draw.circle(screen, secondary, (center_x, center_y), radius, 1)

    # Cross hairs
    pygame.draw.line(screen, secondary, (center_x - max_radius, center_y),
                    (center_x + max_radius, center_y), 1)
    pygame.draw.line(screen, secondary, (center_x, center_y - max_radius),
                    (center_x, center_y + max_radius), 1)

    # Sweep line
    sweep_angle = (frame * 0.03) % (2 * math.pi)
    sweep_x = center_x + math.cos(sweep_angle) * max_radius
    sweep_y = center_y + math.sin(sweep_angle) * max_radius
    pygame.draw.line(screen, accent, (center_x, center_y), (int(sweep_x), int(sweep_y)), 2)

    # Fade trail behind sweep
    for i in range(20):
        trail_angle = sweep_angle - (i * 0.03)
        fade = 1 - (i / 20)
        trail_color = (int(primary[0] * fade * 0.3),
                      int(primary[1] * fade * 0.3),
                      int(primary[2] * fade * 0.3))
        tx = center_x + math.cos(trail_angle) * max_radius
        ty = center_y + math.sin(trail_angle) * max_radius
        pygame.draw.line(screen, trail_color, (center_x, center_y), (int(tx), int(ty)), 1)

    # Blips (random targets)
    random.seed(42)
    num_blips = int(3 + detail * 8)
    for i in range(num_blips):
        blip_angle = random.uniform(0, 2 * math.pi)
        blip_dist = random.uniform(0.2, 0.9) * max_radius

        angle_diff = (sweep_angle - blip_angle) % (2 * math.pi)
        if angle_diff < 1.0:
            brightness = 1 - angle_diff
            blip_color = (int(accent[0] * brightness),
                         int(accent[1] * brightness),
                         int(accent[2] * brightness))
            bx = center_x + math.cos(blip_angle) * blip_dist
            by = center_y + math.sin(blip_angle) * blip_dist
            pygame.draw.circle(screen, blip_color, (int(bx), int(by)), 4)

    random.seed()

    # Labels
    draw_text(screen, "SCAN ACTIVE", 40, 40, 2, secondary)
    draw_text(screen, f"BEARING: {int(math.degrees(sweep_angle)) % 360:03d}", WIDTH - 200, 40, 2, primary)


def draw_spiral(screen, colors, frame, detail, audio_level):
    """Draw spiral visualization"""
    bg, primary, secondary, accent = colors
    screen.fill(bg)

    center_x = WIDTH // 2
    center_y = HEIGHT // 2

    # Number of spiral arms
    num_arms = int(2 + detail * 4)
    points_per_arm = int(50 + detail * 100)
    max_radius = min(WIDTH, HEIGHT) // 2 - 40

    for arm in range(num_arms):
        arm_offset = (arm / num_arms) * 2 * math.pi

        prev_x, prev_y = None, None
        for i in range(points_per_arm):
            t = i / points_per_arm
            angle = t * 4 * math.pi + arm_offset + frame * 0.02
            radius = t * max_radius * (0.8 + 0.2 * audio_level)

            # Add some waviness based on audio
            radius += math.sin(t * 20 + frame * 0.1) * 10 * audio_level

            x = int(center_x + math.cos(angle) * radius)
            y = int(center_y + math.sin(angle) * radius)

            if prev_x is not None:
                # Color gradient along spiral
                brightness = 0.3 + 0.7 * t
                color = (int(primary[0] * brightness),
                        int(primary[1] * brightness),
                        int(primary[2] * brightness))
                pygame.draw.line(screen, color, (prev_x, prev_y), (x, y), 2)

            prev_x, prev_y = x, y

    # Center dot
    pygame.draw.circle(screen, accent, (center_x, center_y), 8)

    # Labels
    draw_text(screen, "FLUX PATTERN", 40, 40, 2, secondary)


def draw(screen, etc):
    """Main draw function"""
    global frame_count, current_display, last_trigger

    # Get knob values
    # Knob 1: Display type (0-5 mapped to display modes)
    display_mode = int(etc.knob1 * 5.99)

    # Knob 2: Animation speed
    speed = 0.5 + etc.knob2 * 2.0

    # Knob 3: Color scheme
    color_idx = int(etc.knob3 * (len(HAL_COLORS) - 0.01))
    colors = HAL_COLORS[color_idx]

    # Knob 4: Detail level
    detail = etc.knob4

    # Knob 5: Audio reactivity
    audio_react = etc.knob5

    # Get audio data
    audio_data = getattr(etc, 'audio_in', None)
    audio_level = 0.0

    if audio_data and len(audio_data) > 0:
        try:
            audio_level = sum(abs(s) for s in audio_data) / len(audio_data)
            audio_level = min(1.0, audio_level * 3)
        except:
            audio_level = 0.0

    # Mix audio reactivity with knob setting
    audio_level = audio_level * audio_react

    # Check for trigger to switch displays
    trigger = getattr(etc, 'audio_trig', False) or getattr(etc, 'trig', False)
    if trigger and not last_trigger:
        current_display = (current_display + 1) % 6
    last_trigger = trigger

    # Adjusted frame for speed control
    adjusted_frame = int(frame_count * speed)

    # Draw selected display mode
    if display_mode == DISPLAY_SYSTEM_STATUS:
        draw_system_status(screen, colors, current_display, adjusted_frame, detail)
    elif display_mode == DISPLAY_CIRCULAR_GRAPH:
        draw_circular_graph(screen, colors, adjusted_frame, detail, audio_level)
    elif display_mode == DISPLAY_OSCILLOSCOPE:
        draw_oscilloscope(screen, colors, adjusted_frame, detail, audio_data, audio_level)
    elif display_mode == DISPLAY_BAR_GRAPH:
        draw_bar_graph(screen, colors, adjusted_frame, detail, audio_level)
    elif display_mode == DISPLAY_RADAR:
        draw_radar(screen, colors, adjusted_frame, detail, audio_level)
    elif display_mode == DISPLAY_SPIRAL:
        draw_spiral(screen, colors, adjusted_frame, detail, audio_level)

    frame_count += 1
