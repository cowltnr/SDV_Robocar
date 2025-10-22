import cv2
from ultralytics import YOLO
import random, time, datetime, requests, base64, threading, queue, math
from collections import deque

# ---------------------------
# Setting
# ---------------------------
STREAM_URL   = "http://192.168.50.165:8000/video"
ODOM_URL     = "http://192.168.50.165:8000/odometry"
LIDAR_URL    = "http://192.168.50.165:8000/lidar"
SERVER_URL   = "http://localhost:8080/inference"

INFER_HZ     = 10.0            # 추론 주기(Hz) 10 = 0.1s마다
SEND_INTERVAL= 1.0             # 1초마다 전송
JPEG_QUALITY = 70              # 전송용 JPEG 품질
TIMEOUT_GET  = 0.3             # odom 요청 타임아웃
TIMEOUT_POST = 0.5             # 전송 타임아웃

# Lidar Setting
LIDAR_HZ    = 10.0     # 폴링 주기(Hz)
LIDAR_TO    = 0.5      # GET timeout(s)
LIDAR_LEN   = 401      # ranges 길이 정규화
CAMERA_FOV_DEG = 71.0  # 카메라 수평 FoV (각도→인덱스 매핑용)

# GPS 근사 변환 기준
BASE_LAT = 37.501000
BASE_LON = 127.036000

def fake_gps_from_odom(x_m, y_m):
    return {
        "lat": BASE_LAT + x_m / 111000.0,
        "lon": BASE_LON + y_m /  88000.0,
    }

# ---------------------------
# 전역 공유 구조
# ---------------------------
frame_q   = deque(maxlen=1)          # 최신 프레임 1장 유지
send_q    = queue.Queue(maxsize=10)  # 전송 대기열(가득 차면 오래된 것 드롭)
odom_lock = threading.Lock()
odom_cache= {"gps": {"lat": None, "lon": None}, "speed": 0.0}
lidar_lock  = threading.Lock()
lidar_cache = {
    "angle_min": None,
    "angle_increment": None,
    "ranges": []
}

stop_evt  = threading.Event()

# ---------------------------
# Thread 1. CaptureThread
# ---------------------------
def capture_loop():
    cap = cv2.VideoCapture(STREAM_URL)
    if not cap.isOpened():
        print("[Capture] 스트림 오픈 실패")
        stop_evt.set()
        return
    print("[Capture] 시작")
    while not stop_evt.is_set():
        ok, frame = cap.read()
        if ok:
            frame_q.append(frame)  # 최신 프레임만 유지
        else:
            # 일시적 실패 시 아주 짧게 대기
            time.sleep(0.005)
    cap.release()
    print("[Capture] 종료")

# ---------------------------
# Thread 2. OdomThread
# ---------------------------
def odom_loop():
    print("[Odom] 시작")
    poll_period = 0.1  # 10Hz
    while not stop_evt.is_set():
        t0 = time.time()
        try:
            r = requests.get(ODOM_URL, timeout=TIMEOUT_GET)
            if r.status_code == 200:
                odom = r.json()
                x = odom["pose"]["position"]["x"]
                y = odom["pose"]["position"]["y"]
                speed = odom["twist"]["linear"]["x"]
                gps = fake_gps_from_odom(x, y)
                with odom_lock:
                    odom_cache["gps"] = gps
                    odom_cache["speed"] = float(speed)
            # 204(No Content) 등은 이전 값 유지
        except Exception as e:
            # 네트워크 오류는 스킵
            # print(f"[Odom] 수신 실패: {e}")
            pass
        # 주기 유지
        dt = time.time() - t0
        if dt < poll_period:
            time.sleep(poll_period - dt)
    print("[Odom] 종료")

