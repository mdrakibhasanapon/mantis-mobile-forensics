/**
 * Electron Preload script exposing secure local IPC bridge to Mantis Mobile Forensics renderer.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('mantisDesktop', {
  isDesktop: true,
  getApiConfig: () => ipcRenderer.invoke('get-api-config'),
  openDataDirectory: () => ipcRenderer.invoke('open-data-dir'),
  checkActiveJobs: () => ipcRenderer.invoke('check-active-jobs'),
  showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),
  showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options)
});
