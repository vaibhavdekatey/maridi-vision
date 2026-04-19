# Maridi Vision — Operator Panel

Electron desktop app for the GP180 bag detection system.  
Runs on Jetson Orin Nano (ARM64 / Ubuntu 22.04 + ROS Humble).

---

## What it does

| Button | Action |
|--------|--------|
| **Launch** | Starts D555 camera nodes, then `vision_node_tcp`, then MJPEG stream |
| **Reset** | Kills everything and restarts the full sequence cleanly |
| **Stop** | Sends SIGINT to all nodes and terminates |

The left panel shows the live camera feed with centre crosshairs.  
No raw terminal output is shown to the operator.

---

## Prerequisites (on the Jetson)

```bash
# Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Python deps for mjpeg_server
sudo apt install -y python3-opencv ros-humble-cv-bridge
```

---

## Build

```bash
cd maridi-vision
npm install
npm run build
```

Output: `dist/maridi-vision_1.0.0_arm64.deb`

> Building natively on the Jetson takes ~5-10 min on first run (electron binary download).
> Subsequent builds are fast.

---

## Install

```bash
sudo dpkg -i dist/maridi-vision_1.0.0_arm64.deb
```

The app appears in the application menu as **Maridi Vision**.  
To launch from terminal: `maridi-vision`

---

## Uninstall

```bash
sudo apt remove maridi-vision
```

---

## Notes

- The MJPEG stream runs on `127.0.0.1:8765` (loopback only, not exposed to network).
- The app kills all spawned processes when closed — no orphan nodes.
- DevTools and right-click are disabled in the installed build.
- To add an icon: place a 512×512 `icon.png` in `assets/` before building.
