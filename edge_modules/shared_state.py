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

    # waypoint / VLM 상태
    "wp_mode": False,
    "wp_selected": None,
    "waiting_vlm": False,
    "vlm_reason": None,
    "last_trigger_time": 0.0,

    "vlm_failed": False,
    "vlm_failed_reason": None,
}

last_stop_state = {"value": False}
last_dist_sent = {"t": 0.0, "d": None}

intent_state = {
    "goal": None,
    "selected_wp": None,
    "valid": False,
    "feedback": None,
}