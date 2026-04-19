#!/usr/bin/env python3
"""
test_mjpeg.py  —  TEST MODE only
Serves a synthetic camera frame as MJPEG on 127.0.0.1:8765.
No ROS required. Simulates bounding-box detections for UI testing.
"""

import math
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
import numpy as np

_PORT    = 8765
_W, _H   = 896, 504
_QUALITY = 75

_latest_jpg = None
_lock       = threading.Lock()


def make_frame(t: float) -> np.ndarray:
    frame = np.full((_H, _W, 3), (18, 18, 18), dtype=np.uint8)

    # Subtle grid
    for x in range(0, _W, 80):
        cv2.line(frame, (x, 0), (x, _H), (30, 30, 30), 1)
    for y in range(0, _H, 80):
        cv2.line(frame, (0, y), (_W, y), (30, 30, 30), 1)

    # Simulated bag bounding box (drifts slowly)
    bx = int(_W * 0.3 + math.sin(t * 0.4) * _W * 0.12)
    by = int(_H * 0.3 + math.cos(t * 0.3) * _H * 0.10)
    bw = int(_W * 0.22 + math.sin(t * 0.2) * _W * 0.04)
    bh = int(_H * 0.28 + math.cos(t * 0.25) * _H * 0.04)
    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (93, 202, 165), 2)

    cx, cy = bx + bw // 2, by + bh // 2
    cv2.drawMarker(frame, (cx, cy), (60, 60, 226), cv2.MARKER_CROSS, 14, 2)

    # Mock coordinates
    rel_x = int((cx - _W // 2) * 1.4)
    rel_y = int((cy - _H // 2) * 1.4)
    rel_z = 620
    label = f"X:{rel_x:+d}  Y:{rel_y:+d}  Z:{rel_z}"
    cv2.putText(frame, label, (bx, by - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (93, 202, 165), 1, cv2.LINE_AA)

    # Centre crosshairs
    cv2.line(frame, (_W // 2, 0),     (_W // 2, _H),     (255, 0, 0), 1)
    cv2.line(frame, (0,       _H // 2), (_W, _H // 2), (255, 0, 0), 1)

    # TEST MODE watermark
    cv2.putText(frame, "TEST MODE", (10, _H - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 60, 60), 1, cv2.LINE_AA)

    # Timestamp
    ts = time.strftime("%H:%M:%S")
    cv2.putText(frame, ts, (_W - 72, _H - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (60, 60, 60), 1, cv2.LINE_AA)

    return frame


def frame_loop():
    global _latest_jpg
    t = 0.0
    while True:
        frame = make_frame(t)
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, _QUALITY])
        if ok:
            with _lock:
                _latest_jpg = buf.tobytes()
        t += 0.05
        time.sleep(0.05)          # 20 fps


class MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type',
                         'multipart/x-mixed-replace; boundary=mjpeg_frame')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            while True:
                with _lock:
                    jpg = _latest_jpg
                if jpg:
                    self.wfile.write(
                        b'--mjpeg_frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                        jpg + b'\r\n'
                    )
                    self.wfile.flush()
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == '__main__':
    threading.Thread(target=frame_loop, daemon=True).start()
    server = HTTPServer(('127.0.0.1', _PORT), MJPEGHandler)
    print(f'[test_mjpeg] serving on 127.0.0.1:{_PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
