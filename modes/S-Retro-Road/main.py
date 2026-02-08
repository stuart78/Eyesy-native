# Retro Road Mode
# Inspired by the "Dare to be Stupid" video by Weird Al
# Road on a tiny planet with buildings radiating outward like bowling pins
#
# Knob 1: Speed (how fast we're driving)
# Knob 2: Building density
# Knob 3: Color palette
# Knob 4: Building height variation
# Knob 5: Background color
#
# Audio Reactivity:
# - Buildings pulse on beats
# - Speed increases with audio level

import pygame
import math
import random

# Screen dimensions
WIDTH = 1280
HEIGHT = 720

# Animation state
frame_count = 0
road_offset = 0.0

# Road is an egg shape - like we're on top of a small planet
ROAD_CENTER_X = WIDTH // 2
ROAD_CENTER_Y = HEIGHT + 30  # Center of the "egg" is below screen
# Road surface should span 85% of screen width at the base
# Road width = egg_width * road_half_width_ratio * 2 (where ratio = 0.4)
# So: ROAD_RADIUS_X * 0.4 * 2 = WIDTH * 0.85  =>  ROAD_RADIUS_X = WIDTH * 0.85 / 0.8
ROAD_RADIUS_X = int(WIDTH * 0.85 / 0.8)  # = 1360, so road surface spans 85% of screen
ROAD_RADIUS_Y = 480  # Vertical radius (height of egg)

# Where the road surface starts (top of visible egg)
HORIZON_Y = ROAD_CENTER_Y - ROAD_RADIUS_Y

# Buildings queue
buildings = []
MAX_BUILDINGS = 50


def setup(screen, etc):
    """Initialize the mode."""
    global buildings
    if len(buildings) == 0:
        init_buildings()


def init_buildings():
    """Create initial set of buildings."""
    global buildings
    buildings = []
    random.seed(12345)

    for i in range(MAX_BUILDINGS):
        # Angle on the egg (0 = top/horizon, pi/2 = bottom)
        angle = (i / MAX_BUILDINGS) * (math.pi / 2)
        add_building(angle)


def add_building(angle):
    """Add a building at the given angle on the egg surface."""
    global buildings

    side = random.choice(['left', 'right'])
    lane = random.randint(0, 2)

    buildings.append({
        'angle': angle,  # 0 = horizon, pi/2 = closest
        'side': side,
        'lane': lane,
        'width': random.uniform(0.7, 1.4),
        'height': random.uniform(0.5, 1.5),
        'color_idx': random.randint(0, 7),
        'style': random.randint(0, 4),
        'wiggle_phase': random.uniform(0, 2 * math.pi),  # Unique phase for each building
        'wiggle_freq': random.uniform(0.8, 1.2),  # Slight frequency variation
    })


def get_palette_color(idx, palette_type, brightness=1.0):
    """Get a color from the current palette."""
    palette_type = int(palette_type * 6) % 6

    if palette_type == 0:
        colors = [
            (255, 0, 128), (0, 255, 255), (255, 255, 0), (128, 0, 255),
            (0, 255, 128), (255, 128, 0), (0, 128, 255), (255, 0, 255),
        ]
    elif palette_type == 1:
        colors = [
            (255, 182, 193), (176, 224, 230), (255, 255, 186), (221, 160, 221),
            (176, 226, 176), (255, 218, 185), (173, 216, 230), (255, 192, 203),
        ]
    elif palette_type == 2:
        colors = [
            (255, 0, 0), (0, 0, 255), (255, 255, 0), (0, 255, 0),
            (255, 128, 0), (128, 0, 128), (0, 200, 200), (255, 255, 255),
        ]
    elif palette_type == 3:
        colors = [
            (255, 0, 128), (128, 0, 255), (64, 0, 128), (255, 0, 255),
            (200, 0, 150), (100, 0, 200), (255, 64, 128), (150, 0, 255),
        ]
    elif palette_type == 4:
        colors = [
            (0, 128, 255), (0, 255, 200), (0, 200, 128), (64, 128, 255),
            (0, 255, 255), (100, 200, 255), (0, 180, 180), (128, 255, 200),
        ]
    else:
        colors = [
            (255, 100, 50), (255, 200, 0), (255, 50, 50), (255, 150, 0),
            (200, 50, 50), (255, 220, 100), (255, 80, 80), (200, 100, 0),
        ]

    color = colors[idx % len(colors)]
    return tuple(min(255, int(c * brightness)) for c in color)


