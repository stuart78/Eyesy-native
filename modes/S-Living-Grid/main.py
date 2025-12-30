# Living Grid Mode
# A grid of cells, each containing either a square or circle
# Knob 1 controls grid density (16x9 to 80x45)
# Knob 2 controls animation speed (0 = stopped, 1 = fast)
# Knob 3 controls background color (0 = black, 1 = white)
# Knob 4 controls foreground color (0 = white, 1 = black) - greyscale mode only
# Knob 5 controls color mode (0 = greyscale, 0.33 = rainbow, 0.66 = synthwave, 1 = metashape)
# Features "meta-shapes" - concentric ring patterns that create sparse areas

import random
import math
import colorsys

# Store the grid state at max resolution (80x45)
# Each cell stores (shape_type, size_factor) where:
#   shape_type: 0 = square, 1 = circle
#   size_factor: 0.0 to 1.0 (scaled based on cell size)
grid = None
meta_shapes = []  # List of organic meta-shapes
# Each meta-shape is a dict with:
#   'cells': dict mapping (row, col) -> distance from seed (0 = seed, 1 = first ring, etc.)
#   'center_row', 'center_col': approximate center for movement
#   'target_row', 'target_col': target position to move toward
#   'max_dist': maximum distance from seed cells
#   'hue': random hue for this meta-shape (0.0 to 1.0)
#   'shape_type': 'blob', 'tendril', 'amoeba', or 'star'

waves = []  # List of [position, length, direction, axis]
# position: current row or col position
# length: 1-4 cells in the wave
# direction: 1 or -1 (moving positive or negative)
# axis: 'x' (horizontal, moves along columns) or 'y' (vertical, moves along rows)
frame_count = 0

