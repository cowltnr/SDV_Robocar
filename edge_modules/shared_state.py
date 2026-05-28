import queue
import threading
from collections import deque

frame_q = deque(maxlen=1)
result_q = deque(maxlen=1)
send_q = queue.Queue(maxsize=10)

odom_lock = threading.Lock()
odom_cache = {"gps": {"lat": None, "lon": None}, "speed": 0.0}

lidar_lock = threading.Lock()
lidar_cache = {
    "angle_min": None,
    "angle_max": None,
    "angle_increment": None,
    "ranges": [],
}

stop_evt = threading.Event()

avoid_state = {
    "active": False,
    "stage": 0,
    "start_time": 0.0,
    "direction": 1,
    "wp_mode": False,        # 현재 wp route 주행 중인지
    "wp_selected": None,     # 선택된 wp 이름
}

last_stop_state = {"value": False}
last_dist_sent = {"t": 0.0, "d": None}
