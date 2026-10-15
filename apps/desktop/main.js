/**
 * Mantis Mobile Forensics - Desktop Main Process (Electron)
 * Manages the local Python FastAPI forensic engine child process,
 * window lifecycle, loopback IPC, and protected graceful shutdown.
 */
const { app, BrowserWindow, Menu, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const crypto = require('crypto');
const http = require('http');

let mainWindow = null;
let pythonProcess = null;
let isQuitting = false;

const API_PORT = process.env.MMF_PORT || 8765;
const API_HOST = '127.0.0.1';
const SESSION_TOKEN = process.env.MMF_SESSION_TOKEN || crypto.randomBytes(32).toString('hex');
const BASE_DATA_DIR = process.env.MMF_DATA_DIR || path.join(app.getPath('userData'), 'cases');

function startPythonBackend() {
  const rootDir = path.resolve(__dirname, '../../');
  const pythonPath = process.env.PYTHON_BIN || 'python3';

  console.log(`[DESKTOP] Starting Python backend engine on ${API_HOST}:${API_PORT}...`);

  const env = {
    ...process.env,
    PYTHONPATH: `${path.join(rootDir, 'packages/mmf_core/src')}:${path.join(rootDir, 'apps/api/src')}`,
    MMF_SESSION_TOKEN: SESSION_TOKEN,
    MMF_DATA_DIR: BASE_DATA_DIR,
    PYTHONUNBUFFERED: '1'
  };

  const args = [
    '-m', 'mmf_api.main',
    '--host', API_HOST,
    '--port', String(API_PORT),
    '--token', SESSION_TOKEN,
    '--data-dir', BASE_DATA_DIR
  ];

  pythonProcess = spawn(pythonPath, args, { env, cwd: rootDir });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[API-OUT] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[API-ERR] ${data.toString().trim()}`);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[API-EXIT] Python backend process exited with code ${code}, signal ${signal}`);
    if (!isQuitting && mainWindow) {
      dialog.showErrorBox(
        'Forensic Engine Terminated',
        `The local Python backend process stopped unexpectedly (code: ${code}).\nPlease restart the application.`
      );
    }
  });
}

function checkBackendHealth(retries = 30, interval = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const poll = () => {
      attempts++;
      const req = http.get(`http://${API_HOST}:${API_PORT}/health`, (res) => {
        if (res.statusCode === 200) {
          console.log('[DESKTOP] Forensic engine is healthy and responding.');
          resolve(true);
        } else {
          retry();
        }
      });

      req.on('error', () => {
        retry();
      });

      req.setTimeout(400);

      function retry() {
        if (attempts >= retries) {
          reject(new Error('Timed out waiting for local forensic backend engine.'));
        } else {
          setTimeout(poll, interval);
        }
      }
    };
    poll();
  });
}

async function getActiveJobs() {
  return new Promise((resolve) => {
    const options = {
      hostname: API_HOST,
      port: API_PORT,
      path: '/jobs/active',
      method: 'GET',
      headers: {
        'X-MMF-Session-Token': SESSION_TOKEN
      },
      timeout: 1000
    };

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          const jobs = JSON.parse(body);
          resolve(Array.isArray(jobs) ? jobs : []);
        } catch {
          resolve([]);
        }
      });
    });

    req.on('error', () => resolve([]));
    req.end();
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: '#0c0f14',
    title: 'Mantis Mobile Forensics - Professional Workstation',
    icon: path.join(__dirname, '../../assets/icon.png'),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  Menu.setApplicationMenu(null);
  mainWindow.removeMenu();
  mainWindow.setMenuBarVisibility(false);

  // Handle protected window close
  mainWindow.on('close', async (e) => {
    if (isQuitting) return;

    e.preventDefault();
    try {
      const activeJobs = await getActiveJobs();
      if (activeJobs.length > 0) {
        const choice = dialog.showMessageBoxSync(mainWindow, {
          type: 'warning',
          buttons: ['Cancel & Keep Running', 'Force Quit Anyway'],
          defaultId: 0,
          cancelId: 0,
          title: 'Active Forensic Jobs In Progress',
          message: `There are ${activeJobs.length} active evidence processing or acquisition jobs running!`,
          detail: 'Closing now may interrupt database hashing or evidence parsing. Are you sure you wish to exit?'
        });

        if (choice === 0) {
          return; // Don't quit
        }
      }
    } catch (err) {
      console.error('Error checking active jobs during close:', err);
    }

    isQuitting = true;
    stopBackend();
    mainWindow.destroy();
    app.quit();
  });

  // Load production bundle or Vite dev server
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    const distPath = path.join(__dirname, '../web/dist/index.html');
    mainWindow.loadFile(distPath);
  }
}

function stopBackend() {
  if (pythonProcess) {
    console.log('[DESKTOP] Gracefully shutting down forensic backend process...');
    pythonProcess.kill('SIGINT');
    setTimeout(() => {
      if (pythonProcess && !pythonProcess.killed) {
        pythonProcess.kill('SIGKILL');
      }
    }, 2000);
  }
}

// IPC Handlers
ipcMain.handle('get-api-config', () => ({
  port: API_PORT,
  token: SESSION_TOKEN,
  baseUrl: `http://${API_HOST}:${API_PORT}`,
  dataDir: BASE_DATA_DIR
}));

ipcMain.handle('open-data-dir', () => {
  shell.openPath(BASE_DATA_DIR);
});

ipcMain.handle('check-active-jobs', async () => {
  return await getActiveJobs();
});

ipcMain.handle('show-save-dialog', async (event, options) => {
  return await dialog.showSaveDialog(mainWindow, options);
});

ipcMain.handle('show-open-dialog', async (event, options) => {
  return await dialog.showOpenDialog(mainWindow, options);
});

// App Lifecycle
app.whenReady().then(async () => {
  startPythonBackend();
  try {
    await checkBackendHealth();
  } catch (err) {
    console.error('[DESKTOP] Backend health check failed:', err);
  }
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    isQuitting = true;
    stopBackend();
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  stopBackend();
});
