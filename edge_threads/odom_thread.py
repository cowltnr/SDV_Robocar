import time
import requests

from edge_modules.navigation_utils import fake_gps_from_odom


def odom_loop(odom_url, timeout_get, stop_evt, odom_lock, odom_cache):
    print("[Odom] 시작")
    poll_period = 0.1

    while not stop_evt.is_set():
        t0 = time.time()
        try:
            response = requests.get(odom_url, timeout=timeout_get)
            if response.status_code == 200:
                odom = response.json()
                x = odom["pose"]["position"]["x"]
                y = odom["pose"]["position"]["y"]
                speed = odom["twist"]["linear"]["x"]
                gps = fake_gps_from_odom(x, y)

                with odom_lock:
                    odom_cache["gps"] = gps
                    odom_cache["speed"] = float(speed)
        except Exception:
            pass

        dt = time.time() - t0
        if dt < poll_period:
            time.sleep(poll_period - dt)

    print("[Odom] 종료")
