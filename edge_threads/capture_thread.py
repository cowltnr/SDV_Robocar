import time
import cv2


def capture_loop(stream_url, frame_q, stop_evt):
    print("[Capture] 시작")
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"[Capture] 스트림 연결 실패: {stream_url}")
        return

    while not stop_evt.is_set():
        ok, frame = cap.read()
        if ok:
            frame_q.append(frame)
        else:
            time.sleep(0.005)

    cap.release()
    print("[Capture] 종료")
