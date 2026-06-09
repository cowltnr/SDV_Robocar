import base64
import datetime
import time
import cv2
import subprocess
import requests
import math

from edge_modules.config import (
    INFER_HZ,
    JPEG_QUALITY,
    SEND_INTERVAL,
    ROUTE_SELECT_TRIGGER,
    EMERGENCY_STOP_TRIGGER,
    VLM_SELECT_API,
    VALID_WPS,
)
from edge_modules.navigation_utils import bbox_short_median_distance, pixel_x_to_angle

def publish_string_topic(topic_name, data):
    try:
        subprocess.run(
            [
                "ros2", "topic", "pub", "--once",
                topic_name,
                "std_msgs/msg/String",
                f"{{data: '{data}'}}"
            ],
            check=False
        )
        print(f"[ROS2 PUB] {topic_name} <- {data}")

    except Exception as e:
        print(f"[ROS2 PUB ERROR] {topic_name}: {e}")

def request_wp_from_vlm(frame, closest_person, goal=(21.0, 1.0)):
    ok, buf = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
    )
    image_b64 = base64.b64encode(buf).decode("utf-8") if ok else None

    payload = {
        "image": image_b64,
        "image_width": frame.shape[1],
        "image_height": frame.shape[0],
        "goal": list(goal),
        "obstacle": closest_person,
        "candidate_routes": VALID_WPS,
        "instruction": "Select the safest waypoint route."
    }

    try:
        response = requests.post(
            VLM_SELECT_API,
            json=payload,
            timeout=8.0
        )
        response.raise_for_status()
        result = response.json()

        selected_wp = result.get("selected_wp", None)

        if selected_wp not in VALID_WPS:
            print(f"[VLM] invalid selected_wp={selected_wp}")
            print("[VLM] 유효하지 않은 wp입니다. route를 선택하지 않고 정지 상태를 유지합니다.")
            return None, f"invalid selected_wp: {selected_wp}"

        print(
            f"[VLM] selected_wp={selected_wp}, "
            f"reason={result.get('reason')}"
        )

        return selected_wp, result.get("reason")

    except Exception as e:
        print(f"[VLM ERROR] {e}")
        print("[VLM ERROR] VLM server 연결 실패. route를 선택하지 않고 정지 상태를 유지합니다.")
        return None, f"vlm_error: {e}"

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

    pending_vlm_request = False
    pending_vlm_frame = None
    pending_closest_person = None

    while not stop_evt.is_set():
        if not frame_q:
            time.sleep(0.005)
            continue

        now = time.time()
        if now - last_infer < (1.0 / INFER_HZ):
            time.sleep(0.001)
            continue

        frame = frame_q[-1].copy()

        # =========================================================
        # Pending VLM 처리
        # 이전 loop에서 /navigation_stop을 먼저 보낸 뒤,
        # 이번 loop에서 정지 상태로 VLM을 호출하고 route를 전달한다.
        # =========================================================
        if pending_vlm_request:
            print("[VLM] 정지 상태에서 최적 waypoint를 선택하는 중입니다.")

            selected_wp, reason = request_wp_from_vlm(
                frame=pending_vlm_frame if pending_vlm_frame is not None else frame,
                closest_person=pending_closest_person,
                goal=(21.0, 1.0)
            )

            if selected_wp is None:
                print(f"[VLM] route 선택 실패: {reason}")
                print("[VLM] 로봇은 정지 상태를 유지합니다.")

                avoid_state["wp_mode"] = False
                avoid_state["wp_selected"] = None
                avoid_state["vlm_reason"] = reason
                avoid_state["waiting_vlm"] = False
                avoid_state["active"] = False

                pending_vlm_request = False
                pending_vlm_frame = None
                pending_closest_person = None

                last_infer = now
                continue

            avoid_state["wp_mode"] = True
            avoid_state["wp_selected"] = selected_wp
            avoid_state["vlm_reason"] = reason
            avoid_state["waiting_vlm"] = False
            avoid_state["active"] = False

            print(f"[VLM] 선택 완료: {selected_wp}, reason={reason}")

            # VLM이 정상적으로 wp를 선택한 경우에만 route 전달
            publish_string_topic("/selected_route", selected_wp)

            pending_vlm_request = False
            pending_vlm_frame = None
            pending_closest_person = None

            last_infer = now
            continue

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
                            "angle": round(math.degrees(center_angle), 2),
                            "center_x": cx,
                            "center_y": (y1 + y2) // 2,
                            "lidar_idx": rep_idx,
                            "lidar_points_used": used_points,
                        },
                    )

            if best[1] is not None:
                closest_person = best[1]

        '''if not avoid_state["active"]:
            dist_to_send = closest_person["distance"] if closest_person else None
            send_distance_to_robocar(dist_to_send, DIST_API, POLICY_FILE, last_dist_sent)'''

        route_select_stop = (
                closest_person is not None
                and closest_person.get("distance") is not None
                and closest_person["distance"] <= ROUTE_SELECT_TRIGGER
        )

        emergency_stop = (
                closest_person is not None
                and closest_person.get("distance") is not None
                and closest_person["distance"] <= EMERGENCY_STOP_TRIGGER
        )

        # 1) Emergency stop은 wp 주행 중에도 항상 살아 있어야 함
        if emergency_stop:
            print(f"[EMERGENCY STOP] closest_person={closest_person}")
            publish_string_topic("/navigation_stop", "stop")

        # 2) Route selection은 최초 1회만 VLM에게 요청
        now_t = time.time()
        cooldown_ok = (now_t - avoid_state.get("last_trigger_time", 0.0)) > 2.0

        if (
                route_select_stop
                and cooldown_ok
                and (not avoid_state.get("wp_mode", False))
                and (not avoid_state.get("waiting_vlm", False))
        ):
            print(f"[ROUTE SELECT TRIGGER] closest_person={closest_person}")

            # 1) 먼저 정지 상태로 전환
            avoid_state["active"] = True
            avoid_state["waiting_vlm"] = True
            avoid_state["last_trigger_time"] = now_t

            print("\n[Obstacle] 사람이 route select threshold 이하로 접근했습니다.")
            print("[Obstacle] LIMO를 즉시 정지합니다.")
            publish_string_topic("/navigation_stop", "stop")

            # 2) 이번 loop에서는 VLM 호출과 route publish를 하지 않음
            #    다음 loop에서 정지 상태로 VLM server를 호출
            pending_vlm_request = True
            pending_vlm_frame = frame.copy()
            pending_closest_person = dict(closest_person)

            print("[VLM] 다음 loop에서 정지 상태로 VLM server를 호출합니다.")

            last_stop_state["value"] = route_select_stop
            last_infer = now
            continue

        last_stop_state["value"] = route_select_stop

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
                "avoid_active": avoid_state.get("active", False),
                "avoid_stage": avoid_state.get("stage", 0),

                "route_select_trigger": ROUTE_SELECT_TRIGGER,
                "emergency_stop_trigger": EMERGENCY_STOP_TRIGGER,
                "wp_mode": avoid_state.get("wp_mode", False),
                "vlm_selected_wp": avoid_state.get("wp_selected"),
                "vlm_reason": avoid_state.get("vlm_reason"),
                "waiting_vlm": avoid_state.get("waiting_vlm", False),

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


