# EYESY Simulator

A web-based simulator for the [Critter & Guitari EYESY](https://www.critterandguitari.com/eyesy) video synthesizer that runs actual Python scripts locally.

**Version 1.0** | Created by Stuart Frederich-Smith | [signalfunctionset.com](https://signalfunctionset.com)

## Features

### Core Simulator
- Flask server with WebSocket (flask-socketio) for real-time communication
- pygame compatibility shim that renders to PIL images
- Eyesy script executor that runs actual main.py files
- Real-time WebSocket streaming of canvas frames at 30 FPS
- Web UI with 5 knob controls and mode selector
- File browser for loading external Python files
- Full Eyesy hardware API compatibility

### Audio Simulation
- Multiple audio types: Silence, Sine Wave, White Noise, Beat/Kick, Audio File
- Audio level and frequency controls
- "Play in browser" toggle to hear audio
- Audio file upload and playback with Web Audio API
- Real-time audio data streaming to backend via WebSocket
- Internet radio streaming with preset stations (SomaFM)
- Audio analyser for waveform extraction

### pygame Shim
The simulator includes a pygame compatibility layer supporting:
- `pygame.draw.circle()`, `rect()`, `line()`, `polygon()`, `ellipse()`, `arc()`
- `pygame.draw.lines()` for connected line segments
- `Surface.fill()`, `get_size()`, `blit()`, `get_width()`, `get_height()`, `get_rect()`
- `Surface.convert_alpha()` for alpha channel support
- `pygame.font.Font` and `pygame.font.SysFont` for text rendering
- `Rect` class with position and size attributes

### UI/UX
- Clean, modern interface with League Spartan font
- Collapsible Controls panel
- Preview panel with 16:9 aspect ratio maintained
- Preview size indicator showing actual canvas dimensions
- Auto-apply audio settings when sliders change during playback
- Play/Pause button for audio simulation control
- About and Help slide-in panels with documentation

## Quick Start

1. **Install dependencies:**
   ```bash
   cd eyesy_sim
   python3 -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. **Run the simulator:**
   ```bash
   source venv/bin/activate
   python backend/app.py
   ```

3. **Open in browser:**
   ```
   http://localhost:5001
   ```

## How to Use

1. **Select a mode** from the dropdown
2. **Click "Load Mode"** to load the Python script
3. **Click "Start"** to begin rendering
4. **Adjust the 5 knobs** to control the visuals in real-time
5. **Configure audio** using the Audio controls section
6. **Click the play button** next to "Audio" to start audio simulation
7. **Click "Stop"** to stop rendering

## Example Modes Included

- **S-Simple-Circle**: Basic circle controlled by knobs (position, size, color)
- **S-Spiral**: Animated spiral with color cycling
- **S-Scope**: Audio waveform visualization (oscilloscope style)
- **S-String-Vibration**: String vibration visualization responding to audio
- **S-Living-Grid**: Dynamic grid pattern
- **T-Flash**: Trigger mode that flashes on audio triggers or when knob 5 > 0.8

## Eyesy API Reference

The simulator supports the full Eyesy hardware API:

### Knob Values
```python
# Always use etc.knob1-5 for hardware compatibility
x = int(etc.knob1 * 1280)
color_intensity = etc.knob4 * 255
```

### Audio Data
```python
etc.audio_in      # Mono audio buffer (100 samples)
etc.audio_left    # Left channel
etc.audio_right   # Right channel
etc.audio_peak    # Peak audio level (0.0 to 1.0)
etc.audio_trig    # Audio trigger boolean
etc.trig          # Alias for audio_trig
```

### Screen Properties
```python
screen            # pygame Surface object (1280x720)
etc.xres          # Screen width (1280)
etc.yres          # Screen height (720)
```

### Color Functions
```python
etc.color_picker(value)     # Returns RGB tuple for value 0.0-1.0
etc.color_picker_bg(value)  # Background color picker
etc.color_picker_fg(value)  # Foreground color picker
```

### Other Properties
```python
etc.mode          # Current mode name
etc.bg_color      # Current background color
etc.fg_color      # Current foreground color
etc.auto_clear    # Whether screen auto-clears between frames
etc.midi_note_new # True when new MIDI note received
etc.midi_note     # Last MIDI note number (0-127)
etc.midi_velocity # Last MIDI velocity (0-127)
```

## Writing Modes

Create a new directory in `modes/` with a `main.py` file:

```python
import pygame  # Required for hardware compatibility

def setup(screen, etc):
    """Called once when mode loads"""
    pass

def draw(screen, etc):
    """Called every frame"""
    screen.fill((0, 0, 0))  # Clear screen

    # Use etc.knob values (hardware compatible)
    x = int(etc.knob1 * 1280)
    y = int(etc.knob2 * 720)
    radius = int(etc.knob3 * 100) + 10
    color = etc.color_picker(etc.knob4)

    # Respond to audio
    if etc.audio_trig:
        radius *= 2

    # Draw with pygame
    pygame.draw.circle(screen, color, (x, y), radius)
```

### Important: Hardware Compatibility

Always use `etc.knob1` through `etc.knob5` instead of bare globals:

```python
# CORRECT - works on real Eyesy hardware AND simulator
x = int(etc.knob1 * 1280)

# WRONG - only works in simulator, fails on real hardware
x = int(knob1 * 1280)
```

Always import pygame at the top of your mode:

```python
import pygame  # Required for real hardware
```

## Project Structure

```
eyesy_sim/
├── backend/
│   ├── app.py              # Flask app with WebSocket (port 5001)
│   ├── eyesy_engine.py     # Core Eyesy execution engine
│   ├── pygame_shim.py      # pygame compatibility layer (PIL-based)
│   └── audio_processor.py  # Audio input simulation
├── frontend/
│   ├── static/
│   │   ├── css/style.css   # UI styling
│   │   ├── js/app.js       # WebSocket client, audio playback
│   │   └── audio/          # Built-in audio samples
│   └── templates/
│       └── index.html      # Main UI
├── modes/
│   ├── S-Simple-Circle/main.py
│   ├── S-Spiral/main.py
│   ├── S-Scope/main.py
│   ├── S-String-Vibration/main.py
│   ├── S-Living-Grid/main.py
│   └── T-Flash/main.py
├── config.py               # Server configuration
├── requirements.txt
├── README.md
└── CLAUDE.md               # Development documentation
```

## Resources

- [EYESY Manual](https://critterandguitari.github.io/cg-docs/EYESY/)
- [EYESY_OS GitHub](https://github.com/critterandguitari/EYESY_OS)
- [EYESY_Modes_Pygame](https://github.com/critterandguitari/EYESY_Modes_Pygame)
- [Community Modes on Patchstorage](https://patchstorage.com/platform/eyesy/)

## License

Copyright 2025 Stuart Frederich-Smith. All rights reserved.
