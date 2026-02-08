const { contextBridge } = require('electron');

// Expose minimal platform info to the renderer
contextBridge.exposeInMainWorld('electronAPI', {
    platform: process.platform,
    isElectron: true
});
