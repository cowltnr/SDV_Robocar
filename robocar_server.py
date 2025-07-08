from flask import Flask, Response, request
import cv2
import time
import threading

# Flask 서버 생성
app = Flask(__name__)

# OpenCV로 카메라 연결 (로보카 카메라 장치 번호에 따라 0 또는 1)
cap = cv2.VideoCapture(0)

# --- 1. MJPEG 스트리밍 ---
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

# --- 3. 서버 실행 ---
if __name__ == "__main__":
    # host='0.0.0.0' → 외부 장치(데스크탑)에서도 접속 가능
    app.run(host='0.0.0.0', port=8000)
