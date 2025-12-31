# Eyesy Python Simulator

A web-based simulator for the **Critter & Guitari Eyesy video synthesizer** that runs actual Python scripts locally.

## ✅ Current Status: MVP Complete + File Browser

The simulator is now functional with all core features implemented:

- ✅ Flask server with WebSocket support
- ✅ pygame compatibility shim that renders to PIL images
- ✅ Eyesy script executor that runs actual main.py files
- ✅ Real-time WebSocket streaming of canvas frames
- ✅ Web UI with 5 knob controls and mode selector
- ✅ **File browser for loading external Python files**
- ✅ **Enhanced Eyesy API compatibility**
- ✅ Three example modes included and working

## Quick Start

1. **Install dependencies:**
   ```bash
   cd eyesy_sim
   python3 -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install flask flask-socketio pillow numpy python-socketio
   ```

2. **Run the simulator:**
   ```bash
   cd backend
   source ../venv/bin/activate
   python app.py
   ```

3. **Open in browser:**
   ```
   http://localhost:5001
   ```

## How to Use

1. **Select a mode** from the dropdown (S-Simple-Circle, S-Spiral, T-Flash)
2. **Click "Load Mode"** to load the Python script
3. **Click "Start"** to begin rendering
4. **Adjust the 5 knobs** to control the visuals in real-time
5. **Click "Stop"** to stop rendering

## Example Modes Included

- **S-Simple-Circle**: Basic circle controlled by knobs (position, size, color)
- **S-Spiral**: Animated spiral with color cycling
- **T-Flash**: Trigger mode that flashes when knob 5 > 0.8

## Architecture

The system follows the exact plan from your JavaScript proof of concept:

- **Backend**: Python Flask app with pygame shim
- **Frontend**: HTML5 canvas with WebSocket connection
- **Real-time**: 30 FPS rendering streamed as base64 PNG images
- **API Compatible**: Uses actual Eyesy Python API (knob1-5, screen, etc)

## Supported Eyesy API

The simulator supports the core Eyesy API for maximum compatibility:

### **Color Functions**
- `eyesy.color_picker(value)` - Returns RGB color based on 0.0-1.0 value
- `eyesy.color_picker_bg(value)` - Background color picker
- `eyesy.color_picker_fg(value)` - Foreground color picker

### **Knob Values**
- `knob1`, `knob2`, `knob3`, `knob4`, `knob5` - Global knob values (0.0-1.0)
- `eyesy.knob1`, `eyesy.knob2`, etc. - Also available via eyesy object

### **Audio Data**
- `etc.audio_in` - Mono audio buffer (1024 samples)
- `etc.audio_left`, `etc.audio_right` - Stereo channels
- `etc.audio_trig` - Audio trigger boolean
- `eyesy.trig` - Audio trigger (alias for audio_trig)

### **Screen Properties**
- `screen` - pygame Surface object (1280x720)
- `etc.xres`, `etc.yres` - Screen resolution values

## Adding New Modes

Create a new directory in `modes/` with a `main.py` file:

```python
def setup(screen, etc):
    """Called once when mode loads"""
    pass

def draw(screen, etc):
    """Called every frame"""
    screen.fill((0, 0, 0))  # Clear screen

    # Use knob values
    x = int(knob1 * 1280)
    y = int(knob2 * 720)
    color = eyesy.color_picker(knob3)  # Get color from knob

    # Draw with pygame
    pygame.draw.circle(screen, color, (x, y), 50)
```

## Next Steps

The MVP is complete! You can now:

1. **Test with real Eyesy scripts** from the official repositories
2. **Add audio support** (Phase 2 from claude.md)
3. **Add hot-reload** for development
4. **Implement recording to video files**

The transition from your JavaScript proof of concept to this full Python implementation is complete and working! 🎉
