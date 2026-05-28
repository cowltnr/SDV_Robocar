from flask import Flask, Response, jsonify
import multiprocessing
import time
import queue
import cv2
import threading

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan, Image
from cv_bridge import CvBridge
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

# --- Flask 서버 정의 ---
app = Flask(__name__)
bridge = CvBridge()
frame_lock = threading.Lock()
latest_frame = None
latest_lidar = None
lidar_shared_lock = None

# --- 공유 큐 ---
odom_queue = multiprocessing.Queue(maxsize=1)
lidar_queue = multiprocessing.Queue(maxsize=1)
image_queue = multiprocessing.Queue(maxsize=1)


# ============================
# Flask 라우트
# ============================

# --- (1) 카메라 스트리밍 ---
def generate_frames():
    latest_frame = None
    while True:
        if not image_queue.empty():
            last_frame = image_queue.get()

        if last_frame is None:
            continue
        _, buffer = cv2.imencode('.jpg', last_frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# --- (2) 최신 Odometry 정보 ---
@app.route('/odometry')
def get_odometry():
    try:
        data = odom_queue.get(timeout=1.0)
        return jsonify(data)
    except queue.Empty:
        return jsonify({"error": "No odometry data"}), 204


# --- (3) 최신 LiDAR 정보 ---
@app.route('/lidar')
def get_ydlidar():
    global latest_lidar, lidar_shared_lock

    if latest_lidar is None:
        return jsonify({"error": "LiDAR shared storage not initialized"}), 204

    with lidar_shared_lock:
        if not latest_lidar.get("ready", False):
            return jsonify({"error": "No LiDAR data"}), 204

        data = dict(latest_lidar)

    return jsonify(data)


# ============================
# ROS2 프로세스 정의
# ============================

def ros_process(odom_q, lidar_q, image_q, latest_lidar_shared, lidar_lock):
    """ROS2 노드: Odometry + LiDAR + Camera 동시 구독"""

    class RobotStreamer(Node):
        def __init__(self):
            super().__init__('robot_streamer')
            # --- Odometry 구독 (기본 QoS로 OK) ---
            self.create_subscription(Odometry, '/sim/odom', self.odom_callback, 10)

            # --- Camera 구독 (기본 QoS로 OK) ---
            self.create_subscription(Image, '/sim/camera/color/image_raw', self.image_callback, 10)

            # --- LiDAR 구독: sensor_data QoS 프로파일 사용 ---
            sensor_qos = QoSProfile(
                depth=10,
                reliability=ReliabilityPolicy.BEST_EFFORT,
                history=HistoryPolicy.KEEP_LAST,
                durability=DurabilityPolicy.VOLATILE,
            )
            self.create_subscription(LaserScan, '/sim/scan', self.lidar_callback, sensor_qos)

        def odom_callback(self, msg):
            pose = msg.pose.pose
            twist = msg.twist.twist
            data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "pose": {
                    "position": {"x": pose.position.x, "y": pose.position.y, "z": pose.position.z},
                    "orientation": {"x": pose.orientation.x, "y": pose.orientation.y,
                                    "z": pose.orientation.z, "w": pose.orientation.w}
                },
                "twist": {
                    "linear": {"x": twist.linear.x, "y": twist.linear.y, "z": twist.linear.z},
                    "angular": {"x": twist.angular.x, "y": twist.angular.y, "z": twist.angular.z}
                }
            }
            if not odom_q.full():
                odom_q.put(data)

        def lidar_callback(self, msg):
            data = {
                "ready": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "stamp_sec": time.time(),
                "angle_min": msg.angle_min,
                "angle_max": msg.angle_max,
                "angle_increment": msg.angle_increment,
                "ranges": list(msg.ranges)
            }

            with lidar_lock:
                latest_lidar_shared.clear()
                latest_lidar_shared.update(data)

        def image_callback(self, msg):
            global latest_frame
            frame = bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            with frame_lock:
                latest_frame = frame

            if not image_q.full():
                image_q.put(latest_frame)

    # --- ROS2 실행 ---
    rclpy.init()
    node = RobotStreamer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


# ============================
# Flask + ROS2 병렬 실행
# ============================

if __name__ == "__main__":
    manager = multiprocessing.Manager()

    latest_lidar = manager.dict()
    latest_lidar["ready"] = False

    lidar_shared_lock = manager.Lock()

    ros_proc = multiprocessing.Process(
        target=ros_process,
        args=(odom_queue, lidar_queue, image_queue, latest_lidar, lidar_shared_lock)
    )

    ros_proc.start()
    print("[INFO] Flask + ROS2 병렬 실행 시작")

    app.run(host='0.0.0.0', port=8000)
    ros_proc.join()