def get_bg_color(knob_value):
    """Get background color based on knob value."""
    t = knob_value
    if t < 0.2:
        return (0, 0, 0)
    elif t < 0.4:
        return (10, 10, 40)
    elif t < 0.6:
        return (30, 10, 40)
    elif t < 0.8:
        return (10, 30, 35)
    else:
        return (35, 10, 15)


def angle_to_position(angle, lateral_offset=0):
    """Convert angle on egg surface to screen position.

    angle: 0 = top of egg (horizon), pi/2 = bottom (closest to viewer)
    lateral_offset: how far left/right from center (in pixels at that depth)

    Returns (x, y, scale) where scale is for sizing objects.
    """
    # Y position on the egg surface
    y = ROAD_CENTER_Y - ROAD_RADIUS_Y * math.cos(angle)

    # Width of egg at this y position
    # As angle increases (going down), the egg gets wider then narrows
    width_at_y = ROAD_RADIUS_X * math.sin(angle)

    # Scale based on how "close" this point is
    # At angle 0 (horizon), scale is small
    # At angle pi/2 (bottom), scale is large
    scale = 0.1 + math.sin(angle) * 2.0

    # X position with lateral offset scaled by width at this depth
    x = ROAD_CENTER_X + lateral_offset * (width_at_y / ROAD_RADIUS_X)

    return x, y, scale, width_at_y


def draw_road_surface(screen):
    """Draw the egg-shaped road surface (below buildings)."""
    road_color = (25, 25, 25)
    edge_color = (80, 80, 80)

    num_segments = 50
    road_half_width_ratio = 0.4  # Road takes up 40% of egg width on each side

    # Build road edge points along the egg
    points_left = []
    points_right = []

    for i in range(num_segments + 1):
        angle = (i / num_segments) * (math.pi / 2)  # 0 to pi/2

        x_center, y, scale, egg_width = angle_to_position(angle, 0)

        # Road width is proportional to egg width at this point
        road_half_width = egg_width * road_half_width_ratio

        left_x = ROAD_CENTER_X - road_half_width
        right_x = ROAD_CENTER_X + road_half_width

        points_left.append((int(left_x), int(y)))
        points_right.append((int(right_x), int(y)))

    # Draw road surface (egg shaped)
    road_points = points_left + points_right[::-1]
    if len(road_points) >= 3:
        pygame.draw.polygon(screen, road_color, road_points)

    # Draw road edges
    for i in range(len(points_left) - 1):
        angle = (i / num_segments) * (math.pi / 2)
        thickness = max(1, int(1 + math.sin(angle) * 6))
        pygame.draw.line(screen, edge_color, points_left[i], points_left[i + 1], thickness)
        pygame.draw.line(screen, edge_color, points_right[i], points_right[i + 1], thickness)


def draw_median_strips(screen, offset):
    """Draw the center median strips (above buildings) - chunky dashes on the sphere."""
    line_color = (255, 255, 255)

    # Fewer, chunkier dashes that feel like they're on the sphere
    num_dashes = 6  # Fewer dashes for chunkier look
    dash_spacing = (math.pi / 2) / num_dashes  # Spacing between dashes in angle
    dash_length_ratio = 0.5  # Dash takes up 50% of its slot, 50% is gap

    for d in range(num_dashes * 3):  # Extra dashes for seamless looping
        # Each dash has a position that moves with the offset
        # offset increases over time, so ADD it to move dashes toward viewer (increasing angle)
        dash_angle = (d * dash_spacing + offset) % (math.pi / 2 + dash_spacing * 3)

        # Skip if not in visible range
        if dash_angle < 0 or dash_angle > math.pi / 2:
            continue

        # Get position and scale for this dash
        _, y, scale, _ = angle_to_position(dash_angle, 0)

        # Dash dimensions grow with scale (just like buildings) - chunkier
        # Use squared scale for more dramatic size increase as they approach
        size_factor = scale * scale * 0.5 + scale * 0.5  # Emphasize perspective
        dash_height = 40 * size_factor * dash_length_ratio
        dash_width = max(4, int(12 * size_factor))  # Wider dashes

        # Draw dash as a rectangle (centered at y position)
        dash_top = y - dash_height / 2
        dash_bottom = y + dash_height / 2

        pygame.draw.line(screen, line_color,
                        (ROAD_CENTER_X, int(dash_top)),
                        (ROAD_CENTER_X, int(dash_bottom)),
                        dash_width)


