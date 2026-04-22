import base64
import datetime
import time

import cv2

from edge_modules.config import (
    CMD_API,
    DIST_API,
    FORWARD_SPEED,
    INFER_HZ,
    JPEG_QUALITY,
    K_TIME,
    POLICY_FILE,
    SEND_INTERVAL,
    STOP_TRIGGER,
    STRAIGHT_ANG,
    TURN_ANG,
)
from edge_modules.navigation_utils import bbox_short_median_distance, pixel_x_to_angle
from edge_modules.robocar_api import send_cmd, send_distance_to_robocar


def infer_loop(
    model,
    class_colors,
    camera_fov_deg,
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
):
    print("[Infer] 시작")
    last_infer = 0.0
    last_send = time.time()

    while not stop_evt.is_set():
        if not frame_q:
            time.sleep(0.005)
            continue

        now = time.time()
        if now - last_infer < (1.0 / INFER_HZ):
            time.sleep(0.001)
            continue

        frame = frame_q[-1].copy()
        result = model.predict(source=frame, conf=0.3, verbose=False)[0]

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
                "cls_id": cls_id,
            })

            color = class_colors.get(cls_id, (0, 255, 0))
            label = f"{class_name} {round(conf, 2)}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if detected:
            result_q.append(frame)
        elif frame is not None:
            result_q.append(frame)

        with lidar_lock:
            angle_min = lidar_cache["angle_min"]
            angle_max = lidar_cache["angle_max"]
            angle_inc = lidar_cache["angle_increment"]
            ranges = list(lidar_cache["ranges"])

        closest_person = None
        if angle_min is not None and angle_inc is not None and len(ranges) > 0 and len(detected) > 0:
            image_w = frame.shape[1]
            best = (float("inf"), None)

            for obj in detected:
                if obj["class"] != "person":
                    continue

                x1, y1, x2, y2 = obj["bbox"]
                cx = (x1 + x2) // 2
                center_angle = pixel_x_to_angle(cx, image_w, camera_fov_deg)

                dist, rep_idx, used_points = bbox_short_median_distance(
                    bbox=obj["bbox"],
                    image_w=image_w,
                    angle_min=angle_min,
                    angle_max=angle_max,
                    angle_inc=angle_inc,
                    ranges=ranges,
                    camera_fov_deg=camera_fov_deg,
                    max_range=12.0,
                    num_samples=100,
                    short_k=3,
                )

                if dist is None:
                    continue

                if dist < best[0]:
                    best = (
                        dist,
                        {
                            "class": obj["class"],
                            "conf": obj["conf"],
                            "bbox": obj["bbox"],
                            "distance": round(dist, 3),
                            "angle": round(__import__('math').degrees(center_angle), 2),
                            "center_x": cx,
                            "center_y": (y1 + y2) // 2,
                            "lidar_idx": rep_idx,
                            "lidar_points_used": used_points,
                        },
                    )

            if best[1] is not None:
                closest_person = best[1]

        if not avoid_state["active"]:
            dist_to_send = closest_person["distance"] if closest_person else None
            send_distance_to_robocar(dist_to_send, DIST_API, POLICY_FILE, last_dist_sent)

        current_stop = bool(closest_person and closest_person["distance"] <= STOP_TRIGGER)

        if (not last_stop_state["value"]) and current_stop and (not avoid_state["active"]):
            avoid_state["active"] = True
            avoid_state["stage"] = 1
            avoid_state["start_time"] = time.time()
            avoid_state["direction"] = 1 if closest_person["center_x"] < frame.shape[1] / 2 else -1
            print("[AVOID] 시작")

        last_stop_state["value"] = current_stop

        if avoid_state["active"]:
            elapsed = time.time() - avoid_state["start_time"]
            stage = avoid_state["stage"]
            direction = avoid_state["direction"]

            cv2.putText(frame, f"AVOID STAGE: {stage}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"DIR: {direction}", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            if stage == 1:
                send_cmd(FORWARD_SPEED, TURN_ANG * direction, CMD_API)
                if elapsed > K_TIME:
                    avoid_state["stage"] = 2
                    avoid_state["start_time"] = time.time()
            elif stage == 2:
                send_cmd(FORWARD_SPEED, -TURN_ANG * direction, CMD_API)
                if elapsed > (2 * K_TIME):
                    avoid_state["stage"] = 3
                    avoid_state["start_time"] = time.time()
            elif stage == 3:
                send_cmd(FORWARD_SPEED, TURN_ANG * direction, CMD_API)
                if elapsed > K_TIME:
                    avoid_state["stage"] = 4
                    avoid_state["start_time"] = time.time()
            elif stage == 4:
                send_cmd(FORWARD_SPEED, STRAIGHT_ANG, CMD_API)
                if elapsed > K_TIME:
                    avoid_state["active"] = False
                    avoid_state["stage"] = 0
                    avoid_state["start_time"] = 0.0
                    send_cmd(0.0, 0.0, CMD_API)
                    print("[AVOID] 종료")

        if now - last_send >= SEND_INTERVAL:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            img_b64 = base64.b64encode(buf).decode('utf-8') if ok else None

            with odom_lock:
                gps = dict(odom_cache["gps"])
                speed = float(odom_cache["speed"])

            payload = {
                "timestamp": timestamp,
                "gps": gps,
                "robocar_speed": speed,
                "objects": [
                    {"class": obj["class"], "conf": obj["conf"], "bbox": obj["bbox"]}
                    for obj in detected
                ],
                "lidar_available": angle_min is not None and angle_inc is not None and len(ranges) > 0,
                "closest_person": closest_person,
                "avoid_active": avoid_state["active"],
                "avoid_stage": avoid_state["stage"],
                "image": img_b64,
            }

            try:
                if send_q.full():
                    send_q.get_nowait()
                send_q.put_nowait(payload)
            except Exception:
                pass

            last_send = now

        last_infer = now

    print("[Infer] 종료")
