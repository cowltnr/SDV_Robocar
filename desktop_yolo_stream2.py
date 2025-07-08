import cv2
from ultralytics import YOLO
import random
import time
import datetime
import requests

# --- 1. 모델 로드 ---
model = YOLO("detector/yolov8s.pt")
class_names = model.names

random.seed(42)
class_colors = {
    cls_id: tuple(random.randint(0, 255) for _ in range(3))
    for cls_id in class_names
}

# --- 2. 로보카 Flask 서버에서 영상 스트리밍 수신 ---
stream_url = "http://192.168.50.165:8000/video"
cap = cv2.VideoCapture(stream_url)

# --- 3. 로보카로부터 odometry 데이터 수신 ---
odometry_url = "http://192.168.50.165:8000/odometry"

# --- 4. GPS 변환 함수 ---
base_lat = 37.501000
base_lon = 127.036000
def fake_gps_from_odom(x_m, y_m):
    return {
        "lat": base_lat + x_m / 111000,
        "lon": base_lon + y_m / 88000
    }

# --- 5. YOLO 루프 시작 ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("스트리밍 수신 실패")
        continue

    # --- A. 로보카로부터 odometry 정보 수신 ---
    try:
        odom = requests.get(odometry_url, timeout=0.5).json()
        odom_x = odom["pose"]["position"]["x"]
        odom_y = odom["pose"]["position"]["y"]
        robocar_speed = odom["twist"]["linear"]["x"]
        gps_info = fake_gps_from_odom(odom_x, odom_y)
    except Exception as e:
        print(f"[odometry 수신 실패] {e}")
        gps_info = {"lat": None, "lon": None}
        robocar_speed = 0.0

    # --- B. YOLO 객체 탐지 수행 ---
    results = model.predict(source=frame, conf=0.3, verbose=False)
    result = results[0]

    boxes = result.boxes
    detected = []
    for box in boxes:
        cls_id = int(box.cls[0])
        class_name = result.names[cls_id]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        detected.append({
            "class": class_name,
            "bbox": [x1, y1, x2, y2],
            "conf": round(conf, 2),
            "cls_id": cls_id
        })

    # --- C. 결과 시각화 ---
    for obj in detected:
        x1, y1, x2, y2 = obj["bbox"]
        label = f"{obj['class']} {obj['conf']}"
        color = class_colors.get(obj["cls_id"], (0, 255, 0))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # --- D. JSON 페이로드 조립 ---
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    payload = {
        "timestamp": timestamp,
        "gps": gps_info,
        "robocar_speed": robocar_speed,
        "objects": [
            {
                "class": obj["class"],
                "conf": obj["conf"],
                "bbox": obj["bbox"]
            } for obj in detected
        ]
    }

    # --- E. 결과를 쿠버네티스 서버로 전송 ---
    kube_server_url = "http://localhost:8080/inference"  # 노트북 IP: 192.168.0.10
    try:
        res = requests.post(kube_server_url, json=payload)
        if res.status_code != 200:
            print(f"[전송 실패] {res.status_code}")
    except Exception as e:
        print(f"[POST 오류] {e}")

    # --- F. 디버그용 화면 표시 ---
    cv2.imshow("YOLO Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 종료 처리
cap.release()
cv2.destroyAllWindows()
