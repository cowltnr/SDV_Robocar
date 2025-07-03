from flask import Flask, Response, request
import cv2
import time
import threading

# Flask 서버 생성
app = Flask(__name__)

# OpenCV로 카메라 연결 (로보카 카메라 장치 번호에 따라 0 또는 1)
cap = cv2.VideoCapture(0)

# ────────── Thread-A : 카메라 MJPEG 스트림 ──────────
def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            continue
        # JPEG 인코딩
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        # MJPEG 포맷으로 반환
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- 2. (선택) 속도 수신용 엔드포인트 ---
@app.route('/speed', methods=['POST'])
def receive_speed():
    data = request.get_json()
    print(f"[속도 수신] timestamp: {data.get('timestamp')}, speed: {data.get('speed')} m/s")
    return {"status": "ok"}

# ─────────────────── Thread-B : /odom 구독 → /speed POST ───────────────────
latest = {"speed": 0.0, "x": 0.0, "y": 0.0, "theta": 0.0}   # 공유 버퍼

def quat_to_yaw(q):
    """쿼터니언 → yaw(rad) 변환"""
    siny_cosp = 2 * (q.w*q.z + q.x*q.y)
    cosy_cosp = 1 - 2 * (q.y*q.y + q.z*q.z)
    return math.atan2(siny_cosp, cosy_cosp)

class OdomListener(Node):
    def __init__(self):
        super().__init__("odom_listener")
        self.create_subscription(Odometry, "/odom", self.cb_odom, 10)

    def cb_odom(self, msg: Odometry):
        latest["speed"] = msg.twist.twist.linear.x            # m/s
        latest["x"]     = msg.pose.pose.position.x            # m
        latest["y"]     = msg.pose.pose.position.y
        latest["theta"] = quat_to_yaw(msg.pose.pose.orientation)  # rad

def sensor_loop():
    """ROS 2 스핀 + 1 Hz /speed POST 루프 (daemon thread)"""
    rclpy.init(args=None)
    node = OdomListener()
    sess = requests.Session()
    last_sent = 0.0

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)           # 20 Hz polling

            now = time.time()
            if now - last_sent >= 1.0:                        # 1 Hz 전송
                payload = {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                    "speed": latest["speed"],
                    "rel_x": latest["x"],
                    "rel_y": latest["y"],
                    "theta": latest["theta"]
                }
                try:
                    sess.post("http://127.0.0.1:8000/speed",
                              json=payload, timeout=0.3)
                except requests.exceptions.RequestException as e:
                    print("[/speed POST 오류]", e)

                last_sent = now
    finally:
        node.destroy_node()
        rclpy.shutdown()

# --- 3. 서버 실행 ---
if __name__ == "__main__":
    # Thread-B 시작 (daemon=True → Flask 종료 시 자동 종료)
    threading.Thread(target=sensor_loop, daemon=True).start()
    # host='0.0.0.0' → 외부 장치(데스크탑)에서도 접속 가능
    app.run(host='0.0.0.0', port=8000)
