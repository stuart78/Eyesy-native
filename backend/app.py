"""
Flask app for Eyesy Python Simulator
"""

import os
import sys
import time
import argparse
import threading
from flask import Flask, render_template, request, Response, jsonify
import requests
from flask_socketio import SocketIO, emit
from eyesy_engine import EyesyEngine

# Import configuration
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import config

# ─── Path Resolution ────────────────────────────────────────────────────────────
# Detect if running inside a packaged Electron app
IS_ELECTRON = os.environ.get('ELECTRON_APP') == '1'

def resolve_project_root():
    """Resolve the project root, accounting for Electron packaging."""
    if IS_ELECTRON:
        # When packaged, resources are in process.resourcesPath
        # The backend/ dir is at <resourcesPath>/backend/
        # So project root equivalent is <resourcesPath>/
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.dirname(backend_dir)
    else:
        # Standard dev: project root is parent of backend/
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = resolve_project_root()

# Default modes dir - can be overridden by --modes-dir CLI arg
MODES_DIR = os.path.join(PROJECT_ROOT, 'modes')

# Resolve template and static paths
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'templates')
STATIC_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'static')

app = Flask(__name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR
)

# Configure app based on environment
config_name = 'production' if IS_ELECTRON else os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

cors_origins = "http://127.0.0.1:*" if IS_ELECTRON else "*"
socketio = SocketIO(app, cors_allowed_origins=cors_origins, async_mode='threading')

# Global engine instance
engine = EyesyEngine()
is_running = False
render_thread = None

@app.route('/')
def index():
    """Serve the main interface"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint for Electron startup polling"""
    return jsonify({'status': 'ok'}), 200

@app.route('/set-modes-dir', methods=['POST'])
def set_modes_dir():
    """Update the modes directory at runtime (called from Electron menu)"""
    global MODES_DIR
    data = request.get_json()
    new_dir = data.get('modes_dir')
    if new_dir and os.path.isdir(new_dir):
        MODES_DIR = new_dir
        print(f"Modes directory updated to: {MODES_DIR}")
        # Notify connected clients to refresh their mode list
        socketio.emit('status', {'message': f'Modes folder changed to: {os.path.basename(MODES_DIR)}', 'type': 'success'})
        # Automatically send updated modes list
        modes = []
        for item in os.listdir(MODES_DIR):
            mode_path = os.path.join(MODES_DIR, item)
            if os.path.isdir(mode_path) and os.path.exists(os.path.join(mode_path, 'main.py')):
                modes.append({'name': item, 'path': item})
        socketio.emit('modes_list', {'modes': modes})
        return jsonify({'status': 'ok'}), 200
    return jsonify({'status': 'error', 'message': 'Invalid directory'}), 400

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to Eyesy simulator', 'type': 'success'})
    # Send current rendering state so client can sync button states
    emit('rendering_state', {'is_running': is_running})

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
    # Broadcast to all clients so they sync their button states
    socketio.emit('rendering_state', {'is_running': True})

@socketio.on('stop_rendering')
def handle_stop_rendering():
    """Stop the rendering loop"""
    global is_running

    is_running = False
    emit('status', {'message': 'Rendering stopped', 'type': 'info'})
    # Broadcast to all clients so they sync their button states
    socketio.emit('rendering_state', {'is_running': False})

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

@app.route('/proxy/stream')
def proxy_stream():
    """Proxy audio streams to bypass CORS restrictions"""
    stream_url = request.args.get('url')
    if not stream_url:
        return Response('Missing url parameter', status=400)

    # Validate URL (basic security check)
    if not stream_url.startswith(('http://', 'https://')):
        return Response('Invalid URL', status=400)

    try:
        # Stream the audio with appropriate headers
        req = requests.get(stream_url, stream=True, timeout=10, headers={
            'User-Agent': 'EyesySimulator/1.0'
        })

        # Get content type from upstream
        content_type = req.headers.get('Content-Type', 'audio/mpeg')

        def generate():
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        return Response(
            generate(),
            content_type=content_type,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache'
            }
        )
    except requests.exceptions.Timeout:
        return Response('Stream connection timeout', status=504)
    except requests.exceptions.RequestException as e:
        print(f"Stream proxy error: {e}")
        return Response(f'Failed to connect to stream: {str(e)}', status=502)

def render_loop():
    """Main rendering loop that runs in a separate thread"""
    global is_running

    target_fps = 30
    frame_time = 1.0 / target_fps
    frame_count = 0
    error_count = 0
    max_consecutive_errors = 10

    print("Render loop started")

    while is_running:
        start_time = time.time()

        try:
            # Render frame
            image_data, error = engine.render_frame()

            if image_data:
                socketio.emit('frame', {'image': image_data})
                frame_count += 1
                error_count = 0  # Reset error count on success
                if frame_count % 30 == 0:
                    print(f"Rendered {frame_count} frames")
            elif error:
                error_count += 1
                print(f"Render error ({error_count}): {error}")
                if error_count >= max_consecutive_errors:
                    print(f"Too many consecutive errors, stopping render loop")
                    socketio.emit('status', {'message': f'Stopped after {max_consecutive_errors} errors: {error}', 'type': 'error'})
                    is_running = False

        except Exception as e:
            error_count += 1
            print(f"Exception in render loop ({error_count}): {e}")
            import traceback
            traceback.print_exc()
            if error_count >= max_consecutive_errors:
                print(f"Too many consecutive exceptions, stopping render loop")
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
    parser = argparse.ArgumentParser(description='EYESY Python Simulator')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5001)),
                        help='Port to run the server on')
    parser.add_argument('--host', type=str, default=os.environ.get('HOST', '0.0.0.0'),
                        help='Host to bind to')
    parser.add_argument('--modes-dir', type=str, default=None,
                        help='Path to the EYESY modes directory')
    args = parser.parse_args()

    # Override modes directory if provided
    if args.modes_dir and os.path.isdir(args.modes_dir):
        MODES_DIR = args.modes_dir
        print(f"Using modes directory: {MODES_DIR}")

    print("Starting Eyesy Python Simulator...")

    # In Electron mode, always run without debug
    if IS_ELECTRON:
        print(f"Electron mode: http://127.0.0.1:{args.port}")
        socketio.run(app, host=args.host, port=args.port, debug=False)
    elif app.config['DEBUG']:
        print(f"Development mode: http://localhost:{args.port}")
        socketio.run(app, host=args.host, port=args.port, debug=True, allow_unsafe_werkzeug=True)
    else:
        print(f"Production mode: http://{args.host}:{args.port}")
        socketio.run(app, host=args.host, port=args.port, debug=False)