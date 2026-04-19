"use strict";

const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn, exec } = require("child_process");
const path = require("path");
const http = require("http");

// ── Process handles ──────────────────────────────────────────────────────────
let win = null;
let camProcess = null;
let nodeProcess = null;
let mjpegProcess = null;

// ── ROS commands ─────────────────────────────────────────────────────────────
const SOURCE = [
  ". /opt/ros/humble/setup.bash",
  ". /home/maridirobot/ros2_ws/install/local_setup.bash",
].join(" && ");

// Live Realsense D555 — matches your .desktop Exec exactly
const CAM_CMD = `${SOURCE} && ros2 launch realsense2_camera rs_launch.py \
  device_type:=d555 \
  align_depth.enable:=true \
  enable_sync:=true \
  enable_gyro:=false \
  enable_accel:=false \
  initial_reset:=true \
  depth_module.depth_profile:=896x504x5 \
  rgb_camera.color_profile:=896x504x5`;

// Vision node — matches your original bash
const NODE_CMD = `${SOURCE} && ros2 run bag_detector vision_node_tcp`;

// ── Helpers ───────────────────────────────────────────────────────────────────
function spawnBash(cmd) {
  return spawn("bash", ["-c", cmd], {
    detached: true,
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function killProcessGroup(proc) {
  if (!proc) return;
  try {
    process.kill(-proc.pid, "SIGINT");
  } catch (_) {
    try {
      proc.kill("SIGINT");
    } catch (_2) {}
  }
}

function killAll(cb) {
  killProcessGroup(camProcess);
  killProcessGroup(nodeProcess);
  killProcessGroup(mjpegProcess);
  camProcess = null;
  nodeProcess = null;
  mjpegProcess = null;
  exec(
    'pkill -SIGINT -f "realsense2_camera" 2>/dev/null; ' +
      'pkill -SIGINT -f "vision_node_tcp_ui"  2>/dev/null; ' +
      'pkill -SIGINT -f "mjpeg_server.py"    2>/dev/null',
    () => {
      if (cb) setTimeout(cb, 500);
    },
  );
}

function send(event, ...args) {
  if (win && !win.isDestroyed()) win.webContents.send(event, ...args);
}

function pollMJPEG(retries) {
  const req = http.get(
    { host: "127.0.0.1", port: 8765, path: "/", timeout: 600 },
    (res) => {
      res.destroy();
      send("status", "running");
    },
  );
  req.on("error", () => {
    if (retries > 0) setTimeout(() => pollMJPEG(retries - 1), 1000);
    else send("status", "running");
  });
  req.on("timeout", () => {
    req.destroy();
    if (retries > 0) setTimeout(() => pollMJPEG(retries - 1), 1000);
    else send("status", "running");
  });
}

// ── Launch sequence ───────────────────────────────────────────────────────────
function doLaunch() {
  const scriptDir = app.isPackaged
    ? path.join(process.resourcesPath, "scripts")
    : path.join(__dirname, "scripts");
  const MJPEG_CMD = `${SOURCE} && python3 "${path.join(scriptDir, "mjpeg_server.py")}"`;

  send("status", "cam-starting");
  camProcess = spawnBash(CAM_CMD);

  // Wait 6 seconds for the Realsense to hardware-reset and spin up
  setTimeout(() => {
    send("status", "node-starting");
    nodeProcess = spawnBash(NODE_CMD);
    mjpegProcess = spawnBash(MJPEG_CMD);
    pollMJPEG(30);
  }, 6000);
}

// ── IPC handlers ──────────────────────────────────────────────────────────────
ipcMain.on("launch", doLaunch);

ipcMain.on("reset", () => {
  send("status", "resetting");
  killAll(() => {
    send("status", "cam-starting");
    doLaunch();
  });
});

ipcMain.on("stop", () => {
  send("status", "stopping");
  killAll(() => send("status", "idle"));
});

ipcMain.on("window-close", () => {
  killAll(() => app.quit());
});
ipcMain.on("window-minimize", () => {
  if (win) win.minimize();
});

// ── Window ────────────────────────────────────────────────────────────────────
function createWindow() {
  win = new BrowserWindow({
    fullscreen: true,
    // width: 1920,
    // height: 1080,
    // minWidth: 1280,
    // minHeight: 720,
    resizable: false,
    frame: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      devTools: false,
    },
  });

  win.setMenu(null);
  win.loadFile(path.join(__dirname, "renderer", "index.html"));

  win.webContents.on("context-menu", (e) => e.preventDefault());
  win.webContents.on("before-input-event", (e, input) => {
    if (
      input.key === "F12" ||
      (input.control && input.shift && input.key === "I")
    )
      e.preventDefault();
  });

  win.once("ready-to-show", () => win.show());
}

app.whenReady().then(createWindow);

app.on("before-quit", () => killAll());
app.on("window-all-closed", () => {
  killAll();
  app.quit();
});
