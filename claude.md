# Eyesy Python Simulator Project

## Project Overview
We are building a web-based simulator for the **Critter & Guitari Eyesy video synthesizer** that can run actual Python scripts locally. The Eyesy is a hardware device that converts audio into visuals using Python/pygame scripts.

## Background & Context

### What is Eyesy?
- Hardware video synthesizer by Critter & Guitari
- Runs on Raspberry Pi with Python 3
- Uses pygame for rendering visuals
- Has 5 knobs for real-time parameter control
- Responds to audio input (scope modes) or triggers (trigger modes)
- Scripts are called "modes" and follow a specific API structure
- Resolution: 1280x720
- Modes are open source and available on GitHub

### Why This Project?
- Develop and test Eyesy modes without the physical hardware
- Faster iteration cycle for visual development
- Can run actual Eyesy Python scripts with minimal modification
- Educational tool for learning Eyesy mode development

### Prior Work
We built a proof-of-concept HTML prototype using JavaScript that successfully demonstrated:
- Canvas rendering (1280x720)
- 5 interactive knobs (0.0 to 1.0 range)
- pygame-style drawing API (circles, rectangles, lines, polygons)
- Animation loop working smoothly
- Example modes (simple circle, spiral animation)

**Why not use that?** We initially tried Pyodide (Python in WebAssembly) but it crashed the browser due to size (~100MB). The JavaScript version proved the concept works, but we need **real Python** to run actual Eyesy scripts.

## Technical Requirements

### Python Environment
- **Python 3.7-3.9** (to match Eyesy hardware capabilities)
- **Flask** web framework (simpler, traditional, good for this use case)
- **pygame** or a pygame shim/compatibility layer
- **WebSockets** for real-time canvas updates to browser
- **Audio processing** libraries (for simulating audio input)

### Eyesy API Structure
Eyesy modes follow this pattern:

```python
# Example Eyesy mode structure (main.py)

def setup(screen, etc):
    """Called once at initialization"""
    # Initialize variables, load resources
    pass

def draw(screen, etc):
    """Called every frame"""
    # Clear screen
    screen.fill((0, 0, 0))
    
    # Access knob values (global variables, 0.0 to 1.0)
    x = int(knob1 * 1280)
    y = int(knob2 * 720)
    
    # Access audio data from etc object
    # etc.audio_in - audio samples (list/array)
    # etc.audio_left, etc.audio_right - stereo
    # etc.audio_trig - trigger event boolean
    
    # Draw using pygame
    pygame.draw.circle(screen, (255, 0, 0), (x, y), 50)
```

### Key Globals/API Available to Scripts
- `knob1`, `knob2`, `knob3`, `knob4`, `knob5` - float values 0.0 to 1.0
- `screen` - pygame Surface object (1280x720)
- `etc` - object containing:
  - `etc.audio_in` - mono audio buffer
  - `etc.audio_left` - left channel
  - `etc.audio_right` - right channel  
  - `etc.audio_trig` - trigger boolean
  - `etc.mode` - current mode name
  - Other metadata
- `pygame` module for drawing

### pygame Drawing Functions Needed
- `pygame.draw.circle(surface, color, pos, radius, width=0)`
- `pygame.draw.rect(surface, color, rect, width=0)`
- `pygame.draw.line(surface, color, start, end, width=1)`
- `pygame.draw.polygon(surface, color, points, width=0)`
- `pygame.draw.ellipse(surface, color, rect, width=0)`
- `pygame.draw.arc(surface, color, rect, start_angle, stop_angle, width=1)`
- `screen.fill(color)` - clear screen to color
- `screen.get_size()` - returns (1280, 720)

## Project Structure

```
eyesy-simulator/
├── backend/
│   ├── app.py                 # Flask app with WebSocket
│   ├── eyesy_engine.py        # Core Eyesy execution engine
│   ├── pygame_shim.py         # pygame compatibility layer
│   └── audio_processor.py     # Audio input simulation
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── app.js         # WebSocket client, canvas rendering
│   └── templates/
│       └── index.html         # Main UI
├── modes/
│   ├── S-Simple-Circle/
│   │   └── main.py
│   ├── S-Spiral/
│   │   └── main.py
│   └── T-Flash/
│       └── main.py
├── audio_samples/
│   └── test_audio.wav
├── requirements.txt
├── README.md
└── claude.md                  # This file
```

## Features to Implement

