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

        // Audio playback
        this.audioContext = null;
        this.audioOscillator = null;
        this.audioGain = null;
        this.noiseNode = null;
        this.beatInterval = null;
        this.isAudioPlaying = false;
        this.audioFileBuffer = null;
        this.audioFileSource = null;
        this.audioAnalyser = null;
        this.audioDataInterval = null;

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

        // Setup audio controls
        this.setupAudioControls();
    }

    setupAudioControls() {
        const audioLevel = document.getElementById('audioLevel');
        const audioLevelValue = document.getElementById('audioLevelValue');
        const audioFreq = document.getElementById('audioFreq');
        const audioFreqValue = document.getElementById('audioFreqValue');
        const applyAudioBtn = document.getElementById('applyAudioBtn');

        // Update displayed values on slider change and update audio if playing
        audioLevel.addEventListener('input', () => {
            audioLevelValue.textContent = (audioLevel.value / 100).toFixed(2);
            // Update gain in real-time if audio is playing
            if (this.isAudioPlaying && this.audioGain) {
                this.audioGain.gain.value = (audioLevel.value / 100) * 0.3;
            }
        });

        audioFreq.addEventListener('input', () => {
            audioFreqValue.textContent = `${audioFreq.value} Hz`;
            // Update frequency in real-time if oscillator is playing
            if (this.isAudioPlaying && this.audioOscillator) {
                this.audioOscillator.frequency.value = parseInt(audioFreq.value);
            }
        });

        // Apply audio settings button
        applyAudioBtn.addEventListener('click', () => {
            this.applyAudioSettings();
        });

        // Also apply on type change for immediate feedback
        document.getElementById('audioType').addEventListener('change', () => {
            this.applyAudioSettings();
        });

        // Audio playback toggle
        const playAudioToggle = document.getElementById('playAudioToggle');
        if (playAudioToggle) {
            playAudioToggle.addEventListener('change', () => {
                this.toggleAudioPlayback();
            });
        }

        // Audio file controls
        const audioFileInput = document.getElementById('audioFileInput');
        const browseAudioBtn = document.getElementById('browseAudioBtn');
        const audioFileRow = document.getElementById('audioFileRow');

        // Show/hide file row based on audio type
        document.getElementById('audioType').addEventListener('change', (e) => {
            if (e.target.value === 'file') {
                audioFileRow.style.display = 'flex';
            } else {
                audioFileRow.style.display = 'none';
            }
        });

        browseAudioBtn.addEventListener('click', () => {
            audioFileInput.click();
        });

        audioFileInput.addEventListener('change', (e) => {
            this.handleAudioFileSelection(e);
        });
    }

    handleAudioFileSelection(event) {
        const file = event.target.files[0];
        const audioFileName = document.getElementById('audioFileName');

        if (file) {
            audioFileName.textContent = file.name;
            audioFileName.classList.add('has-file');

            // Load the audio file
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    this.initAudioContext();
                    this.audioFileBuffer = await this.audioContext.decodeAudioData(e.target.result);
                    this.setStatus(`Audio file "${file.name}" loaded successfully`, 'success');
                } catch (err) {
                    this.setStatus(`Error loading audio file: ${err.message}`, 'error');
                    this.audioFileBuffer = null;
                }
            };
            reader.readAsArrayBuffer(file);
        } else {
            audioFileName.textContent = 'No file selected';
            audioFileName.classList.remove('has-file');
            this.audioFileBuffer = null;
        }
    }

    applyAudioSettings() {
        if (this.socket && this.socket.connected) {
            const audioType = document.getElementById('audioType').value;
            const audioLevel = document.getElementById('audioLevel').value / 100;
            const audioFreq = parseInt(document.getElementById('audioFreq').value);

            this.socket.emit('set_audio', {
                type: audioType,
                level: audioLevel,
                frequency: audioFreq
            });

            // Update browser audio playback if enabled
            const playAudio = document.getElementById('playAudioToggle')?.checked;
            if (playAudio) {
                this.updateAudioPlayback(audioType, audioLevel, audioFreq);
            }

            this.setStatus(`Audio: ${audioType} (level: ${audioLevel.toFixed(2)}, freq: ${audioFreq}Hz)`, 'info');
        }
    }

    initAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
    }

    stopAudioPlayback() {
        if (this.audioOscillator) {
            this.audioOscillator.stop();
            this.audioOscillator.disconnect();
            this.audioOscillator = null;
        }
        if (this.audioGain) {
            this.audioGain.disconnect();
            this.audioGain = null;
        }
        if (this.noiseNode) {
            this.noiseNode.stop();
            this.noiseNode.disconnect();
            this.noiseNode = null;
        }
        if (this.beatInterval) {
            clearInterval(this.beatInterval);
            this.beatInterval = null;
        }
        if (this.audioFileSource) {
            this.audioFileSource.stop();
            this.audioFileSource.disconnect();
            this.audioFileSource = null;
        }
        if (this.audioAnalyser) {
            this.audioAnalyser.disconnect();
            this.audioAnalyser = null;
        }
        if (this.audioDataInterval) {
            clearInterval(this.audioDataInterval);
            this.audioDataInterval = null;
        }
        this.isAudioPlaying = false;
    }

    createNoiseNode(audioContext) {
        // Create white noise using a buffer
        const bufferSize = audioContext.sampleRate * 2; // 2 seconds of noise
        const noiseBuffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate);
        const output = noiseBuffer.getChannelData(0);

        for (let i = 0; i < bufferSize; i++) {
            output[i] = Math.random() * 2 - 1;
        }

        const noiseNode = audioContext.createBufferSource();
        noiseNode.buffer = noiseBuffer;
        noiseNode.loop = true;
        return noiseNode;
    }

    updateAudioPlayback(audioType, level, frequency) {
        this.stopAudioPlayback();

        if (audioType === 'silence' || level === 0) {
            return;
        }

        this.initAudioContext();
        const ctx = this.audioContext;

        // Create gain node for volume control
        this.audioGain = ctx.createGain();
        this.audioGain.gain.value = level * 0.3; // Scale down to avoid being too loud
        this.audioGain.connect(ctx.destination);

        if (audioType === 'sine') {
            // Sine wave oscillator
            this.audioOscillator = ctx.createOscillator();
            this.audioOscillator.type = 'sine';
            this.audioOscillator.frequency.value = frequency;
            this.audioOscillator.connect(this.audioGain);
            this.audioOscillator.start();

        } else if (audioType === 'noise') {
            // White noise
            this.noiseNode = this.createNoiseNode(ctx);
            this.noiseNode.connect(this.audioGain);
            this.noiseNode.start();

        } else if (audioType === 'beat') {
            // Beat/kick - short burst every ~500ms
            const playBeat = () => {
                const osc = ctx.createOscillator();
                const beatGain = ctx.createGain();

                osc.type = 'sine';
                osc.frequency.value = 80; // Low kick frequency

                beatGain.gain.setValueAtTime(level * 0.5, ctx.currentTime);
                beatGain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);

                osc.connect(beatGain);
                beatGain.connect(ctx.destination);

                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.15);
            };

            playBeat(); // Play immediately
            this.beatInterval = setInterval(playBeat, 500); // Repeat every 500ms

        } else if (audioType === 'file') {
            // Play loaded audio file
            if (!this.audioFileBuffer) {
                this.setStatus('No audio file loaded. Please select a file first.', 'error');
                return;
            }

            // Create buffer source for the audio file
            this.audioFileSource = ctx.createBufferSource();
            this.audioFileSource.buffer = this.audioFileBuffer;
            this.audioFileSource.loop = true;

            // Create analyser for extracting audio data
            this.audioAnalyser = ctx.createAnalyser();
            this.audioAnalyser.fftSize = 2048;  // Gives us 1024 time-domain samples

            // Connect: source -> analyser -> gain -> destination
            this.audioFileSource.connect(this.audioAnalyser);
            this.audioAnalyser.connect(this.audioGain);
            this.audioFileSource.start(0);

            // Start sending audio data to backend for visualization
            this.startAudioDataStream();

            this.setStatus('Playing audio file (streaming to visuals)...', 'info');
        }

        this.isAudioPlaying = true;
    }

    toggleAudioPlayback() {
        const playAudio = document.getElementById('playAudioToggle')?.checked;

        if (playAudio) {
            const audioType = document.getElementById('audioType').value;
            const audioLevel = document.getElementById('audioLevel').value / 100;
            const audioFreq = parseInt(document.getElementById('audioFreq').value);
            this.updateAudioPlayback(audioType, audioLevel, audioFreq);
        } else {
            this.stopAudioPlayback();
        }
    }

    startAudioDataStream() {
        // Stop any existing stream
        if (this.audioDataInterval) {
            clearInterval(this.audioDataInterval);
        }

        // Send audio data to backend at ~30fps (matching render rate)
        const dataArray = new Uint8Array(this.audioAnalyser.frequencyBinCount);

        this.audioDataInterval = setInterval(() => {
            if (this.audioAnalyser && this.socket && this.socket.connected) {
                // Get time-domain data (waveform)
                this.audioAnalyser.getByteTimeDomainData(dataArray);

                // Convert Uint8Array to regular array and send to backend
                // Values are 0-255 where 128 is silence
                const samples = Array.from(dataArray);

                this.socket.emit('audio_data', { samples: samples });
            }
        }, 33);  // ~30fps
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