def create_organic_meta_shape(max_rows, max_cols, shape_type=None):
    """
    Create an organic meta-shape by growing outward from random seed cells.
    Returns a dict with cell distances and center position.

    Shape types:
    - 'blob': Uniform organic growth (roughly circular)
    - 'tendril': Narrow branching paths
    - 'amoeba': Multiple lobes extending outward
    - 'star': Preferential growth along cardinal/diagonal directions
    """
    if shape_type is None:
        shape_type = random.choice(['blob', 'tendril', 'amoeba', 'star'])

    # Pick a center region
    center_row = random.randint(10, max_rows - 11)
    center_col = random.randint(12, max_cols - 13)

    cells = {}  # (row, col) -> distance from nearest seed

    if shape_type == 'blob':
        # Original organic blob - uniform growth with random edges
        num_seeds = random.randint(2, 5)
        for _ in range(num_seeds):
            seed_row = center_row + random.randint(-2, 2)
            seed_col = center_col + random.randint(-2, 2)
            seed_row = max(2, min(max_rows - 3, seed_row))
            seed_col = max(2, min(max_cols - 3, seed_col))
            cells[(seed_row, seed_col)] = 0

        max_rings = random.randint(5, 9)
        for ring in range(1, max_rings + 1):
            prev_ring_cells = [(r, c) for (r, c), d in cells.items() if d == ring - 1]
            for r, c in prev_ring_cells:
                neighbors = [
                    (r-1, c), (r+1, c), (r, c-1), (r, c+1),
                    (r-1, c-1), (r-1, c+1), (r+1, c-1), (r+1, c+1)
                ]
                for nr, nc in neighbors:
                    if (nr, nc) not in cells:
                        if 0 <= nr < max_rows and 0 <= nc < max_cols:
                            if random.random() < 0.7:
                                cells[(nr, nc)] = ring

    elif shape_type == 'tendril':
        # Narrow branching paths - start with one seed, grow in limited directions
        cells[(center_row, center_col)] = 0
        max_rings = random.randint(8, 14)

        # Each active tip has a preferred direction
        active_tips = [(center_row, center_col, random.uniform(0, 2 * math.pi))]

        for ring in range(1, max_rings + 1):
            new_tips = []
            for r, c, angle in active_tips:
                # Primary growth direction based on angle
                dr = round(math.sin(angle))
                dc = round(math.cos(angle))

                # Try to grow in primary direction
                nr, nc = r + dr, c + dc
                if (nr, nc) not in cells and 0 <= nr < max_rows and 0 <= nc < max_cols:
                    cells[(nr, nc)] = ring
                    # Slightly vary the angle for organic feel
                    new_angle = angle + random.uniform(-0.3, 0.3)
                    new_tips.append((nr, nc, new_angle))

                    # Chance to branch
                    if random.random() < 0.15:
                        branch_angle = angle + random.choice([-math.pi/3, math.pi/3])
                        new_tips.append((nr, nc, branch_angle))

            active_tips = new_tips
            if not active_tips:
                break

    elif shape_type == 'amoeba':
        # Multiple lobes extending outward from center
        cells[(center_row, center_col)] = 0
        num_lobes = random.randint(3, 6)
        lobe_angles = [i * 2 * math.pi / num_lobes + random.uniform(-0.3, 0.3)
                       for i in range(num_lobes)]
        lobe_lengths = [random.randint(5, 10) for _ in range(num_lobes)]

        max_rings = max(lobe_lengths)

        for ring in range(1, max_rings + 1):
            prev_ring_cells = [(r, c) for (r, c), d in cells.items() if d == ring - 1]

            for r, c in prev_ring_cells:
                # Calculate angle from center
                dr = r - center_row
                dc = c - center_col
                cell_angle = math.atan2(dr, dc)

                # Check if this cell is within any lobe's angular range
                in_lobe = False
                lobe_idx = -1
                for i, lobe_angle in enumerate(lobe_angles):
                    angle_diff = abs((cell_angle - lobe_angle + math.pi) % (2 * math.pi) - math.pi)
                    if angle_diff < 0.6:  # ~35 degree cone per lobe
                        in_lobe = True
                        lobe_idx = i
                        break

                if in_lobe and ring <= lobe_lengths[lobe_idx]:
                    # Grow more aggressively in lobe direction
                    neighbors = [
                        (r-1, c), (r+1, c), (r, c-1), (r, c+1),
                        (r-1, c-1), (r-1, c+1), (r+1, c-1), (r+1, c+1)
                    ]
                    for nr, nc in neighbors:
                        if (nr, nc) not in cells:
                            if 0 <= nr < max_rows and 0 <= nc < max_cols:
                                if random.random() < 0.8:
                                    cells[(nr, nc)] = ring
                elif ring <= 2:
                    # Core area grows normally
                    neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
                    for nr, nc in neighbors:
                        if (nr, nc) not in cells:
                            if 0 <= nr < max_rows and 0 <= nc < max_cols:
                                if random.random() < 0.7:
                                    cells[(nr, nc)] = ring

    elif shape_type == 'star':
        # Preferential growth along cardinal and diagonal directions
        cells[(center_row, center_col)] = 0
        num_points = random.choice([4, 5, 6, 8])
        point_angles = [i * 2 * math.pi / num_points for i in range(num_points)]
        # Rotate randomly
        rotation = random.uniform(0, 2 * math.pi / num_points)
        point_angles = [(a + rotation) for a in point_angles]

        max_rings = random.randint(6, 10)

        for ring in range(1, max_rings + 1):
            prev_ring_cells = [(r, c) for (r, c), d in cells.items() if d == ring - 1]

            for r, c in prev_ring_cells:
                dr = r - center_row
                dc = c - center_col
                cell_angle = math.atan2(dr, dc)

                # Check if aligned with a star point
                aligned = False
                for point_angle in point_angles:
                    angle_diff = abs((cell_angle - point_angle + math.pi) % (2 * math.pi) - math.pi)
                    if angle_diff < 0.4:  # ~23 degree tolerance
                        aligned = True
                        break

                neighbors = [
                    (r-1, c), (r+1, c), (r, c-1), (r, c+1),
                    (r-1, c-1), (r-1, c+1), (r+1, c-1), (r+1, c+1)
                ]

                for nr, nc in neighbors:
                    if (nr, nc) not in cells:
                        if 0 <= nr < max_rows and 0 <= nc < max_cols:
                            # Higher probability along star points
                            prob = 0.85 if aligned else 0.25
                            # Also allow some growth in inner rings
                            if ring <= 2:
                                prob = max(prob, 0.5)
                            if random.random() < prob:
                                cells[(nr, nc)] = ring

    # Calculate actual max distance in the shape
    max_dist = max(cells.values()) if cells else 1

    return {
        'cells': cells,
        'center_row': center_row,
        'center_col': center_col,
        'target_row': center_row,
        'target_col': center_col,
        'max_dist': max_dist,
        'hue': random.random(),
        'shape_type': shape_type
    }