# ---------------------------
# Thread 3. InferThread
# ---------------------------
def infer_loop(model):
    print("[Infer] 시작")
    last_infer = 0.0
    last_send  = time.time()
    while not stop_evt.is_set():
        # 최신 프레임이 없으면 대기
        if not frame_q:
            time.sleep(0.005)
            continue

        # 추론 주기 제어
        now = time.time()
        if now - last_infer < (1.0 / INFER_HZ):
            time.sleep(0.001)
            continue

        frame = frame_q[-1]  # 최신 프레임
        # YOLO 추론
        res = model.predict(source=frame, conf=0.3, verbose=False)[0]

        # 결과 파싱 & 시각화
        boxes = res.boxes
        detected = []
        for box in boxes:
            cls_id = int(box.cls[0])
            class_name = res.names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            detected.append({
                "class": class_name,
                "bbox": [x1, y1, x2, y2],
                "conf": round(conf, 2),
                "cls_id": cls_id
            })

            # 클래스별 색상(고정)
            color = class_colors.get(cls_id, (0, 255, 0))
            label = f"{class_name} {round(conf,2)}"
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(frame, label, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 전송 주기(1초)마다 페이로드 생성 → send_q로
        if now - last_send >= SEND_INTERVAL:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # JPEG 인코딩
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if ok:
                img_b64 = base64.b64encode(buf).decode('utf-8')
            else:
                img_b64 = None

            with odom_lock:
                gps   = dict(odom_cache["gps"])
                speed = float(odom_cache["speed"])

            # --- LiDAR snapshot & closest person ---
            with lidar_lock:
                angle_min = lidar_cache["angle_min"]
                angle_inc = lidar_cache["angle_increment"]
                ranges = list(lidar_cache["ranges"])  # 복사본

            closest_person = None
            if angle_min is not None and angle_inc is not None and len(ranges) > 0 and len(detected) > 0:
                image_w = frame.shape[1]
                fov_rad = math.radians(CAMERA_FOV_DEG)
                fov_half = fov_rad / 2.0
                best = (float("inf"), None)  # (dist, info)

                for obj in detected:
                    # 필요 시 특정 클래스만: if obj["class"] != "person": continue
                    x1, y1, x2, y2 = obj["bbox"]
                    cx = (x1 + x2) // 2
                    ratio = cx / image_w
                    angle_rel = (ratio - 0.5) * fov_rad
                    if abs(angle_rel) > fov_half:
                        continue
                    angle_global = angle_rel  # 설치 오프셋 있으면 여기서 보정

                    idx = int((angle_global - angle_min) / angle_inc)
                    if 0 <= idx < len(ranges):
                        dist = ranges[idx]
                        if 0.02 < dist < 12.0:
                            if dist < best[0]:
                                best = (dist, {
                                    "class": obj["class"],
                                    "conf": obj["conf"],
                                    "bbox": obj["bbox"],
                                    "distance": round(dist, 3),
                                    "angle": round(math.degrees(angle_global), 2),
                                    "center_x": cx,
                                    "center_y": (y1 + y2) // 2
                                })
                if best[1] is not None:
                    closest_person = best[1]

            payload = {
                "timestamp": timestamp,
                "gps": gps,
                "robocar_speed": speed,
                "objects": [
                    {"class": o["class"], "conf": o["conf"], "bbox": o["bbox"]}
                    for o in detected
                ],
                "image": img_b64,
                # --- LiDAR fields ---
                "lidar_available": angle_min is not None and angle_inc is not None and len(ranges) > 0,
                "closest_person": closest_person
            }

            # 최신 우선: 가득 차면 오래된 것 드롭
            try:
                if send_q.full():
                    send_q.get_nowait()
                send_q.put_nowait(payload)
            except queue.Full:
                pass

            last_send = now

        last_infer = now
    print("[Infer] 종료")

# ---------------------------
# Thread 4. SenderThread
# ---------------------------
def sender_loop():
    print("[Sender] 시작")
    while not stop_evt.is_set():
        try:
            data = send_q.get(timeout=0.2)
        except queue.Empty:
            continue
        try:
            r = requests.post(SERVER_URL, json=data, timeout=TIMEOUT_POST)
            if r.status_code != 200:
                print(f"[Sender] 전송 실패: {r.status_code}")
            else:
                print(f"[Sender] 전송 성공: {data.get('timestamp')}")
        except Exception as e:
            print(f"[Sender] 오류: {e}")
        finally:
            send_q.task_done()
    print("[Sender] 종료")

# ---------------------------
# Thread 5. LidarThread
# ---------------------------
def lidar_loop():
    print("[LiDAR] 시작")
    period = 1.0 / LIDAR_HZ
    while not stop_evt.is_set():
        t0 = time.time()
        try:
            r = requests.get(LIDAR_URL, timeout=LIDAR_TO)
            if r.status_code == 200:
                data = r.json()
                angle_min = data.get("angle_min")
                angle_inc = data.get("angle_increment")
                ranges    = data.get("ranges", [])

                # 길이 정규화
                if len(ranges) < LIDAR_LEN:
                    ranges = ranges + [0.0] * (LIDAR_LEN - len(ranges))
                elif len(ranges) > LIDAR_LEN:
                    ranges = ranges[:LIDAR_LEN]

                with lidar_lock:
                    lidar_cache["angle_min"]       = angle_min
                    lidar_cache["angle_increment"] = angle_inc
                    lidar_cache["ranges"]          = ranges
            # 204 등은 이전 값 유지
        except Exception:
            pass
        dt = time.time() - t0
        if dt < period:
            time.sleep(period - dt)
    print("[LiDAR] 종료")

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    # YOLO 모델 로드
    model = YOLO("detector/yolov8s.pt")
    class_names = model.names
    random.seed(42)
    class_colors = {
        cls_id: tuple(random.randint(0,255) for _ in range(3))
        for cls_id in class_names
    }

    # 스레드 가동
    th_cap  = threading.Thread(target=capture_loop, daemon=True)
    th_odom = threading.Thread(target=odom_loop, daemon=True)
    th_lidar = threading.Thread(target=lidar_loop, daemon=True)
    th_inf  = threading.Thread(target=infer_loop, args=(model,), daemon=True)
    th_send = threading.Thread(target=sender_loop, daemon=True)

    th_cap.start(); th_odom.start(); th_lidar.start(); th_inf.start(); th_send.start()

    # UI 루프(최신 프레임 표시만, 논블로킹)
    try:
        while not stop_evt.is_set():
            if frame_q:
                cv2.imshow("YOLO Detection (Live)", frame_q[-1])
            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_evt.set()
                break
            time.sleep(0.005)
    finally:
        stop_evt.set()
        th_cap.join(timeout=1.0)
        th_odom.join(timeout=1.0)
        th_lidar.join(timeout=1.0)
        th_inf.join(timeout=1.0)
        th_send.join(timeout=1.0)
        cv2.destroyAllWindows()
