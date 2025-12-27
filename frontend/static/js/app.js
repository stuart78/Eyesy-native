// Eyesy Python Simulator Frontend

class EyesySimulator {
    constructor() {
        this.socket = null;
        this.canvas = document.getElementById('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.isRunning = false;
        this.fpsCounter = 0;
        this.lastFpsTime = Date.now();
        this.frameSequence = 0;  // Track frame order to prevent race conditions
        this.lastRenderedFrame = -1;  // Track last successfully rendered frame
        this.knobThrottleTimers = {};  // Throttle knob updates

        this.initializeSocket();
        this.setupControls();
    }

    initializeSocket() {
        console.log('Initializing socket...');
        this.socket = io({
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true
        });

        this.socket.on('connect', () => {
            console.log('Connected to server, transport:', this.socket.io.engine.transport.name);
            this.updateConnectionStatus(true);
            this.setStatus('Connected to Eyesy simulator', 'success');
            this.loadModes();
        });

        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from server:', reason);
            this.updateConnectionStatus(false);
            this.setStatus(`Disconnected from server: ${reason}`, 'error');
        });

        this.socket.on('reconnect', () => {
            console.log('Reconnected to server');
            this.updateConnectionStatus(true);
            this.setStatus('Reconnected to server', 'success');
        });

        this.socket.on('reconnect_attempt', () => {
            console.log('Attempting to reconnect...');
            this.setStatus('Attempting to reconnect...', 'info');
        });

        this.socket.on('status', (data) => {
            this.setStatus(data.message, data.type);
        });

        this.socket.on('frame', (data) => {
            this.displayFrame(data.image);
            this.updateFPS();
        });

        this.socket.on('modes_list', (data) => {
            this.populateModeSelector(data.modes);
        });
    }

    setupControls() {
        // Setup knob controls
        for (let i = 1; i <= 5; i++) {
            const slider = document.getElementById(`knob${i}`);
            const valueDisplay = slider.parentElement.querySelector('.value');

            slider.addEventListener('input', () => {
                const value = slider.value / 100;
                valueDisplay.textContent = value.toFixed(2);
                this.sendKnobChange(i, value);
            });
        }

        // Setup buttons
        document.getElementById('startBtn').addEventListener('click', () => {
            this.startRendering();
        });

        document.getElementById('stopBtn').addEventListener('click', () => {
            this.stopRendering();
        });

        document.getElementById('loadModeBtn').addEventListener('click', () => {
            this.loadSelectedMode();
        });

        document.getElementById('refreshModesBtn').addEventListener('click', () => {
            this.loadModes();
        });

        // Setup file browser
        document.getElementById('browseFileBtn').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });

        document.getElementById('fileInput').addEventListener('change', (event) => {
            this.handleFileSelection(event);
        });

        document.getElementById('loadFileBtn').addEventListener('click', () => {
            this.loadSelectedFile();
        });
    }

    sendKnobChange(knobNum, value) {
        if (this.socket && this.socket.connected) {
            // Clear any existing timer for this knob
            if (this.knobThrottleTimers[knobNum]) {
                clearTimeout(this.knobThrottleTimers[knobNum]);
            }

            // Send immediately, then throttle subsequent changes
            this.socket.emit('knob_change', {
                knob: knobNum,
                value: value
            });

            // Set a small throttle to prevent overwhelming the server
            this.knobThrottleTimers[knobNum] = setTimeout(() => {
                delete this.knobThrottleTimers[knobNum];
            }, 16); // ~60fps throttle
        }
    }

    startRendering() {
        if (this.socket && this.socket.connected) {
            this.socket.emit('start_rendering');
            this.isRunning = true;
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
        }
    }

    stopRendering() {
        if (this.socket && this.socket.connected) {
            this.socket.emit('stop_rendering');
            this.isRunning = false;
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }
    }

    loadSelectedMode() {
        const select = document.getElementById('modeSelect');
        const selectedMode = select.value;
        console.log('loadSelectedMode called, selectedMode:', selectedMode);

        if (!selectedMode) {
            this.setStatus('Please select a mode first', 'error');
            return;
        }

        if (this.socket && this.socket.connected) {
            console.log('Emitting load_mode event with path:', selectedMode);
            this.socket.emit('load_mode', {
                path: selectedMode
            });
        } else {
            console.log('Socket not connected:', this.socket?.connected);
        }
    }

    loadModes() {
        if (this.socket && this.socket.connected) {
            this.socket.emit('get_modes');
            this.setStatus('Loading available modes...', 'info');
        }
    }

    populateModeSelector(modes) {
        const select = document.getElementById('modeSelect');

        // Clear existing options except the first one
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }

        // Add mode options
        modes.forEach(mode => {
            const option = document.createElement('option');
            option.value = mode.path;
            option.textContent = mode.name;
            select.appendChild(option);
        });

        this.setStatus(`Found ${modes.length} modes`, 'info');
    }

    displayFrame(imageData) {
        // Assign a sequence number to this frame
        const currentFrame = ++this.frameSequence;

        const img = new Image();
        img.onload = () => {
            // Only render if this is the most recent frame (prevents out-of-order rendering)
            if (currentFrame > this.lastRenderedFrame) {
                // Clear canvas completely and draw the new frame
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
                this.lastRenderedFrame = currentFrame;
            }
        };

        // Set image source (base64 data doesn't need cache busting)
        img.src = imageData;
    }

    updateFPS() {
        this.fpsCounter++;
        const now = Date.now();

        if (now - this.lastFpsTime >= 1000) {
            document.getElementById('fps').textContent = `FPS: ${this.fpsCounter}`;
            this.fpsCounter = 0;
            this.lastFpsTime = now;
        }
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connection');
        if (connected) {
            indicator.className = 'connected';
            indicator.title = 'Connected';
        } else {
            indicator.className = '';
            indicator.title = 'Disconnected';
        }
    }

    handleFileSelection(event) {
        const file = event.target.files[0];
        const selectedFileElement = document.getElementById('selectedFile');
        const loadFileBtn = document.getElementById('loadFileBtn');

        if (file && file.name.endsWith('.py')) {
            selectedFileElement.textContent = file.name;
            selectedFileElement.className = 'selected-file has-file';
            loadFileBtn.disabled = false;
            this.selectedFile = file;
        } else if (file) {
            selectedFileElement.textContent = 'Please select a .py file';
            selectedFileElement.className = 'selected-file';
            loadFileBtn.disabled = true;
            this.selectedFile = null;
            this.setStatus('Please select a Python (.py) file', 'error');
        } else {
            selectedFileElement.textContent = 'No file selected';
            selectedFileElement.className = 'selected-file';
            loadFileBtn.disabled = true;
            this.selectedFile = null;
        }
    }

    loadSelectedFile() {
        if (!this.selectedFile) {
            this.setStatus('No file selected', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target.result;
            this.uploadModeContent(this.selectedFile.name, content);
        };
        reader.readAsText(this.selectedFile);
    }

    uploadModeContent(filename, content) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('load_mode_content', {
                filename: filename,
                content: content
            });
            this.setStatus(`Uploading ${filename}...`, 'info');
        }
    }

    setStatus(message, type = 'info') {
        const statusElement = document.getElementById('status');
        statusElement.textContent = message;
        statusElement.className = `status-${type}`;
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// Initialize the simulator when page loads
document.addEventListener('DOMContentLoaded', () => {
    const simulator = new EyesySimulator();
    window.eyesySimulator = simulator; // For debugging
});