# Flash Mode
# Trigger mode that responds to audio/manual triggers

import pygame

frame_count = 0
flash_intensity = 0.0

def setup(screen, etc):
    """Setup function called once when mode loads"""
    global frame_count, flash_intensity
    frame_count = 0
    flash_intensity = 0.0

def draw(screen, etc):
    """Draw function called every frame"""
    global frame_count, flash_intensity

    frame_count += 1

    # Use knob5 as manual trigger (when > 0.8)
    trigger = etc.knob5 > 0.8 or etc.audio_trig

    # Flash parameters (Eyesy hardware API)
    decay_rate = etc.knob1 * 0.3 + 0.05  # Flash decay speed
    flash_size = etc.knob2 * 300 + 50    # Flash size
    color_hue = etc.knob3 * 360          # Flash color
    pattern = int(etc.knob4 * 4)         # Flash pattern (0-3)

    # Update flash intensity
    if trigger:
        flash_intensity = 1.0
    else:
        flash_intensity = max(0.0, flash_intensity - decay_rate)

    # Clear screen
    screen.fill((0, 0, 0))

    if flash_intensity > 0.01:
        # Calculate color
        h = color_hue / 60
        c = int(255 * flash_intensity)
        x_val = int(c * (1 - abs(h % 2 - 1)))

        if h < 1:
            r, g, b = c, x_val, 0
        elif h < 2:
            r, g, b = x_val, c, 0
        elif h < 3:
            r, g, b = 0, c, x_val
        elif h < 4:
            r, g, b = 0, x_val, c
        elif h < 5:
            r, g, b = x_val, 0, c
        else:
            r, g, b = c, 0, x_val

        # Draw different patterns based on knob4
        if pattern == 0:
            # Full screen flash
            screen.fill((r, g, b))
        elif pattern == 1:
            # Center circle
            radius = int(flash_size * flash_intensity)
            pygame.draw.circle(screen, (r, g, b), (640, 360), radius)
        elif pattern == 2:
            # Rectangle bars
            bar_height = int(flash_size * flash_intensity)
            pygame.draw.rect(screen, (r, g, b), (0, 360 - bar_height//2, 1280, bar_height))
        else:
            # Cross pattern
            thickness = int(flash_size * flash_intensity * 0.3)
            pygame.draw.rect(screen, (r, g, b), (640 - thickness//2, 0, thickness, 720))
            pygame.draw.rect(screen, (r, g, b), (0, 360 - thickness//2, 1280, thickness))