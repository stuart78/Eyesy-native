const { app, BrowserWindow, Menu, dialog, shell, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const http = require('http');
const crypto = require('crypto');
const Store = require('electron-store');
const TelemetryDeck = require('@telemetrydeck/sdk');

const store = new Store({
    defaults: {
        modesDir: null,
        windowBounds: { width: 1400, height: 900 },
        telemetryUserId: null
    }
});

const isDev = process.env.ELECTRON_DEV === '1';

let mainWindow = null;
let pythonProcess = null;
let serverPort = null;

// ─── Telemetry ────────────────────────────────────────────────────────────────

// Generate or retrieve a persistent anonymous user ID
function getTelemetryUserId() {
    let userId = store.get('telemetryUserId');
    if (!userId) {
        userId = crypto.randomUUID();
        store.set('telemetryUserId', userId);
    }
    return userId;
}

const td = new TelemetryDeck({
    appID: 'A0A52C82-D7ED-4F4E-8320-064E719AFCA9',
    clientUser: getTelemetryUserId(),
    subtleCrypto: crypto.webcrypto.subtle,
    testMode: isDev
});

function sendSignal(type, payload = {}) {
    try {
        td.signal(type, {
            platform: process.platform,
            arch: process.arch,
            electronVersion: process.versions.electron,
            appVersion: app.getVersion(),
            ...payload
        });
    } catch (e) {
        // Telemetry should never break the app
        console.error('Telemetry error:', e.message);
    }
}

// Listen for telemetry signals from the renderer process
ipcMain.on('telemetry', (_event, type, payload) => {
    sendSignal(type, payload || {});
});

// ─── Path Resolution ───────────────────────────────────────────────────────────

function getResourcePath() {
    if (isDev) {
        return path.join(__dirname, '..');
    }
    return process.resourcesPath;
}

function getPythonPath() {
    const resourcePath = getResourcePath();
    if (isDev) {
        // Use system Python in dev mode
        return process.platform === 'win32' ? 'python' : 'python3';
    }
    if (process.platform === 'win32') {
        return path.join(resourcePath, 'python', 'python.exe');
    }
    return path.join(resourcePath, 'python', 'bin', 'python3');
}

function getBackendPath() {
    const resourcePath = getResourcePath();
    return path.join(resourcePath, 'backend', 'app.py');
}

function getDefaultModesDir() {
    const resourcePath = getResourcePath();
    return path.join(resourcePath, 'modes');
}

function getModesDir() {
    const saved = store.get('modesDir');
    if (saved && require('fs').existsSync(saved)) {
        return saved;
    }
    return getDefaultModesDir();
}

// ─── Port Discovery ────────────────────────────────────────────────────────────

function findFreePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.listen(0, '127.0.0.1', () => {
            const port = server.address().port;
            server.close(() => resolve(port));
        });
        server.on('error', reject);
    });
}

// ─── Health Check ──────────────────────────────────────────────────────────────

function waitForServer(port, timeoutMs = 15000) {
    const startTime = Date.now();
    return new Promise((resolve, reject) => {
        const check = () => {
            if (Date.now() - startTime > timeoutMs) {
                reject(new Error('Server startup timed out after 15 seconds'));
                return;
            }

            const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
                if (res.statusCode === 200) {
                    resolve();
                } else {
                    setTimeout(check, 200);
                }
            });

            req.on('error', () => {
                setTimeout(check, 200);
            });

            req.setTimeout(1000, () => {
                req.destroy();
                setTimeout(check, 200);
            });
        };

        check();
    });
}

// ─── Python Process ────────────────────────────────────────────────────────────

