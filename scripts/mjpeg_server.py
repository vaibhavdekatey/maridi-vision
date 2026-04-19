#!/usr/bin/env python3
"""
mjpeg_server.py
Subscribes to the RealSense colour topic and serves it as a
Motion-JPEG HTTP stream on 127.0.0.1:8765 for the Electron UI.
Draws centre crosshairs identical to vision_node_tcp's viewer.
"""

import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

# ── Shared state ──────────────────────────────────────────────────────────────
_latest_jpg  = None
_frame_lock  = threading.Lock()
_MJPEG_PORT  = 8765
_JPEG_QUALITY = 75          # lower = less bandwidth, still plenty sharp at 896×504

# ── MJPEG HTTP handler ────────────────────────────────────────────────────────
class MJPEGHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):   # suppress default access log
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type',
                         'multipart/x-mixed-replace; boundary=mjpeg_frame')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            while True:
                with _frame_lock:
                    jpg = _latest_jpg
                if jpg is not None:
                    payload = (
                        b'--mjpeg_frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' +
                        jpg + b'\r\n'
                    )
                    self.wfile.write(payload)
                    self.wfile.flush()
                time.sleep(0.05)          # ~20 fps cap — enough for an operator view
        except (BrokenPipeError, ConnectionResetError):
            pass

# ── ROS2 node ─────────────────────────────────────────────────────────────────
class MJPEGNode(Node):

    def __init__(self):
        super().__init__('mjpeg_server')
        self.bridge = CvBridge()
        self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self._on_frame,
            rclpy.qos.qos_profile_sensor_data
        )
        self.get_logger().info(f'MJPEG server listening on 127.0.0.1:{_MJPEG_PORT}')

    def _on_frame(self, msg: Image):
        global _latest_jpg
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            h, w  = frame.shape[:2]

            # Centre crosshairs (same as vision_node_tcp UI)
            cv2.line(frame, (w // 2, 0),     (w // 2, h),     (255, 0, 0), 1)
            cv2.line(frame, (0,     h // 2), (w,      h // 2),(255, 0, 0), 1)

            ok, buf = cv2.imencode(
                '.jpg', frame,
                [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY]
            )
            if ok:
                with _frame_lock:
                    _latest_jpg = buf.tobytes()
        except Exception as e:
            self.get_logger().error(f'Frame encode error: {e}')

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    rclpy.init()
    node = MJPEGNode()

    server = HTTPServer(('127.0.0.1', _MJPEG_PORT), MJPEGHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
