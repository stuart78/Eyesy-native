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
        this.beatGainNode = null;
        this.isAudioPlaying = false;
        this.isAudioSimulationOn = false;
        this.audioFileBuffer = null;
        this.audioFileSource = null;
        this.audioAnalyser = null;
        this.audioDataInterval = null;
        this.audioStreamElement = null;
        this.audioStreamSource = null;

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

        // Setup panel collapse
        this.setupPanelCollapse();

        // Setup preview size display
        this.setupPreviewSizeDisplay();
    }

    setupPanelCollapse() {
        const collapseBtn = document.getElementById('collapseBtn');
        const controlsPanel = document.getElementById('controlsPanel');

        if (collapseBtn && controlsPanel) {
            collapseBtn.addEventListener('click', () => {
                controlsPanel.classList.toggle('collapsed');
                collapseBtn.textContent = controlsPanel.classList.contains('collapsed') ? '+' : '−';
                collapseBtn.title = controlsPanel.classList.contains('collapsed') ? 'Expand panel' : 'Collapse panel';
                // Update preview size after collapse animation
                setTimeout(() => this.updatePreviewSize(), 50);
            });
        }
    }

    setupPreviewSizeDisplay() {
        // Update on window resize
        window.addEventListener('resize', () => this.updatePreviewSize());
        // Initial update
        this.updatePreviewSize();
    }

    updatePreviewSize() {
        const previewSizeElement = document.getElementById('previewSize');
        if (previewSizeElement && this.canvas) {
            const rect = this.canvas.getBoundingClientRect();
            const width = Math.round(rect.width);
            const height = Math.round(rect.height);
            previewSizeElement.textContent = `${width}x${height}`;
        }
    }

    setupAudioControls() {
        const audioLevel = document.getElementById('audioLevel');
        const audioLevelValue = document.getElementById('audioLevelValue');
        const audioFreq = document.getElementById('audioFreq');
        const audioFreqValue = document.getElementById('audioFreqValue');
        const applyAudioBtn = document.getElementById('applyAudioBtn');

        // Update displayed values on slider change and auto-apply if simulation is on
        audioLevel.addEventListener('input', () => {
            audioLevelValue.textContent = (audioLevel.value / 100).toFixed(2);
            // Update gain in real-time if audio is playing
            if (this.isAudioPlaying && this.audioGain) {
                this.audioGain.gain.value = (audioLevel.value / 100) * 0.3;
            }
            // Auto-apply if simulation is on
            if (this.isAudioSimulationOn) {
                this.applyAudioSettings();
            }
        });

        audioFreq.addEventListener('input', () => {
            audioFreqValue.textContent = `${audioFreq.value} Hz`;
            // Update frequency in real-time if oscillator is playing
            if (this.isAudioPlaying && this.audioOscillator) {
                this.audioOscillator.frequency.value = parseInt(audioFreq.value);
            }
            // Auto-apply if simulation is on
            if (this.isAudioSimulationOn) {
                this.applyAudioSettings();
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

        // Audio playback toggle (checkbox)
        const playAudioToggle = document.getElementById('playAudioToggle');
        if (playAudioToggle) {
            playAudioToggle.addEventListener('change', () => {
                this.toggleAudioPlayback();
                this.updateAudioPlayPauseButton();
            });
        }

        // Audio play/pause button
        const audioPlayPauseBtn = document.getElementById('audioPlayPauseBtn');
        if (audioPlayPauseBtn) {
            audioPlayPauseBtn.addEventListener('click', () => {
                this.toggleAudioSimulation();
            });
        }

        // Audio file controls
        const audioFileInput = document.getElementById('audioFileInput');
        const browseAudioBtn = document.getElementById('browseAudioBtn');
        const audioFileRow = document.getElementById('audioFileRow');
        const audioStreamRow = document.getElementById('audioStreamRow');
        const audioStreamUrlRow = document.getElementById('audioStreamUrlRow');
        const audioStreamPreset = document.getElementById('audioStreamPreset');

        // Show/hide file/stream row based on audio type
        const audioLevelRow = audioLevel.closest('.audio-row');
        const audioFreqRow = audioFreq.closest('.audio-row');

        document.getElementById('audioType').addEventListener('change', (e) => {
            const type = e.target.value;
            const isStream = type === 'stream';
            const isFile = type === 'file';
            // Frequency only applies to sine wave
            const freqDisabled = type !== 'sine';
            // Level doesn't apply to stream or file (file has its own volume)
            const levelDisabled = isStream || isFile;

            audioFileRow.style.display = isFile ? 'flex' : 'none';
            audioStreamRow.style.display = isStream ? 'flex' : 'none';
            // Show custom URL row only if stream selected and preset is "Custom URL..."
            audioStreamUrlRow.style.display = (isStream && !audioStreamPreset.value) ? 'flex' : 'none';

            // Disable controls that don't apply to current type
            audioLevel.disabled = levelDisabled;
            audioFreq.disabled = freqDisabled;
            audioLevelRow.style.opacity = levelDisabled ? '0.5' : '1';
            audioFreqRow.style.opacity = freqDisabled ? '0.5' : '1';
        });

        // Show/hide custom URL input based on preset selection
        audioStreamPreset.addEventListener('change', (e) => {
            audioStreamUrlRow.style.display = e.target.value === '' ? 'flex' : 'none';
            // Auto-switch stream when a preset station is selected
            if (e.target.value && this.isAudioSimulationOn) {
                this.applyAudioSettings();
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

            // For beat mode, we stream a real audio file, so tell backend to use 'file' mode
            // This ensures the backend uses our streamed audio data instead of synthesizing its own
            const backendType = (audioType === 'beat') ? 'file' : audioType;

            this.socket.emit('set_audio', {
                type: backendType,
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

    toggleAudioSimulation() {
        this.isAudioSimulationOn = !this.isAudioSimulationOn;

        if (this.isAudioSimulationOn) {
            // Turn on audio simulation - apply current settings
            this.applyAudioSettings();
        } else {
            // Turn off audio simulation - set to silence on backend
            if (this.socket && this.socket.connected) {
                this.socket.emit('set_audio', {
                    type: 'silence',
                    level: 0,
                    frequency: 440
                });
            }
            // Stop browser audio playback (but don't change the checkbox)
            this.stopAudioPlayback();
        }

        this.updateAudioPlayPauseButton();
    }

    updateAudioPlayPauseButton() {
        const btn = document.getElementById('audioPlayPauseBtn');
        if (!btn) return;

        const isPlaying = this.isAudioSimulationOn || this.isAudioPlaying;

        if (isPlaying) {
            btn.innerHTML = '&#10074;&#10074;'; // Pause symbol (two vertical bars)
            btn.title = 'Pause audio';
            btn.classList.add('playing');
        } else {
            btn.innerHTML = '&#9654;'; // Play symbol (triangle)
            btn.title = 'Play audio';
            btn.classList.remove('playing');
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
        if (this.beatGainNode) {
            this.beatGainNode.disconnect();
            this.beatGainNode = null;
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
        if (this.audioStreamElement) {
            this.audioStreamElement.pause();
            this.audioStreamElement.src = '';
            this.audioStreamElement = null;
        }
        if (this.audioStreamSource) {
            this.audioStreamSource.disconnect();
            this.audioStreamSource = null;
        }
        this.isAudioPlaying = false;
        this.isAudioSimulationOn = false;
        this.updateAudioPlayPauseButton();
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

    async loadBeatSample(ctx, level) {
        try {
            // Fetch the beat sample from static files
            const response = await fetch('/static/audio/kickTom.mp3');
            if (!response.ok) {
                throw new Error(`Failed to load beat sample: ${response.status}`);
            }
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

            // Create looping buffer source
            this.audioFileSource = ctx.createBufferSource();
            this.audioFileSource.buffer = audioBuffer;
            this.audioFileSource.loop = true;

            // Connect through analyser (same path as audio file)
            this.audioFileSource.connect(this.audioAnalyser);
            this.audioFileSource.start(0);

            // Start sending audio data to backend for visualization
            this.startAudioDataStream();

            this.isAudioPlaying = true;
            this.isAudioSimulationOn = true;
            this.updateAudioPlayPauseButton();

            this.setStatus('Playing beat sample (looping)', 'info');
        } catch (err) {
            this.setStatus(`Error loading beat sample: ${err.message}`, 'error');
            console.error('Beat sample load error:', err);
        }
    }

    updateAudioPlayback(audioType, level, frequency) {
        this.stopAudioPlayback();

        if (audioType === 'silence' || level === 0) {
            // Already stopped, button updated by stopAudioPlayback
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
            // Create analyser for extracting audio data for visualization
            this.audioAnalyser = ctx.createAnalyser();
            this.audioAnalyser.fftSize = 2048;
            this.audioAnalyser.connect(this.audioGain);

            this.audioOscillator = ctx.createOscillator();
            this.audioOscillator.type = 'sine';
            this.audioOscillator.frequency.value = frequency;
            this.audioOscillator.connect(this.audioAnalyser);
            this.audioOscillator.start();

            // Start sending audio data to backend for visualization
            this.startAudioDataStream();

        } else if (audioType === 'noise') {
            // White noise
            // Create analyser for extracting audio data for visualization
            this.audioAnalyser = ctx.createAnalyser();
            this.audioAnalyser.fftSize = 2048;
            this.audioAnalyser.connect(this.audioGain);

            this.noiseNode = this.createNoiseNode(ctx);
            this.noiseNode.connect(this.audioAnalyser);
            this.noiseNode.start();

            // Start sending audio data to backend for visualization
            this.startAudioDataStream();

        } else if (audioType === 'beat') {
            // Beat/kick - load the beat sample file and loop it
            // This uses the same reliable path as audio file playback
            this.audioAnalyser = ctx.createAnalyser();
            this.audioAnalyser.fftSize = 2048;
            this.audioAnalyser.connect(this.audioGain);

            // Load the beat sample
            this.loadBeatSample(ctx, level);
            return; // loadBeatSample handles the rest asynchronously

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

        } else if (audioType === 'stream') {
            // Play internet radio stream via backend proxy
            const presetUrl = document.getElementById('audioStreamPreset')?.value;
            const customUrl = document.getElementById('audioStreamUrl')?.value;
            const streamUrl = presetUrl || customUrl;
            if (!streamUrl) {
                this.setStatus('Please select a station or enter a stream URL.', 'error');
                return;
            }

            this.setStatus(`Connecting to stream...`, 'info');

            // Use backend proxy to avoid CORS issues
            const proxyUrl = `/proxy/stream?url=${encodeURIComponent(streamUrl)}`;

            // Create audio element for the stream
            this.audioStreamElement = new Audio();

            // Handle successful load
            this.audioStreamElement.oncanplay = () => {
                this.audioStreamElement.play().then(() => {
                    // Extract station name from URL for display
                    const stationName = streamUrl.split('/').pop().replace(/-/g, ' ');
                    this.setStatus(`Playing: ${stationName}`, 'info');

                    // Try to connect to Web Audio API for visualization
                    try {
                        this.initAudioContext();
                        if (!this.audioStreamSource) {
                            this.audioStreamSource = this.audioContext.createMediaElementSource(this.audioStreamElement);
                            this.audioAnalyser = this.audioContext.createAnalyser();
                            this.audioAnalyser.fftSize = 2048;
                            this.audioStreamSource.connect(this.audioAnalyser);
                            this.audioAnalyser.connect(this.audioContext.destination);
                            this.startAudioDataStream();
                        }
                    } catch (err) {
                        console.log('Could not connect stream to analyser:', err);
                    }
                }).catch(err => {
                    this.setStatus(`Playback error: ${err.message}`, 'error');
                });
            };

            // Handle load errors
            this.audioStreamElement.onerror = (e) => {
                const error = this.audioStreamElement.error;
                console.error('Audio stream error:', error);
                this.setStatus(`Stream error: ${error?.message || 'Failed to load stream'}`, 'error');
            };

            // Start loading via proxy
            this.audioStreamElement.src = proxyUrl;
            this.audioStreamElement.load();
        }

        this.isAudioPlaying = true;
        this.isAudioSimulationOn = true;
        this.updateAudioPlayPauseButton();
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