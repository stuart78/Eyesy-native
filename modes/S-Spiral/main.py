# Spiral Mode
# Animated spiral of colored circles

import math

# Global variables for animation
angle = 0.0

def setup(screen, etc):
    """Setup function called once when mode loads"""
    global angle
    angle = 0.0

def draw(screen, etc):
    """Draw function called every frame"""
    global angle

    # Clear screen to black
    screen.fill((0, 0, 0))

    # Parameters from knobs (Eyesy hardware API)
    num_circles = int(etc.knob1 * 20) + 3      # Number of circles (3-23)
    radius = etc.knob2 * 200 + 50              # Spiral radius (50-250)
    size = int(etc.knob3 * 30) + 5             # Circle size (5-35)
    speed = etc.knob4 * 0.2                    # Animation speed
    hue_shift = etc.knob5 * 360                # Color hue shift

    # Update animation
    angle += speed

    # Draw spiral
    for i in range(num_circles):
        # Calculate position
        a = angle + (i * 2 * math.pi / num_circles)
        x = int(640 + math.cos(a) * radius)
        y = int(360 + math.sin(a) * radius)

        # Calculate color using HSV-like approach
        hue = (i * 360 / num_circles + hue_shift) % 360
        h = hue / 60
        c = 255
        x_val = c * (1 - abs(h % 2 - 1))

        if h < 1:
            r, g, b = c, int(x_val), 0
        elif h < 2:
            r, g, b = int(x_val), c, 0
        elif h < 3:
            r, g, b = 0, c, int(x_val)
        elif h < 4:
            r, g, b = 0, int(x_val), c
        elif h < 5:
            r, g, b = int(x_val), 0, c
        else:
            r, g, b = c, 0, int(x_val)

        # Draw circle
        pygame.draw.circle(screen, (r, g, b), (x, y), size)