def setup(screen, etc):
    """Setup function called once when mode loads"""
    global grid, meta_shapes, waves

    # Max grid dimensions
    max_cols = 80
    max_rows = 45

    # Generate organic meta-shapes (one of each type for variety)
    meta_shapes = []
    for shape_type in ['blob', 'tendril', 'amoeba', 'star']:
        meta_shape = create_organic_meta_shape(max_rows, max_cols, shape_type)
        meta_shapes.append(meta_shape)
        print(f"Created meta-shape: {shape_type} with {len(meta_shape['cells'])} cells")

    # Generate fewer waves
    num_waves = random.randint(1, 3)
    waves = []
    for _ in range(num_waves):
        axis = random.choice(['x', 'y'])
        if axis == 'x':
            # Horizontal wave - moves along columns, spans rows
            position = random.randint(0, max_cols - 1)
            row_start = random.randint(0, max_rows - 4)
        else:
            # Vertical wave - moves along rows, spans columns
            position = random.randint(0, max_rows - 1)
            col_start = random.randint(0, max_cols - 4)

        length = random.randint(2, 4)
        direction = random.choice([-1, 1])
        # Store: [position, length, direction, axis, span_start]
        # span_start is where the wave starts on the perpendicular axis
        span_start = row_start if axis == 'x' else col_start
        waves.append([position, length, direction, axis, span_start])

    # Initialize grid with random shapes and size factors
    # Circles can only appear at positions where both row and col are multiples of 4
    grid = []
    for row in range(max_rows):
        grid_row = []
        for col in range(max_cols):
            # Check if this cell is part of a meta-shape
            size_factor = get_meta_shape_size(row, col)

            # If not part of a meta-shape, use a common default size
            if size_factor is None:
                size_factor = 0.5

            # Check if this cell can be a circle (multiples of 4)
            if row % 4 == 0 and col % 4 == 0:
                # Randomly choose square or circle
                shape_type = random.randint(0, 1)
            else:
                # Must be a square
                shape_type = 0

            grid_row.append((shape_type, size_factor))
        grid.append(grid_row)