function startPythonServer(port, modesDir) {
    const pythonPath = getPythonPath();
    const backendPath = getBackendPath();

    const env = {
        ...process.env,
        ELECTRON_APP: '1',
        PYTHONUNBUFFERED: '1'
    };

    // Ensure the backend directory is in the Python path so eyesy_engine and config can be imported
    const backendDir = path.dirname(backendPath);
    const projectDir = path.join(backendDir, '..');
    env.PYTHONPATH = [backendDir, projectDir, env.PYTHONPATH].filter(Boolean).join(path.delimiter);

    const args = [
        backendPath,
        '--port', String(port),
        '--host', '127.0.0.1',
        '--modes-dir', modesDir
    ];

    console.log(`Starting Python: ${pythonPath} ${args.join(' ')}`);

    pythonProcess = spawn(pythonPath, args, {
        env,
        cwd: isDev ? path.join(__dirname, '..') : getResourcePath(),
        stdio: ['pipe', 'pipe', 'pipe']
    });

    pythonProcess.stdout.on('data', (data) => {
        console.log(`[Python] ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python ERROR] ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
        if (code !== 0 && code !== null && mainWindow && !app.isQuitting) {
            dialog.showErrorBox(
                'Python Backend Error',
                `The Python backend process exited unexpectedly (code ${code}).\nThe application will now quit.`
            );
            app.quit();
        }
    });

    pythonProcess.on('error', (err) => {
        console.error('Failed to start Python process:', err);
        dialog.showErrorBox(
            'Python Not Found',
            `Could not start the Python backend.\n\nError: ${err.message}\n\nPlease ensure Python 3 is installed and accessible.`
        );
        app.quit();
    });
}

function stopPythonServer() {
    if (pythonProcess) {
        console.log('Stopping Python server...');
        if (process.platform === 'win32') {
            spawn('taskkill', ['/pid', String(pythonProcess.pid), '/f', '/t']);
        } else {
            pythonProcess.kill('SIGTERM');
            // Force kill after 3 seconds if still running
            setTimeout(() => {
                try {
                    pythonProcess.kill('SIGKILL');
                } catch (e) {
                    // Already dead
                }
            }, 3000);
        }
        pythonProcess = null;
    }
}

// ─── Modes Folder Selection ────────────────────────────────────────────────────

async function showModesFolderDialog() {
    const result = await dialog.showOpenDialog({
        title: 'Select your EYESY modes folder',
        message: 'Choose the folder containing your EYESY mode directories (each with a main.py)',
        properties: ['openDirectory', 'createDirectory'],
        defaultPath: store.get('modesDir') || app.getPath('home')
    });

    if (!result.canceled && result.filePaths.length > 0) {
        const selectedPath = result.filePaths[0];
        store.set('modesDir', selectedPath);
        return selectedPath;
    }
    return null;
}

async function changeModesFolderAndNotify() {
    const newPath = await showModesFolderDialog();
    if (newPath) {
        // Tell the Flask backend about the new modes directory
        try {
            const res = await new Promise((resolve, reject) => {
                const postData = JSON.stringify({ modes_dir: newPath });
                const req = http.request({
                    hostname: '127.0.0.1',
                    port: serverPort,
                    path: '/set-modes-dir',
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(postData)
                    }
                }, (res) => {
                    resolve(res.statusCode);
                });
                req.on('error', reject);
                req.write(postData);
                req.end();
            });
            console.log(`Modes directory updated to: ${newPath} (status: ${res})`);
            sendSignal('ModesFolder.changed');
        } catch (err) {
            console.error('Failed to notify backend of modes dir change:', err);
        }
    }
}

// ─── Menu ──────────────────────────────────────────────────────────────────────

function createMenu() {
    const isMac = process.platform === 'darwin';

    const template = [
        ...(isMac ? [{
            label: app.name,
            submenu: [
                { role: 'about' },
                { type: 'separator' },
                { role: 'hide' },
                { role: 'hideOthers' },
                { role: 'unhide' },
                { type: 'separator' },
                { role: 'quit' }
            ]
        }] : []),
        {
            label: 'File',
            submenu: [
                {
                    label: 'Change Modes Folder...',
                    accelerator: 'CmdOrCtrl+Shift+M',
                    click: () => changeModesFolderAndNotify()
                },
                { type: 'separator' },
                ...(isMac ? [{ role: 'close' }] : [{ role: 'quit' }])
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { type: 'separator' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'EYESY Documentation',
                    click: () => shell.openExternal('https://critterandguitari.github.io/cg-docs/EYESY/')
                },
                {
                    label: 'EYESY Modes Repository',
                    click: () => shell.openExternal('https://github.com/critterandguitari/EYESY_Modes_Pygame')
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

// ─── Window ────────────────────────────────────────────────────────────────────

function createWindow(port) {
    const { width, height } = store.get('windowBounds');
    const isMac = process.platform === 'darwin';

    mainWindow = new BrowserWindow({
        width,
        height,
        minWidth: 900,
        minHeight: 600,
        title: 'EYESY Simulator',
        titleBarStyle: isMac ? 'hiddenInset' : 'default',
        trafficLightPosition: isMac ? { x: 15, y: 15 } : undefined,
        backgroundColor: '#1a1a1a',
        show: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        }
    });

    mainWindow.loadURL(`http://127.0.0.1:${port}`);

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // Save window size on resize
    mainWindow.on('resize', () => {
        const bounds = mainWindow.getBounds();
        store.set('windowBounds', { width: bounds.width, height: bounds.height });
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Detect renderer process crashes
    mainWindow.webContents.on('render-process-gone', (event, details) => {
        console.error('Renderer process gone:', details.reason, details.exitCode);
    });

    mainWindow.webContents.on('crashed', (event) => {
        console.error('Renderer crashed');
    });

    // Open external links in browser
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    if (isDev) {
        mainWindow.webContents.openDevTools();
    }
}

// ─── App Lifecycle ─────────────────────────────────────────────────────────────

app.isQuitting = false;

app.on('before-quit', () => {
    app.isQuitting = true;
    sendSignal('App.quit');
    stopPythonServer();
});

app.on('window-all-closed', () => {
    app.quit();
});

app.on('activate', () => {
    if (mainWindow === null && serverPort) {
        createWindow(serverPort);
    }
});

app.whenReady().then(async () => {
    try {
        // Step 1: First-launch modes folder selection
        let modesDir = getModesDir();
        const savedModesDir = store.get('modesDir');

        if (!savedModesDir) {
            // First launch — ask user to pick their modes folder
            const chosen = await showModesFolderDialog();
            if (chosen) {
                modesDir = chosen;
            }
            // If they cancel, we use the built-in modes directory
        }

        // Step 2: Find a free port
        serverPort = await findFreePort();
        console.log(`Using port: ${serverPort}`);

        // Step 3: Create the menu
        createMenu();

        // Step 4: Start Python backend
        startPythonServer(serverPort, modesDir);

        // Step 5: Wait for server to be ready
        console.log('Waiting for Python server to start...');
        await waitForServer(serverPort);
        console.log('Python server is ready!');

        // Step 6: Create the window
        createWindow(serverPort);

        // Step 7: Send app launched telemetry
        sendSignal('App.launched');

    } catch (err) {
        console.error('Startup error:', err);
        dialog.showErrorBox(
            'Startup Error',
            `Failed to start EYESY Simulator:\n\n${err.message}`
        );
        app.quit();
    }
});