def draw_building(screen, building, palette, audio_level):
    """Draw a single building with perspective on the egg surface."""
    angle = building['angle']
    side = building['side']
    lane = building['lane']

    # Get position on egg surface
    _, base_y, scale, egg_width = angle_to_position(angle, 0)

    # Don't draw if off screen
    if base_y < HORIZON_Y - 50 or base_y > HEIGHT + 100:
        return

    # Building dimensions
    bld_width = building['width'] * 60 * scale
    bld_height = building['height'] * 100 * scale

    # Audio-reactive wiggle - buildings dance to the sound
    wiggle_phase = building.get('wiggle_phase', 0)
    wiggle_freq = building.get('wiggle_freq', 1.0)
    # Wiggle amount increases with audio level and building proximity (scale)
    wiggle_time = frame_count * 0.15 * wiggle_freq + wiggle_phase
    wiggle_amount = math.sin(wiggle_time) * audio_level * 12 * scale

    # Road width at this depth
    road_half_width = egg_width * 0.35

    # Position building outside the road
    gap = 8 * scale
    lane_width = 40 * scale
    lane_offset = lane * lane_width

    if side == 'left':
        bld_right = ROAD_CENTER_X - road_half_width - gap - lane_offset + wiggle_amount
        bld_left = bld_right - bld_width
    else:
        bld_left = ROAD_CENTER_X + road_half_width + gap + lane_offset + wiggle_amount
        bld_right = bld_left + bld_width

    top_y = base_y - bld_height

    # Skip if building hasn't crested the horizon
    if top_y > base_y or base_y < HORIZON_Y:
        return

    # Fisheye lean - buildings lean outward, more so as they get closer
    lean_amount = math.sin(angle) * bld_height * 0.4
    if side == 'left':
        lean_amount = -lean_amount

    # Perspective squeeze
    squeeze = 0.65 + (1 - math.sin(angle)) * 0.25

    top_center = (bld_left + bld_right) / 2 + lean_amount
    top_half_width = bld_width * squeeze / 2

    top_left = top_center - top_half_width
    top_right = top_center + top_half_width

    # Colors
    brightness = 0.8 + audio_level * 0.4
    color = get_palette_color(building['color_idx'], palette, brightness)
    dark_color = tuple(max(0, int(c * 0.5)) for c in color)
    darker_color = tuple(max(0, int(c * 0.3)) for c in color)

    # Front face
    front_points = [
        (int(bld_left), int(base_y)),
        (int(top_left), int(top_y)),
        (int(top_right), int(top_y)),
        (int(bld_right), int(base_y))
    ]

    # Side face
    side_depth = 15 * scale
    if side == 'left':
        side_points = [
            (int(bld_left), int(base_y)),
            (int(top_left), int(top_y)),
            (int(top_left - side_depth), int(top_y - side_depth * 0.3)),
            (int(bld_left - side_depth), int(base_y - side_depth * 0.2))
        ]
        top_points = [
            (int(top_left), int(top_y)),
            (int(top_right), int(top_y)),
            (int(top_right - side_depth * 0.3), int(top_y - side_depth * 0.4)),
            (int(top_left - side_depth), int(top_y - side_depth * 0.3))
        ]
    else:
        side_points = [
            (int(bld_right), int(base_y)),
            (int(top_right), int(top_y)),
            (int(top_right + side_depth), int(top_y - side_depth * 0.3)),
            (int(bld_right + side_depth), int(base_y - side_depth * 0.2))
        ]
        top_points = [
            (int(top_left), int(top_y)),
            (int(top_right), int(top_y)),
            (int(top_right + side_depth), int(top_y - side_depth * 0.3)),
            (int(top_left + side_depth * 0.3), int(top_y - side_depth * 0.4))
        ]

    # Draw faces
    pygame.draw.polygon(screen, dark_color, side_points)
    pygame.draw.polygon(screen, (0, 0, 0), side_points, 1)

    pygame.draw.polygon(screen, color, front_points)
    pygame.draw.polygon(screen, (0, 0, 0), front_points, 1)

    pygame.draw.polygon(screen, darker_color, top_points)
    pygame.draw.polygon(screen, (0, 0, 0), top_points, 1)

    # Windows
    if bld_width > 20 and bld_height > 30:
        draw_windows(screen, front_points, building['style'])


