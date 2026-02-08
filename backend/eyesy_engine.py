"""
Eyesy execution engine - loads and runs Eyesy Python scripts
"""

import os
import sys
import importlib.util
import traceback
from io import BytesIO
import base64
from pygame_shim import pygame, Surface

class EtcObject:
    """Mock etc object that contains audio data and metadata.

    This simulates the Eyesy hardware's 'etc' object that gets passed to modes.
    See: https://github.com/critterandguitari/EYESY_OS/blob/master/engines/python/eyesy.py
    """
    def __init__(self):
        # Audio buffers (100 samples like real Eyesy)
        self.audio_in = [0.0] * 100  # Mono audio buffer
        self.audio_left = [0.0] * 100  # Left channel (alias for audio_in)
        self.audio_right = [0.0] * 100  # Right channel
        self.audio_in_r = [0.0] * 100  # Right channel (real Eyesy naming)
        self.audio_peak = 0.0  # Peak audio level
        self.audio_peak_r = 0.0  # Right channel peak
        self.audio_trig = False
        self.mode = "unknown"
        self.xres = 1280
        self.yres = 720

        # Audio simulation parameters (simulator-specific)
        self.audio_level = 0.0  # 0.0 to 1.0
        self.audio_frequency = 440.0  # Hz for sine wave
        self.audio_type = "sine"  # "sine", "noise", "silence", "beat", "file"
        self.frame_count = 0
        self._file_audio_received = False  # True once browser sends audio data

        # Color palettes (mock values)
        self.color_picker_bg = self._color_picker_bg
        self.color_picker_fg = self._color_picker_fg
        self.color_picker = self._color_picker  # Generic color picker

        # Knob values (0.0 to 1.0) - accessed as etc.knob1, etc.knob2, etc.
        self.knob1 = 0.5
        self.knob2 = 0.5
        self.knob3 = 0.5
        self.knob4 = 0.5
        self.knob5 = 0.5

        # MIDI variables
        self.midi_note_new = False
        self.midi_note = 60
        self.midi_velocity = 127
        self.midi_notes = [0] * 128  # All MIDI note states
        self.midi_clk = 0  # MIDI clock counter

        # Color state
        self.bg_color = (0, 0, 0)
        self.fg_color = (255, 255, 255)

        # Trigger variables
        self.trig = False  # Alias for audio_trig
        self.audio_trig = False

        # System state
        self.auto_clear = True  # Whether to auto-clear screen between frames
        self.fps = 30  # Current FPS
        self.screen = None  # Reference to screen surface (set by engine)

    def _color_picker_bg(self, value):
        """Mock background color picker - returns RGB tuple based on value"""
        # Simple HSV-like color picker simulation
        value = max(0.0, min(1.0, value))  # Clamp to 0-1
        hue = value * 360
        h = hue / 60
        c = 255
        x_val = c * (1 - abs(h % 2 - 1))

        if h < 1:
            return (c, int(x_val), 0)
        elif h < 2:
            return (int(x_val), c, 0)
        elif h < 3:
            return (0, c, int(x_val))
        elif h < 4:
            return (0, int(x_val), c)
        elif h < 5:
            return (int(x_val), 0, c)
        else:
            return (c, 0, int(x_val))

    def _color_picker_fg(self, value):
        """Mock foreground color picker - returns RGB tuple based on value"""
        # Different color range for foreground
        value = max(0.0, min(1.0, value))  # Clamp to 0-1
        hue = (value * 360 + 180) % 360  # Offset by 180 degrees
        h = hue / 60
        c = 255
        x_val = c * (1 - abs(h % 2 - 1))

        if h < 1:
            return (c, int(x_val), 0)
        elif h < 2:
            return (int(x_val), c, 0)
        elif h < 3:
            return (0, c, int(x_val))
        elif h < 4:
            return (0, int(x_val), c)
        elif h < 5:
            return (int(x_val), 0, c)
        else:
            return (c, 0, int(x_val))

    def _color_picker(self, value):
        """Generic color picker - same as background for compatibility"""
        return self._color_picker_bg(value)

    def generate_audio_data(self):
        """Generate simulated audio data based on current settings.

        Real Eyesy uses 100-sample buffers, so we match that.
        """
        import math
        import random

        self.frame_count += 1
        buffer_size = 100  # Match real Eyesy buffer size

        if self.audio_type == "silence":
            # Silent audio
            self.audio_in = [0.0] * buffer_size
        elif self.audio_type == "sine":
            # Generate sine wave
            sample_rate = 44100
            samples_per_frame = buffer_size

            audio_data = []
            for i in range(samples_per_frame):
                sample_index = (self.frame_count * samples_per_frame + i)
                time_s = sample_index / sample_rate
                amplitude = self.audio_level * 32767  # 16-bit audio range
                sample = amplitude * math.sin(2 * math.pi * self.audio_frequency * time_s)
                audio_data.append(sample)

            self.audio_in = audio_data
        elif self.audio_type == "noise":
            # Generate white noise
            amplitude = self.audio_level * 32767
            self.audio_in = [random.uniform(-amplitude, amplitude) for _ in range(buffer_size)]
        elif self.audio_type == "beat":
            # Generate rhythmic beat pattern
            beat_frequency = 2.0  # 2 beats per second
            sample_rate = 44100
            samples_per_frame = buffer_size

            audio_data = []
            for i in range(samples_per_frame):
                sample_index = (self.frame_count * samples_per_frame + i)
                time_s = sample_index / sample_rate

                # Create a kick drum-like pattern
                beat_phase = (time_s * beat_frequency) % 1.0
                if beat_phase < 0.1:  # 10% of beat cycle
                    envelope = (0.1 - beat_phase) / 0.1  # Decay envelope
                    amplitude = self.audio_level * 32767 * envelope
                    # Low frequency sine for kick
                    sample = amplitude * math.sin(2 * math.pi * 60 * time_s)
                else:
                    sample = 0.0

                audio_data.append(sample)

            self.audio_in = audio_data

        else:
            # Fallback for 'file' mode (before browser audio arrives) or unknown types
            # Generate a sine wave so modes have audio to react to
            sample_rate = 44100
            samples_per_frame = buffer_size
            amplitude = self.audio_level * 32767
            audio_data = []
            for i in range(samples_per_frame):
                sample_index = (self.frame_count * samples_per_frame + i)
                time_s = sample_index / sample_rate
                sample = amplitude * math.sin(2 * math.pi * self.audio_frequency * time_s)
                audio_data.append(sample)
            self.audio_in = audio_data

        # Copy to stereo channels (all aliases)
        self.audio_left = self.audio_in[:]
        self.audio_right = self.audio_in[:]
        self.audio_in_r = self.audio_in[:]  # Real Eyesy naming

        # Calculate peak levels
        if self.audio_in:
            self.audio_peak = abs(max(self.audio_in, key=abs)) / 32767.0
            self.audio_peak_r = self.audio_peak  # Same for mono simulation

        # Update trigger based on audio level
        if self.audio_in:
            current_level = self.audio_peak
            self.audio_trig = current_level > 0.3  # Trigger threshold
        else:
            self.audio_trig = False

        # Update trig alias
        self.trig = self.audio_trig

