import time
import requests


def lidar_loop(lidar_url, lidar_timeout, lidar_hz, stop_evt, lidar_lock, lidar_cache):
    print("[LiDAR] 시작")
    period = 1.0 / lidar_hz

    while not stop_evt.is_set():
        t0 = time.time()
        try:
            response = requests.get(lidar_url, timeout=lidar_timeout)
            if response.status_code == 200:
                data = response.json()
                with lidar_lock:
                    lidar_cache["angle_min"] = data.get("angle_min")
                    lidar_cache["angle_max"] = data.get("angle_max")
                    lidar_cache["angle_increment"] = data.get("angle_increment")
                    lidar_cache["ranges"] = data.get("ranges", [])
        except Exception:
            pass

        dt = time.time() - t0
        if dt < period:
            time.sleep(period - dt)

    print("[LiDAR] 종료")