def get_meta_shape_size(row, col):
    """
    Check if a cell is part of an organic meta-shape or wave and return its size factor.
    Organic shapes have smallest sizes at seed cells, growing larger outward.
    Returns None if not part of any meta-shape or wave.
    """
    global meta_shapes, waves

    # Check organic meta-shapes
    for meta in meta_shapes:
        cells = meta['cells']
        max_dist = meta['max_dist']

        if (row, col) in cells:
            distance = cells[(row, col)]
            # Normalize distance to 0-1 range
            normalized_dist = distance / max_dist if max_dist > 0 else 0

            # Sparse effect: center (seeds) are smallest, outer rings are larger
            min_size = 0.05
            max_size = 0.5
            size_factor = min_size + normalized_dist * (max_size - min_size)
            return size_factor

    # Check waves
    for wave in waves:
        position, length, direction, axis, span_start = wave[0], wave[1], wave[2], wave[3], wave[4]

        if axis == 'x':
            # Horizontal wave - check if cell is in the wave's column range
            # Wave spans from position (front) back by length cells
            wave_start = position - (length - 1) * direction
            wave_end = position

            # Ensure start <= end for range check
            if wave_start > wave_end:
                wave_start, wave_end = wave_end, wave_start

            # Check if cell is in wave's column range and row span
            if wave_start <= col <= wave_end and span_start <= row < span_start + 4:
                # Calculate position in wave (0 = front, 1 = tail)
                if direction == 1:
                    wave_pos = (position - col) / max(1, length - 1) if length > 1 else 0
                else:
                    wave_pos = (col - position) / max(1, length - 1) if length > 1 else 0
                wave_pos = max(0, min(1, wave_pos))
                # Front is large (1.0), tail is small (0.15)
                size_factor = 1.0 - wave_pos * 0.85
                return size_factor

        else:  # axis == 'y'
            # Vertical wave - check if cell is in the wave's row range
            wave_start = position - (length - 1) * direction
            wave_end = position

            if wave_start > wave_end:
                wave_start, wave_end = wave_end, wave_start

            # Check if cell is in wave's row range and column span
            if wave_start <= row <= wave_end and span_start <= col < span_start + 4:
                # Calculate position in wave (0 = front, 1 = tail)
                if direction == 1:
                    wave_pos = (position - row) / max(1, length - 1) if length > 1 else 0
                else:
                    wave_pos = (row - position) / max(1, length - 1) if length > 1 else 0
                wave_pos = max(0, min(1, wave_pos))
                # Front is large (1.0), tail is small (0.15)
                size_factor = 1.0 - wave_pos * 0.85
                return size_factor

    return None

def update_meta_shapes():
    """
    Animate organic meta-shapes by:
    1. Moving toward target position
    2. Morphing shape by growing/shrinking edges
    3. Occasionally adding new lobes or retracting existing ones
    """
    global meta_shapes

    max_cols = 80
    max_rows = 45

    for meta in meta_shapes:
        center_row = meta['center_row']
        center_col = meta['center_col']
        target_row = meta['target_row']
        target_col = meta['target_col']
        cells = meta['cells']

        # Movement toward target
        if center_row == target_row and center_col == target_col:
            meta['target_row'] = random.randint(10, max_rows - 11)
            meta['target_col'] = random.randint(12, max_cols - 13)
        else:
            dr = 0
            dc = 0
            if center_row < target_row:
                dr = 1
            elif center_row > target_row:
                dr = -1
            if center_col < target_col:
                dc = 1
            elif center_col > target_col:
                dc = -1

            new_cells = {}
            for (r, c), dist in cells.items():
                new_r = r + dr
                new_c = c + dc
                if 0 <= new_r < max_rows and 0 <= new_c < max_cols:
                    new_cells[(new_r, new_c)] = dist

            cells = new_cells
            meta['center_row'] = center_row + dr
            meta['center_col'] = center_col + dc

        # Morphing: grow new cells on edges (30% chance per update)
        if random.random() < 0.3 and cells:
            # Find edge cells (cells with max distance)
            max_dist = meta['max_dist']
            edge_cells = [(r, c) for (r, c), d in cells.items() if d >= max_dist - 1]

            if edge_cells:
                # Pick a random edge cell to grow from
                grow_from = random.choice(edge_cells)
                r, c = grow_from
                neighbors = [
                    (r-1, c), (r+1, c), (r, c-1), (r, c+1),
                    (r-1, c-1), (r-1, c+1), (r+1, c-1), (r+1, c+1)
                ]
                for nr, nc in neighbors:
                    if (nr, nc) not in cells:
                        if 0 <= nr < max_rows and 0 <= nc < max_cols:
                            if random.random() < 0.4:
                                cells[(nr, nc)] = max_dist + 1
                                meta['max_dist'] = max_dist + 1
                                break

        # Morphing: shrink cells on edges (25% chance per update)
        if random.random() < 0.25 and cells:
            max_dist = meta['max_dist']
            edge_cells = [(r, c) for (r, c), d in cells.items() if d >= max_dist - 1]

            if edge_cells and len(cells) > 10:  # Keep minimum size
                # Remove a random edge cell
                remove_cell = random.choice(edge_cells)
                del cells[remove_cell]

                # Recalculate max_dist if needed
                if cells:
                    meta['max_dist'] = max(cells.values())

        # Morphing: occasionally shift some edge cells sideways (20% chance)
        if random.random() < 0.2 and cells:
            max_dist = meta['max_dist']
            edge_cells = [(r, c) for (r, c), d in cells.items() if d >= max_dist - 2]

            if edge_cells:
                # Pick a cell to shift
                shift_cell = random.choice(edge_cells)
                r, c = shift_cell
                old_dist = cells[(r, c)]

                # Pick a random adjacent empty cell
                neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
                random.shuffle(neighbors)
                for nr, nc in neighbors:
                    if (nr, nc) not in cells:
                        if 0 <= nr < max_rows and 0 <= nc < max_cols:
                            # Move the cell
                            del cells[(r, c)]
                            cells[(nr, nc)] = old_dist
                            break

        meta['cells'] = cells