class EyesyEngine:
    def __init__(self):
        self.screen = Surface((1280, 720))
        self.etc = EtcObject()
        self.current_mode = None
        self.setup_func = None
        self.draw_func = None
        self.is_initialized = False

        # Global knob values (0.0 to 1.0)
        self.knob_values = {
            'knob1': 0.5,
            'knob2': 0.5,
            'knob3': 0.5,
            'knob4': 0.5,
            'knob5': 0.5
        }

    def set_knob_value(self, knob_num, value):
        """Set knob value (1-5, value 0.0-1.0)"""
        if 1 <= knob_num <= 5:
            self.knob_values[f'knob{knob_num}'] = max(0.0, min(1.0, value))
            # Immediately update the etc object and module globals
            self.update_knobs_in_mode()

    def load_mode(self, mode_path):
        """Load an Eyesy mode from a directory containing main.py"""
        try:
            main_py_path = os.path.join(mode_path, 'main.py')
            if not os.path.exists(main_py_path):
                raise FileNotFoundError(f"main.py not found in {mode_path}")

            # Load the module
            spec = importlib.util.spec_from_file_location("eyesy_mode", main_py_path)
            module = importlib.util.module_from_spec(spec)

            # Add our pygame shim and knob values to the module's globals
            module.pygame = pygame
            module.screen = self.screen
            module.etc = self.etc
            # Add eyesy module (same as etc for compatibility)
            module.eyesy = self.etc
            # Also add math module which is commonly used
            import math
            module.math = math
            for knob, value in self.knob_values.items():
                setattr(module, knob, value)

            # Intercept pygame imports by adding pygame to sys.modules temporarily
            import sys
            original_pygame = sys.modules.get('pygame')
            sys.modules['pygame'] = pygame

            try:
                # Execute the module
                spec.loader.exec_module(module)
            finally:
                # Restore original pygame module (or remove if it wasn't there)
                if original_pygame is not None:
                    sys.modules['pygame'] = original_pygame
                else:
                    sys.modules.pop('pygame', None)

            # Get the required functions
            if hasattr(module, 'setup'):
                self.setup_func = module.setup
            else:
                self.setup_func = None

            if hasattr(module, 'draw'):
                self.draw_func = module.draw
            else:
                raise AttributeError("Mode must have a 'draw' function")

            self.current_mode = module
            mode_name = os.path.basename(mode_path)
            # Handle temp uploaded modes
            if mode_name.startswith('uploaded_'):
                mode_name = mode_name[9:]  # Remove 'uploaded_' prefix
            self.etc.mode = mode_name
            self.is_initialized = False

            return True, f"Mode '{self.etc.mode}' loaded successfully"

        except Exception as e:
            error_msg = f"Error loading mode: {str(e)}\n{traceback.format_exc()}"
            return False, error_msg

    def update_knobs_in_mode(self):
        """Update knob values in the current mode's globals and etc object"""
        if self.current_mode:
            for knob, value in self.knob_values.items():
                setattr(self.current_mode, knob, value)
                # Also update the etc object knob values
                setattr(self.etc, knob, value)

    def render_frame(self):
        """Render one frame and return as base64 image"""
        try:
            if not self.draw_func:
                return None, "No mode loaded"

            # Update knob values in the mode and etc object
            self.update_knobs_in_mode()

            # Generate audio data for this frame
            # In 'file' mode, skip only once browser is actually streaming audio data
            if self.etc.audio_type == 'file' and self.etc._file_audio_received:
                pass  # Using live audio from browser
            else:
                self.etc.generate_audio_data()

            # Run setup if this is the first frame
            if not self.is_initialized and self.setup_func:
                self.setup_func(self.screen, self.etc)
                self.is_initialized = True

            # Let the script handle background color based on knobs
            # But ensure screen is cleared if script doesn't do it

            # Render frame
            self.draw_func(self.screen, self.etc)

            # Convert to base64 image (JPEG is ~10x faster than PNG for 1280x720)
            img = self.screen.get_image()
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_data = buffer.getvalue()
            img_base64 = base64.b64encode(img_data).decode('utf-8')

            return f"data:image/jpeg;base64,{img_base64}", None

        except Exception as e:
            error_msg = f"Error rendering frame: {str(e)}\n{traceback.format_exc()}"
            return None, error_msg

    def set_audio_data(self, audio_data):
        """Set audio data for the mode to use

        Audio data comes from Web Audio API's getByteTimeDomainData
        which gives values 0-255 where 128 is silence.
        We convert to signed values centered at 0.

        Real Eyesy uses 100-sample buffers, so we downsample if needed.
        """
        if isinstance(audio_data, list) and len(audio_data) > 0:
            self.etc._file_audio_received = True
            buffer_size = 100  # Match real Eyesy buffer size

            # Convert from 0-255 (128 = silence) to signed range
            # Scale to roughly match what modes expect (16-bit audio style)
            # Downsample to 100 samples
            step = max(1, len(audio_data) // buffer_size)
            converted = []
            for i in range(buffer_size):
                idx = i * step
                if idx < len(audio_data):
                    # Convert 0-255 to -128 to 127, then scale to larger range
                    signed = (audio_data[idx] - 128) * 256  # Now -32768 to 32512
                    converted.append(signed)
                else:
                    converted.append(0.0)

            self.etc.audio_in = converted
            # For stereo, duplicate mono for now
            self.etc.audio_left = self.etc.audio_in[:]
            self.etc.audio_right = self.etc.audio_in[:]
            self.etc.audio_in_r = self.etc.audio_in[:]  # Real Eyesy naming

            # Calculate peak levels and trigger
            if self.etc.audio_in:
                self.etc.audio_peak = abs(max(self.etc.audio_in, key=abs)) / 32768.0
                self.etc.audio_peak_r = self.etc.audio_peak
                self.etc.audio_trig = self.etc.audio_peak > 0.1  # Lower threshold for file audio

            # Update trig alias
            self.etc.trig = self.etc.audio_trig

    def set_audio_simulation(self, audio_type="sine", level=0.5, frequency=440.0):
        """Configure audio simulation

        Args:
            audio_type: "sine", "noise", "beat", "silence", or "file"
            level: Audio level 0.0 to 1.0
            frequency: Frequency in Hz (for sine wave)
        """
        self.etc.audio_type = audio_type
        self.etc.audio_level = max(0.0, min(1.0, level))
        self.etc.audio_frequency = frequency

        # Reset file audio tracking when switching modes
        if audio_type == 'file':
            self.etc._file_audio_received = False

        buffer_size = 100  # Match real Eyesy buffer size

        # When switching to file mode, we'll receive data via set_audio_data
        # When switching away from file mode, clear any stale file audio
        if audio_type != 'file':
            # Reset to silence if no audio simulation
            if audio_type == 'silence':
                self.etc.audio_in = [0.0] * buffer_size
                self.etc.audio_left = [0.0] * buffer_size
                self.etc.audio_right = [0.0] * buffer_size
                self.etc.audio_in_r = [0.0] * buffer_size

    def get_status(self):
        """Get current engine status"""
        return {
            'mode_loaded': self.current_mode is not None,
            'current_mode': self.etc.mode,
            'knobs': self.knob_values,
            'resolution': (1280, 720)
        }