### Phase 1 (MVP)
1. ✅ Flask server with WebSocket support
2. ✅ Load and execute Eyesy Python scripts (main.py)
3. ✅ pygame shim that renders to PIL Image or canvas buffer
4. ✅ WebSocket streaming of canvas frames to browser
5. ✅ Web UI with:
   - Canvas display (1280x720)
   - 5 knob controls (sliders)
   - Mode selector (load different scripts)
   - Start/Stop button
6. ✅ Example modes included

### Phase 2 (Audio)
1. Load WAV file as audio input
2. Process audio into buffer that scripts can access
3. Simulate audio_in, audio_left, audio_right
4. Implement trigger detection (audio threshold crossing)
5. Real-time microphone input (optional)

### Phase 3 (Polish)
1. File browser to load modes from disk
2. Hot reload - watch main.py for changes
3. FPS counter and performance metrics
4. Color palette system (Eyesy has foreground/background palettes)
5. Save recordings to video file
6. MIDI input support (optional)

## Technical Approach

### Canvas Rendering Strategy
Since we need to run Python on the backend and display in browser:

**Option A: PIL/Pillow Images**
- pygame shim renders to PIL Image
- Convert image to base64 PNG
- Send via WebSocket to browser
- Browser displays on canvas

**Option B: Raw Pixel Data**
- pygame shim writes to numpy array
- Send binary pixel data via WebSocket
- Use ImageData in browser to render

**Recommendation:** Start with Option A (PIL) for simplicity, optimize later if needed.

### WebSocket Communication
```javascript
// Browser -> Server
{
  "type": "knob_change",
  "knob": 1,
  "value": 0.75
}

{
  "type": "load_mode",
  "path": "modes/S-Spiral"
}

// Server -> Browser
{
  "type": "frame",
  "image": "data:image/png;base64,..." 
}

{
  "type": "status",
  "message": "Mode loaded successfully"
}
```

## Resources & References

### Official Eyesy Resources
- Eyesy Manual: https://critterandguitari.github.io/cg-docs/EYESY/
- GitHub Repos:
  - EYESY_OS: https://github.com/critterandguitari/EYESY_OS
  - EYESY_Modes_Pygame: https://github.com/critterandguitari/EYESY_Modes_Pygame
- Community modes: https://patchstorage.com/platform/eyesy/

### Similar Projects
- eyesim by notmatthancock: https://github.com/notmatthancock/eyesim
  - Python 3 simulator using actual pygame
  - Good reference for API implementation

## Development Notes

### Challenges to Consider
1. **pygame installation** - May need headless rendering (no display)
2. **Performance** - Need to maintain ~30-60 FPS
3. **Script isolation** - User scripts shouldn't crash the server
4. **Audio sync** - Keeping audio and visuals in sync
5. **Color accuracy** - RGB color matching between Python and browser

### Design Decisions Made
- Python 3.7+ (Eyesy compatible)
- Flask (not FastAPI) for simplicity
- WebSocket for real-time communication
- PIL/Pillow for image generation
- Start without actual pygame, use shim
- Audio comes second (visual rendering first)

## Getting Started Commands

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install flask flask-socketio pillow numpy

# Run server
python backend/app.py

# Access at http://localhost:5000
```

## User Stories

1. **As a developer**, I want to write an Eyesy mode in Python and see it running immediately without deploying to hardware
2. **As a VJ**, I want to test different visual modes with my music before a performance
3. **As a learner**, I want to understand how Eyesy modes work by tweaking examples
4. **As a creator**, I want to load a WAV file and see how my visuals respond to the audio

## Success Criteria

This project is successful when:
- ✅ Can load actual Eyesy Python scripts (main.py files)
- ✅ Scripts render visuals that update in real-time in browser
- ✅ 5 knobs control parameters smoothly
- ✅ Maintains 30+ FPS
- ✅ Audio input can be loaded from WAV file
- ✅ Scripts can access audio data through etc object
- ✅ Multiple example modes work correctly

## Next Steps for Claude Code

1. Set up Flask app with WebSocket support
2. Create pygame shim that can render pygame commands to PIL Image
3. Implement Eyesy script executor that runs main.py files
4. Build web frontend with canvas and controls
5. Add example modes
6. Implement audio input simulation
7. Test with actual Eyesy scripts from GitHub

---

**Important:** The user has already validated that the concept works with a JavaScript prototype. The canvas rendering, knobs, and animation loop all work smoothly. Now we just need to replace the JavaScript execution with real Python script execution on the backend.