def update_waves():
    """
    Move waves across the grid.
    When a wave goes off the edge, wrap it to the other side.
    """
    global waves

    max_cols = 80
    max_rows = 45

    for wave in waves:
        position, length, direction, axis = wave[0], wave[1], wave[2], wave[3]

        # Move wave in its direction
        new_position = position + direction

        # Wrap around edges
        if axis == 'x':
            if new_position >= max_cols:
                new_position = 0
            elif new_position < 0:
                new_position = max_cols - 1
        else:  # axis == 'y'
            if new_position >= max_rows:
                new_position = 0
            elif new_position < 0:
                new_position = max_rows - 1

        wave[0] = new_position

def get_cells_near_meta_shapes():
    """
    Get a list of all cells that are within or near any meta-shape or wave.
    This includes cells that need updating as meta-shapes and waves move.
    """
    global meta_shapes, waves
    cells = set()

    max_cols = 80
    max_rows = 45

    # Add cells from organic meta-shapes plus neighbors
    for meta in meta_shapes:
        for (r, c) in meta['cells'].keys():
            cells.add((r, c))
            # Also add immediate neighbors for smooth transitions
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < max_rows and 0 <= nc < max_cols:
                        cells.add((nr, nc))

    # Add cells near waves
    for wave in waves:
        position, length, direction, axis, span_start = wave[0], wave[1], wave[2], wave[3], wave[4]

        if axis == 'x':
            # Horizontal wave - add cells in the wave's path
            for offset in range(-length - 1, length + 2):
                col = (position + offset) % max_cols
                for r in range(max(0, span_start - 1), min(max_rows, span_start + 5)):
                    cells.add((r, col))
        else:  # axis == 'y'
            # Vertical wave - add cells in the wave's path
            for offset in range(-length - 1, length + 2):
                row = (position + offset) % max_rows
                for c in range(max(0, span_start - 1), min(max_cols, span_start + 5)):
                    cells.add((row, c))

    return list(cells)

