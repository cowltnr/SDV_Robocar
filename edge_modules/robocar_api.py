import time
import requests

from edge_modules.policy_utils import allow_send_distance


def send_distance_to_robocar(dist_m, dist_api, policy_file, last_dist_sent, min_interval=0.2, delta=0.05):
    now = time.time()
    prev_t = last_dist_sent["t"]
    prev_d = last_dist_sent["d"]

    if dist_m is None:
        return

    if not allow_send_distance(policy_file):
        print(f"[Policy] ingress-action=drop -> distance 전송 차단 ({dist_m:.2f} m)")
        return

    if now - prev_t < min_interval:
        return

    if (prev_d is not None) and (abs(prev_d - dist_m) < delta):
        return

    try:
        response = requests.post(dist_api, json={"distance": float(dist_m)}, timeout=0.3)
        if response.status_code == 200:
            last_dist_sent["t"] = now
            last_dist_sent["d"] = float(dist_m)
            print(f"[Robocar] distance -> {dist_m:.2f} m 전송 OK")
        else:
            print(f"[Robocar] distance 전송 실패: {response.status_code}")
    except Exception as e:
        print(f"[Robocar] distance 전송 오류: {e}")


def send_cmd(linear, angular, cmd_api):
    try:
        requests.post(
            cmd_api,
            json={
                "linear_x": float(linear),
                "angular_z": float(angular),
            },
            timeout=0.2,
        )
    except Exception as e:
        print("[CMD ERROR]", e)
