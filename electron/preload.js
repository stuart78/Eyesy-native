const { contextBridge, ipcRenderer } = require('electron');

// Expose minimal platform info and telemetry to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
    platform: process.platform,
    isElectron: true,
    sendTelemetry: (type, payload) => {
        ipcRenderer.send('telemetry', type, payload);
    }
});