def get_meta_shape_color(row, col):
    """
    Get the color for a cell based on meta-shape membership.
    Returns (r, g, b) tuple or None if not part of any meta-shape.
    Colors are blended when a cell belongs to multiple meta-shapes.
    Center cells have full saturation, outer rings have decreasing saturation.
    """
    global meta_shapes

    # Collect color contributions from all meta-shapes this cell belongs to
    contributions = []

    for meta in meta_shapes:
        cells = meta['cells']
        max_dist = meta['max_dist']
        hue = meta['hue']

        if (row, col) in cells:
            distance = cells[(row, col)]
            # Normalize distance to 0-1 range
            normalized_dist = distance / max_dist if max_dist > 0 else 0

            # Saturation decreases from center (1.0) to edge (0.3)
            saturation = 1.0 - normalized_dist * 0.7

            # Weight for blending - closer to center = more influence
            weight = 1.0 - normalized_dist * 0.5

            contributions.append((hue, saturation, weight))

    if not contributions:
        return None

    if len(contributions) == 1:
        # Single meta-shape - just use its color
        hue, saturation, _ = contributions[0]
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, 0.95)
        return (int(r * 255), int(g * 255), int(b * 255))

    # Multiple meta-shapes - blend colors
    # Convert each HSV to RGB, then blend by weight
    total_weight = sum(c[2] for c in contributions)
    blended_r, blended_g, blended_b = 0.0, 0.0, 0.0

    for hue, saturation, weight in contributions:
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, 0.95)
        normalized_weight = weight / total_weight
        blended_r += r * normalized_weight
        blended_g += g * normalized_weight
        blended_b += b * normalized_weight

    return (int(blended_r * 255), int(blended_g * 255), int(blended_b * 255))

def update_single_cell():
    """
    Update a single cell near a meta-shape based on current meta-shape positions.
    This creates the train station flip-board effect while maintaining meta-shape integrity.
    """
    global grid

    # Get cells that are near meta-shapes
    affected_cells = get_cells_near_meta_shapes()

    if not affected_cells:
        return

    # Pick a random cell from those near meta-shapes
    row, col = random.choice(affected_cells)

    # Recalculate this cell's size based on current meta-shapes
    size_factor = get_meta_shape_size(row, col)
    if size_factor is None:
        size_factor = 0.5

    # Keep the existing shape type
    old_shape_type = grid[row][col][0]
    grid[row][col] = (old_shape_type, size_factor)

