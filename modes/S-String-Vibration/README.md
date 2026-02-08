# String Vibration Mode

A mesmerizing audio-reactive visualization that renders vertical strings in 3D space. Each string displays a portion of the audio waveform, creating a scrolling "sound fingerprint" effect as audio flows across the field of strings from left to right.

## How It Works

When audio is present, each string acts like a slice through time - the leftmost strings show older audio, and the rightmost strings show the most recent sound. This creates a waterfall-like visualization where you can literally see sound traveling across the screen.

Without audio input, the strings animate with a gentle sine wave pattern, creating an ambient visual effect.

The strings are rendered with 3D perspective projection and can be rotated in space to create dynamic viewing angles.

## Controls

### Knob 1 - String Count
Controls the number of vertical strings displayed.
- **0.0**: 8 strings (sparse, bold look)
- **1.0**: 64 strings (dense, detailed look)

### Knob 2 - Amplitude & Smoothness
A dual-function control:
- **0.0**: Strings are still (no displacement) with maximum smoothing applied
- **1.0**: Maximum displacement with no smoothing (raw, jagged waveforms)

Turn down for calmer, smoother visuals. Turn up for energetic, detailed audio response.

### Knob 3 - X-Axis Rotation (Tilt)
Tilts the entire string field forward or backward.
- **0.0**: Tilted back (-90 degrees)
- **0.5**: Straight on (no tilt)
- **1.0**: Tilted forward (+90 degrees)

### Knob 4 - Z-Axis Rotation (Spin)
Rotates the string field clockwise or counter-clockwise.
- **0.0**: Rotated left (-90 degrees)
- **0.5**: No rotation
- **1.0**: Rotated right (+90 degrees)

### Knob 5 - Color Mode
Selects from 10 different color palettes:

| Range | Color Mode |
|-------|------------|
| 0.0 | White (classic) |
| 0.1 | Rainbow (each string a different hue) |
| 0.2 | Audio-reactive hue shift |
| 0.3 | Green |
| 0.4 | Red |
| 0.5 | Green to purple gradient |
| 0.6 | White to black gradient |
| 0.7 | Light pink to light blue gradient |
| 0.8 | Warm cream to hot pink |
| 0.9+ | Pastel trio (cream/blue/pink) |

## Tips

- For a classic oscilloscope look: Knob 3 and 4 at 0.5 (no rotation), Knob 5 at 0.0 (white)
- For an immersive 3D effect: Rotate with Knobs 3 and 4 while audio plays
- For ambient/calm visuals: Lower Knob 2 for more smoothing
- For energetic performances: High Knob 2 with rainbow or gradient colors
- The pastel trio palette (Knob 5 at max) works beautifully for softer music

## Technical Details

- Resolution: 1280x720
- 50 points per string for smooth curves
- 3D perspective projection with depth sorting
- Strings are filled with a darker shade and outlined with the main color
- Audio history buffer creates the scrolling time-delay effect