def draw_windows(screen, front_points, style):
    """Draw windows on building front face."""
    xs = [p[0] for p in front_points]
    ys = [p[1] for p in front_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y

    if width < 12 or height < 18:
        return

    window_color = (255, 255, 180)
    dark_window = (30, 30, 50)
    margin = 0.15

    if style == 0:
        cols = max(1, int(width / 16))
        rows = max(1, int(height / 20))
        win_w = width * (1 - margin * 2) / cols * 0.5
        win_h = height * (1 - margin * 2) / rows * 0.4
        for row in range(rows):
            for col in range(cols):
                wx = min_x + width * margin + col * (width * (1 - margin * 2)) / cols
                wy = min_y + height * margin + row * (height * (1 - margin * 2)) / rows
                c = dark_window if (row + col + frame_count // 30) % 3 == 0 else window_color
                pygame.draw.rect(screen, c, (int(wx), int(wy), int(win_w), int(win_h)))
    elif style == 1:
        bands = max(1, int(height / 22))
        for b in range(bands):
            by = min_y + height * margin + b * (height * (1 - margin * 2)) / bands
            bh = (height * (1 - margin * 2)) / bands * 0.4
            pygame.draw.rect(screen, window_color,
                           (int(min_x + width * margin), int(by),
                            int(width * (1 - margin * 2)), int(bh)))
    elif style == 2:
        pygame.draw.rect(screen, window_color,
                        (int(min_x + width * 0.2), int(min_y + height * 0.15),
                         int(width * 0.6), int(height * 0.5)))
    elif style == 3:
        stripes = max(1, int(width / 10))
        for s in range(stripes):
            if s % 2 == 0:
                sx = min_x + width * margin + s * (width * (1 - margin * 2)) / stripes
                sw = (width * (1 - margin * 2)) / stripes * 0.6
                pygame.draw.rect(screen, window_color,
                               (int(sx), int(min_y + height * 0.1),
                                int(sw), int(height * 0.7)))
    else:
        random.seed(int(min_x * 100 + min_y))
        for _ in range(4):
            wx = min_x + width * (0.15 + random.random() * 0.6)
            wy = min_y + height * (0.15 + random.random() * 0.5)
            ws = 3 + random.random() * 6
            pygame.draw.rect(screen, window_color, (int(wx), int(wy), int(ws), int(ws)))


def draw(screen, etc):
    """Main draw function."""
    global frame_count, road_offset, buildings

    setup(screen, etc)

    # Get knob values
    speed = etc.knob1
    density = etc.knob2
    palette = etc.knob3
    height_var = etc.knob4
    bg_color_knob = etc.knob5

    # Audio level
    audio_data = getattr(etc, 'audio_in', None)
    audio_level = 0.0
    if audio_data and len(audio_data) > 0:
        total = sum(abs(s) for s in audio_data)
        audio_level = min(1.0, total / len(audio_data) / 32768.0 * 3)

    # Clear screen
    screen.fill(get_bg_color(bg_color_knob))

    # Update animation - building speed is the master speed
    building_speed = 0.008 + speed * 0.025 + audio_level * 0.012

    # Road offset accumulates at the same rate as buildings move
    road_offset += building_speed

    # Move buildings along the egg surface (increasing angle = coming toward us)
    for building in buildings:
        building['angle'] += building_speed

        # Reset buildings that pass the viewer
        if building['angle'] > math.pi / 2 + 0.1:
            building['angle'] = -0.05
            building['side'] = random.choice(['left', 'right'])
            building['lane'] = random.randint(0, 2)
            building['width'] = random.uniform(0.7, 1.4)
            building['height'] = random.uniform(0.4 + height_var * 0.4, 0.9 + height_var * 0.9)
            building['color_idx'] = random.randint(0, 7)
            building['style'] = random.randint(0, 4)
            building['wiggle_phase'] = random.uniform(0, 2 * math.pi)
            building['wiggle_freq'] = random.uniform(0.8, 1.2)

    # Sort by angle (far first)
    buildings.sort(key=lambda b: b['angle'])

    # Layer 1: Buildings (bottom layer, far to near)
    for building in buildings:
        if building['angle'] > 0:
            draw_building(screen, building, palette, audio_level)

    # Layer 2: Road surface (middle layer, on top of buildings)
    draw_road_surface(screen)

    # Layer 3: Median strips (top layer)
    draw_median_strips(screen, road_offset)

    frame_count += 1
