"""
Flask app for Eyesy Python Simulator
"""

import os
import time
import threading
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from eyesy_engine import EyesyEngine

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import config

# Get project root directory (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODES_DIR = os.path.join(PROJECT_ROOT, 'modes')

app = Flask(__name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)

# Configure app based on environment
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global engine instance
engine = EyesyEngine()
is_running = False
render_thread = None

@app.route('/')
def index():
    """Serve the main interface"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to Eyesy simulator', 'type': 'success'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

@socketio.on('knob_change')
def handle_knob_change(data):
    """Handle knob value changes"""
    try:
        knob_num = data.get('knob')
        value = data.get('value')

        if knob_num and isinstance(value, (int, float)):
            engine.set_knob_value(knob_num, value)
            print(f"Knob {knob_num} set to {value:.2f}")

    except Exception as e:
        emit('status', {'message': f'Error setting knob: {str(e)}', 'type': 'error'})

@socketio.on('load_mode')
def handle_load_mode(data):
    """Load an Eyesy mode"""
    try:
        mode_path = data.get('path')
        print(f"Loading mode: {mode_path}")
        if not mode_path:
            emit('status', {'message': 'No mode path provided', 'type': 'error'})
            return

        # Convert relative path to absolute
        if not os.path.isabs(mode_path):
            mode_path = os.path.join(MODES_DIR, mode_path)

        print(f"Full path: {mode_path}")
        success, message = engine.load_mode(mode_path)
        print(f"Load result: {success}, {message}")

        if success:
            emit('status', {'message': message, 'type': 'success'})
            # Send an initial frame so user sees something immediately
            image_data, error = engine.render_frame()
            if image_data:
                emit('frame', {'image': image_data})
        else:
            emit('status', {'message': message, 'type': 'error'})

    except Exception as e:
        emit('status', {'message': f'Error loading mode: {str(e)}', 'type': 'error'})

@socketio.on('start_rendering')
def handle_start_rendering():
    """Start the rendering loop"""
    global is_running, render_thread

    if is_running:
        emit('status', {'message': 'Already running', 'type': 'info'})
        return

    is_running = True
    render_thread = threading.Thread(target=render_loop)
    render_thread.daemon = True
    render_thread.start()

    emit('status', {'message': 'Rendering started', 'type': 'success'})

@socketio.on('stop_rendering')
def handle_stop_rendering():
    """Stop the rendering loop"""
    global is_running

    is_running = False
    emit('status', {'message': 'Rendering stopped', 'type': 'info'})

@socketio.on('get_modes')
def handle_get_modes():
    """Get list of available modes"""
    try:
        modes_dir = MODES_DIR
        if not os.path.exists(modes_dir):
            emit('modes_list', {'modes': [], 'message': 'Modes directory not found'})
            return

        modes = []
        for item in os.listdir(modes_dir):
            mode_path = os.path.join(modes_dir, item)
            if os.path.isdir(mode_path) and os.path.exists(os.path.join(mode_path, 'main.py')):
                modes.append({
                    'name': item,
                    'path': item
                })

        emit('modes_list', {'modes': modes})

    except Exception as e:
        emit('status', {'message': f'Error getting modes: {str(e)}', 'type': 'error'})

@socketio.on('load_mode_content')
def handle_load_mode_content(data):
    """Load mode from uploaded file content"""
    try:
        filename = data.get('filename', 'uploaded_mode.py')
        content = data.get('content', '')

        if not content.strip():
            emit('status', {'message': 'File content is empty', 'type': 'error'})
            return

        # Create a temporary directory for the uploaded mode (outside source directory)
        import tempfile
        temp_base = tempfile.gettempdir()
        temp_dir = os.path.join(temp_base, 'eyesy_uploaded_modes')
        os.makedirs(temp_dir, exist_ok=True)

        # Create a unique directory name based on filename
        mode_name = os.path.splitext(filename)[0]
        mode_dir = os.path.join(temp_dir, f"uploaded_{mode_name}")
        os.makedirs(mode_dir, exist_ok=True)

        # Write the content to main.py
        main_py_path = os.path.join(mode_dir, 'main.py')
        with open(main_py_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Load the mode
        success, message = engine.load_mode(mode_dir)

        if success:
            emit('status', {'message': f'Uploaded mode "{filename}" loaded successfully', 'type': 'success'})
        else:
            emit('status', {'message': message, 'type': 'error'})

    except Exception as e:
        emit('status', {'message': f'Error loading uploaded mode: {str(e)}', 'type': 'error'})

@socketio.on('set_audio')
def handle_set_audio(data):
    """Configure audio simulation"""
    try:
        audio_type = data.get('type', 'sine')
        level = data.get('level', 0.5)
        frequency = data.get('frequency', 440.0)

        engine.set_audio_simulation(audio_type, level, frequency)
        emit('status', {'message': f'Audio set to {audio_type} (level: {level:.2f})', 'type': 'success'})

    except Exception as e:
        emit('status', {'message': f'Error setting audio: {str(e)}', 'type': 'error'})

@socketio.on('audio_data')
def handle_audio_data(data):
    """Receive raw audio data from the browser for visualization"""
    try:
        audio_samples = data.get('samples', [])
        if audio_samples:
            engine.set_audio_data(audio_samples)
    except Exception as e:
        print(f"Error processing audio data: {str(e)}")

def render_loop():
    """Main rendering loop that runs in a separate thread"""
    global is_running

    target_fps = 30
    frame_time = 1.0 / target_fps
    frame_count = 0

    print("Render loop started")

    while is_running:
        start_time = time.time()

        try:
            # Render frame
            image_data, error = engine.render_frame()

            if image_data:
                socketio.emit('frame', {'image': image_data})
                frame_count += 1
                if frame_count % 30 == 0:
                    print(f"Rendered {frame_count} frames")
            elif error:
                print(f"Render error: {error}")
                socketio.emit('status', {'message': error, 'type': 'error'})
                is_running = False

        except Exception as e:
            print(f"Exception in render loop: {e}")
            socketio.emit('status', {'message': f'Render error: {str(e)}', 'type': 'error'})
            is_running = False

        # Maintain target FPS
        elapsed = time.time() - start_time
        sleep_time = max(0, frame_time - elapsed)
        time.sleep(sleep_time)

    print("Render loop stopped")

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app.config.from_object(config[config_name])
    return app

if __name__ == '__main__':
    print("Starting Eyesy Python Simulator...")

    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')

    if app.config['DEBUG']:
        print(f"Development mode: http://localhost:{port}")
        socketio.run(app, host=host, port=port, debug=True, allow_unsafe_werkzeug=True)
    else:
        print(f"Production mode: http://{host}:{port}")
        socketio.run(app, host=host, port=port, debug=False)