def draw(screen, etc):
    """Draw function called every frame"""
    global grid, frame_count

    # Initialize grid if not done yet
    if grid is None:
        setup(screen, etc)

    # Get knob values from etc object (Eyesy hardware API)
    knob1 = etc.knob1
    knob2 = etc.knob2
    knob3 = etc.knob3
    knob4 = etc.knob4
    knob5 = etc.knob5

    # Animation controlled by knob2
    # knob2 = 0: no animation
    # knob2 = 1: update many cells per frame
    if knob2 > 0.01:
        # Number of cells to update per frame (1 to 50 based on knob2)
        cells_to_update = max(1, int(knob2 * 50))

        # Update meta-shape positions
        update_meta_shapes()

        # Update wave positions
        update_waves()

        # Update multiple cells per frame for faster animation
        for _ in range(cells_to_update):
            update_single_cell()

    frame_count += 1

    # Background color controlled by knob3 (0 = black, 1 = white)
    bg_value = int(knob3 * 255)
    screen.fill((bg_value, bg_value, bg_value))

    # Knob 1 controls grid density
    # At 0.0: 16x9, at 1.0: 80x45
    min_cols, max_cols = 16, 80
    min_rows, max_rows = 9, 45

    cols = int(min_cols + knob1 * (max_cols - min_cols))
    rows = int(min_rows + knob1 * (max_rows - min_rows))

    # Ensure at least minimum
    cols = max(min_cols, cols)
    rows = max(min_rows, rows)

    # Calculate spacing (1280x720 resolution)
    spacing_x = 1280 / cols
    spacing_y = 720 / rows

    # Max shape size is based on cell size (leave some margin)
    max_size = int(min(spacing_x, spacing_y) * 0.9)

    # Calculate step to sample from the full grid
    col_step = 80 / cols
    row_step = 45 / rows

    # Draw the grid
    for row in range(rows):
        for col in range(cols):
            # Calculate position (centered in each cell)
            x = int(spacing_x / 2 + col * spacing_x)
            y = int(spacing_y / 2 + row * spacing_y)

            # Sample from the master grid
            grid_row = int(row * row_step) % 45
            grid_col = int(col * col_step) % 80

            # Get shape type and size factor for this cell
            shape_type, size_factor = grid[grid_row][grid_col]

            # Calculate actual size based on cell size and size factor
            size = max(2, int(max_size * size_factor))

            # Determine color based on knob5 (color mode)
            # Use grid position to seed variation so it's stable per cell
            cell_seed = (grid_row * 80 + grid_col) * 17 % 100

            if knob5 < 0.25:
                # Greyscale mode (knob5 = 0)
                # Foreground color controlled by knob4 (0 = white, 1 = black)
                fg_value = int((1 - knob4) * 255)
                color = (fg_value, fg_value, fg_value)
            elif knob5 < 0.5:
                # Rainbow mode (knob5 = 0.33) - mosaic style with variation
                # Calculate base hue from position (top-left to bottom-right diagonal)
                diagonal_pos = (col / cols + row / rows) / 2.0
                base_hue = diagonal_pos * 0.85

                # Add random variation based on grid cell (consistent per cell)
                hue_variation = (cell_seed / 100.0 - 0.5) * 0.15  # +/- 0.075 hue variation
                hue = (base_hue + hue_variation) % 1.0

                # Also vary saturation and value slightly for mosaic effect
                sat_variation = 0.7 + (cell_seed % 30) / 100.0  # 0.7 to 1.0
                val_variation = 0.8 + ((cell_seed * 3) % 20) / 100.0  # 0.8 to 1.0

                r, g, b = colorsys.hsv_to_rgb(hue, sat_variation, val_variation)
                color = (int(r * 255), int(g * 255), int(b * 255))
            elif knob5 < 0.75:
                # Synthwave mode (knob5 = 0.66) - vertical gradient blue-green to purple
                # Purple (magenta) at top, blue-green (cyan/teal) at bottom
                # Using HSV: purple ~0.8-0.85, cyan/teal ~0.45-0.5
                vertical_pos = row / rows  # 0 at top, 1 at bottom

                # Interpolate hue from purple (top) to cyan (bottom)
                # Purple hue ~0.83, Cyan hue ~0.5
                purple_hue = 0.83
                cyan_hue = 0.5
                base_hue = purple_hue + vertical_pos * (cyan_hue - purple_hue)

                # Add mosaic-style variation
                hue_variation = (cell_seed / 100.0 - 0.5) * 0.08  # +/- 0.04 hue variation
                hue = (base_hue + hue_variation) % 1.0

                # High saturation for that neon synthwave look
                sat_variation = 0.85 + (cell_seed % 15) / 100.0  # 0.85 to 1.0
                val_variation = 0.85 + ((cell_seed * 3) % 15) / 100.0  # 0.85 to 1.0

                r, g, b = colorsys.hsv_to_rgb(hue, sat_variation, val_variation)
                color = (int(r * 255), int(g * 255), int(b * 255))
            else:
                # Meta-shape color mode (knob5 = 1)
                # Each meta-shape has its own random color
                # Saturation decreases from center to edge
                # Colors blend where meta-shapes overlap
                meta_color = get_meta_shape_color(grid_row, grid_col)
                if meta_color:
                    color = meta_color
                else:
                    # Default color for cells not in any meta-shape
                    # Use a neutral grey based on knob4
                    fg_value = int((1 - knob4) * 200 + 55)  # 55-255 range
                    color = (fg_value, fg_value, fg_value)

            if shape_type == 1:
                # Draw circle
                pygame.draw.circle(screen, color, (x, y), size // 2)
            else:
                # Draw square (centered on position)
                half = size // 2
                pygame.draw.rect(screen, color, (x - half, y - half, size, size))
