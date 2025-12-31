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

    # Access knob values from etc object (0.0 to 1.0)
    # IMPORTANT: Always use etc.knob1, etc.knob2, etc. - NOT bare globals!
    x = int(etc.knob1 * 1280)
    y = int(etc.knob2 * 720)

    # Access audio data from etc object
    # etc.audio_in - audio samples (list/array)
    # etc.audio_left, etc.audio_right - stereo
    # etc.audio_trig - trigger event boolean

    # Draw using pygame
    pygame.draw.circle(screen, (255, 0, 0), (x, y), 50)
```

### IMPORTANT: Eyesy Hardware Compatibility

**Always access knob values via the `etc` object, not as bare globals:**

```python
# CORRECT - works on real Eyesy hardware AND simulator
x = int(etc.knob1 * 1280)
color_value = etc.knob4 * 255

# WRONG - only works in simulator, fails on real hardware
x = int(knob1 * 1280)  # NameError on real Eyesy!
```

The simulator injects knob values as both module globals AND etc attributes for backwards compatibility, but the real Eyesy hardware only provides them via the `etc` object. Always use `etc.knob1` through `etc.knob5` to ensure modes work in both environments.

**Always import pygame at the top of your mode:**

```python
import pygame  # Required for pygame.draw functions on real hardware
```

The real Eyesy hardware requires an explicit `import pygame` statement. The simulator injects pygame as a module global, but real hardware does not.

### Key API Available to Scripts (via `etc` object)
- `etc.knob1` through `etc.knob5` - float values 0.0 to 1.0
- `etc.audio_in` - mono audio buffer (list of samples)
- `etc.audio_left` - left channel audio
- `etc.audio_right` - right channel audio
- `etc.audio_trig` - trigger boolean (True when audio exceeds threshold)
- `etc.trig` - alias for audio_trig
- `etc.mode` - current mode name
- `etc.xres`, `etc.yres` - screen resolution (1280, 720)
- `etc.bg_color` - current background color tuple
- `etc.fg_color` - current foreground color tuple
- `etc.color_picker(val)` - get foreground color from palette (val 0.0-1.0)
- `etc.color_picker_bg(val)` - get background color from palette (val 0.0-1.0)
- `etc.auto_clear` - whether screen auto-clears between frames
- `etc.midi_note_new` - True when new MIDI note received
- `etc.midi_note` - last MIDI note number (0-127)
- `etc.midi_velocity` - last MIDI velocity (0-127)
- `screen` - pygame Surface object (1280x720)
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

## Recent Development Progress

### Completed Features (as of Dec 2024)

#### Core Simulator
- ✅ Flask server with WebSocket (flask-socketio) on port 5001
- ✅ pygame shim (`pygame_shim.py`) renders to PIL Image
- ✅ Eyesy script executor loads and runs main.py files
- ✅ WebSocket streaming of base64 PNG frames to browser
- ✅ 5 knob controls with real-time updates
- ✅ Mode selector with refresh functionality
- ✅ File browser to load custom main.py files
- ✅ FPS counter displaying actual frame rate

#### Audio Simulation
- ✅ Multiple audio types: Silence, Sine Wave, White Noise, Beat/Kick, Audio File
- ✅ Audio level and frequency controls
- ✅ "Play in browser" toggle to hear simulated audio
- ✅ Audio file upload and playback with Web Audio API
- ✅ Real-time audio data streaming to backend via WebSocket
- ✅ Audio analyser for waveform extraction from uploaded files
- ✅ Play/Pause button for audio simulation control

#### pygame Shim Features
- ✅ `pygame.draw.circle()`, `rect()`, `line()`, `polygon()`, `ellipse()`, `arc()`
- ✅ `pygame.draw.lines()` for connected line segments
- ✅ `Surface.fill()`, `get_size()`, `blit()`, `get_width()`, `get_height()`, `get_rect()`
- ✅ `Surface.convert_alpha()` for alpha channel support
- ✅ `pygame.font.Font` and `pygame.font.SysFont` for text rendering
- ✅ `Rect` class with position and size attributes
- ✅ Color constants (SRCALPHA)

#### UI/UX Improvements
- ✅ IBM Plex Mono font from Google Fonts
- ✅ Clean title bar (no glow effects or emojis, left-aligned)
- ✅ Collapsible Controls panel (shrinks to narrow column when collapsed)
- ✅ Preview panel with 16:9 aspect ratio maintained
- ✅ Preview size indicator showing actual canvas dimensions
- ✅ Auto-apply audio settings when sliders change during playback
- ✅ "Play in browser" defaults to checked

#### Example Modes Included
- `S-Simple-Circle/` - Basic circle following knob positions
- `S-Spiral/` - Animated spiral pattern
- `S-Scope/` - Audio waveform visualization (scope mode)
- `S-String-Vibration/` - String vibration visualization
- `S-Living-Grid/` - Dynamic grid pattern
- `T-Flash/` - Trigger-based flash mode

### Known Issues / Considerations
- Server runs on port **5001** (not 5000)
- Modes must use `etc.knob1` through `etc.knob5` (not bare globals) for hardware compatibility
- Modes must `import pygame` at the top for hardware compatibility

### File Structure (Current)
```
eyesy_sim/
├── backend/
│   ├── app.py                 # Flask app with WebSocket (port 5001)
│   ├── eyesy_engine.py        # Core Eyesy execution engine
│   ├── pygame_shim.py         # pygame compatibility layer (PIL-based)
│   └── audio_processor.py     # Audio input simulation
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css      # IBM Plex Mono, collapsible panels
│   │   └── js/
│   │       └── app.js         # WebSocket client, audio playback, UI
│   └── templates/
│       └── index.html         # Main UI with Google Fonts
├── modes/
│   ├── S-Simple-Circle/main.py
│   ├── S-Spiral/main.py
│   ├── S-Scope/main.py
│   ├── S-String-Vibration/main.py
│   ├── S-Living-Grid/main.py
│   └── T-Flash/main.py
├── requirements.txt
├── README.md
└── CLAUDE.md                  # This file
```

### Running the Simulator
```bash
# Activate virtual environment
source venv/bin/activate

# Run server
python backend/app.py

# Access at http://localhost:5001
```

---

## Original Planning Notes

### Next Steps for Claude Code

1. ~~Set up Flask app with WebSocket support~~ ✅
2. ~~Create pygame shim that can render pygame commands to PIL Image~~ ✅
3. ~~Implement Eyesy script executor that runs main.py files~~ ✅
4. ~~Build web frontend with canvas and controls~~ ✅
5. ~~Add example modes~~ ✅
6. ~~Implement audio input simulation~~ ✅
7. Test with actual Eyesy scripts from GitHub (ongoing)

### Future Enhancements to Consider
- Hot reload - watch main.py for changes
- Color palette system (Eyesy foreground/background palettes)
- Save recordings to video file
- MIDI input support
- Real-time microphone input

---

**Important:** The user has already validated that the concept works with a JavaScript prototype. The canvas rendering, knobs, and animation loop all work smoothly. Now we just need to replace the JavaScript execution with real Python script execution on the backend.