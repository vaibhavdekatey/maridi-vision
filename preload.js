'use strict'
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('maridi', {
  launch:   () => ipcRenderer.send('launch'),
  reset:    () => ipcRenderer.send('reset'),
  stop:     () => ipcRenderer.send('stop'),
  onStatus: (cb) => ipcRenderer.on('status', (_, s) => cb(s)),
  close:    () => ipcRenderer.send('window-close'),
  minimize: () => ipcRenderer.send('window-minimize')
})
