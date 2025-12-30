# Simple Circle Mode
# Basic test mode that draws a circle controlled by knobs

import pygame

def setup(screen, etc):
    """Setup function called once when mode loads"""
    pass

def draw(screen, etc):
    """Draw function called every frame"""
    # Clear screen to black
    screen.fill((0, 0, 0))

    # Get knob values from etc object (Eyesy hardware API)
    x = int(etc.knob1 * 1280)  # X position from knob 1
    y = int(etc.knob2 * 720)   # Y position from knob 2
    radius = int(etc.knob3 * 100) + 10  # Radius from knob 3 (10-110)
    red = int(etc.knob4 * 255)    # Red component from knob 4
    green = int(etc.knob5 * 255)  # Green component from knob 5

    # Draw circle
    pygame.draw.circle(screen, (red, green, 255), (x, y), radius)