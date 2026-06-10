import random
import time
import threading

import cv2
from ultralytics import YOLO

from sensor.camera_fov import get_camera_hfov
from sensor.lidar_length import get_lidar_length

from edge_modules.config import LIDAR_HZ, LIDAR_TO, ODOM_URL, STREAM_URL, LIDAR_URL, SERVER_URL, TIMEOUT_GET, TIMEOUT_POST
from edge_modules.shared_state import (
    avoid_state,
    frame_q,
    last_dist_sent,
    last_stop_state,
    lidar_cache,
    lidar_lock,
    odom_cache,
    odom_lock,
    result_q,
    send_q,
    stop_evt,
)
from edge_threads.capture_thread import capture_loop
from edge_threads.infer_thread import infer_loop
from edge_threads.lidar_thread import lidar_loop
from edge_threads.odom_thread import odom_loop
from edge_threads.sender_thread import sender_loop


CAMERA_FOV_DEG = get_camera_hfov()
LIDAR_LEN = get_lidar_length('/sim/scan')


def main():
    model = YOLO("detector/yolov8s.pt")
    class_names = model.names

    random.seed(42)
    class_colors = {
        cls_id: tuple(random.randint(0, 255) for _ in range(3))
        for cls_id in class_names
    }

    th_cap = threading.Thread(target=capture_loop, args=(STREAM_URL, frame_q, stop_evt), daemon=True)
    th_odom = threading.Thread(
        target=odom_loop,
        args=(ODOM_URL, TIMEOUT_GET, stop_evt, odom_lock, odom_cache),
        daemon=True,
    )
    th_lidar = threading.Thread(
        target=lidar_loop,
        args=(LIDAR_URL, LIDAR_TO, LIDAR_HZ, stop_evt, lidar_lock, lidar_cache),
        daemon=True,
    )
    th_inf = threading.Thread(
        target=infer_loop,
        args=(
            model,
            class_colors,
            CAMERA_FOV_DEG,
            frame_q,
            result_q,
            send_q,
            stop_evt,
            odom_lock,
            odom_cache,
            lidar_lock,
            lidar_cache,
            avoid_state,
            last_stop_state,
            last_dist_sent,
        ),
        daemon=True,
    )
    th_send = threading.Thread(
        target=sender_loop,
        args=(SERVER_URL, TIMEOUT_POST, send_q, stop_evt),
        daemon=True,
    )

    threads = [th_cap, th_odom, th_lidar, th_inf, th_send]
    for thread in threads:
        thread.start()

    print(f"[Init] CAMERA_FOV_DEG={CAMERA_FOV_DEG}")
    print(f"[Init] LIDAR_LEN={LIDAR_LEN}")

    try:
        while not stop_evt.is_set():
            if result_q:
                cv2.imshow("YOLO Detection", result_q[-1])

            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_evt.set()
                break

            time.sleep(0.005)
    finally:
        stop_evt.set()
        for thread in threads:
            thread.join(timeout=1.0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()