# SDV Robocar Architecture and Static Source Audit

## Document status

This is the top-level architecture map for the ICTC2026 branch. It records a
static source inspection performed on 2026-07-21. Production code is the source
of truth when this document or `README.md` disagrees with it.

## Verification method

The audit used read-only source inspection. No Flask server, ROS2 node, Isaac
Sim process, Ollama process, robot process, or ROS2 topic publisher was started.
The labels used below mean:

- **Verified**: directly established by executable source in this checkout.
- **Partially verified**: some of the statement is implemented, but a defect,
  inactive path, missing enforcement, or unexecuted runtime dependency prevents
  the full statement from being established.
- **Assumption**: documentation, intended deployment behavior, or an operational
  rule that static source does not establish.

The inspection covers repository-owned Python, shell, tests, and documentation.
The untracked embedded `IsaacSim/` installation is a third-party runtime tree and
is not treated as project application source, except for the absolute-path note
below. Static inspection cannot establish that ROS2 topics, HTTP peers, Ollama,
Isaac Sim, sensors, or a physical robot are available at runtime.

## Architecture statement verification

| Architecture statement | Status | Source evidence and qualification |
|---|---|---|
| The system combines camera, 2D LiDAR, odometry, YOLO detection, camera–LiDAR distance estimation, VLM route selection, and waypoint following. | Verified | Sensor subscriptions are in `imo_server_lidar.py:85-147`; YOLO and the five edge workers are initialized in `edge_control.py:36-85`; fusion and person selection are in `edge_threads/infer_thread.py:253-333`; VLM selection is in `edge_threads/infer_thread.py:80-141`; controller publishers are in `waypoint_tools/point_follower.py:10-70` and `waypoint_tools/pure_pursuit_follower.py:9-86`. |
| The robot-side sensor process receives camera, LiDAR, and odometry and exposes them over HTTP. | Verified | `imo_server_lidar.py:49-78` defines the three HTTP routes; `imo_server_lidar.py:85-154` defines the three ROS2 subscriptions; `imo_server_lidar.py:161-178` starts the ROS child process and Flask server. |
| The edge process fetches sensors, runs detection/fusion, performs stop/VLM decisions, and sends logs. | Verified | `edge_control.py:46-85` starts capture, odometry, LiDAR, inference, and sender workers; their I/O is in `edge_threads/capture_thread.py:5-20`, `edge_threads/odom_thread.py:7-32`, `edge_threads/lidar_thread.py:5-29`, `edge_threads/infer_thread.py:253-459`, and `edge_threads/sender_thread.py:5-24`. |
| The VLM server accepts image and obstacle context, restricts output to candidates, and returns a route and reason. | Verified | Request fields are read in `vlm_server.py:78-83` and `vlm_server.py:168-195`; candidate filtering and invalid-output rejection are in `vlm_server.py:173-209`; response fields are in `vlm_server.py:220-233`. |
| Intent processing determines candidate routes and publishes a selected route and feedback. | Partially verified | Candidate calculation and publishing exist at `waypoint_tools/intent_decision.py:52-120` and `waypoint_tools/intent_decision.py:132-206`. The intended shared state is not written for valid intents, and the invalid-intent writer uses an undefined `self.current_intent_state_file` at `waypoint_tools/intent_decision.py:213-245`. |
| Point Follower and Pure Pursuit follow selected routes and publish velocity commands. | Verified | Route subscriptions and `/sim/cmd_vel` publishers are in `waypoint_tools/point_follower.py:35-70` and `waypoint_tools/pure_pursuit_follower.py:48-86`; command publication is at `waypoint_tools/point_follower.py:350-399` and `waypoint_tools/pure_pursuit_follower.py:430-475`. This is source verification only, not live motion validation. |
| The logging server stores edge JSON and synchronized images. | Verified | The edge payload is built at `edge_threads/infer_thread.py:407-451`; the server writes JSON and decodes the image at `k8s_server.py:18-49`. |
| Stored logs are shared with other vehicles. | Assumption | `k8s_server.py:18-53` implements only `POST /inference` and local file writes. No repository endpoint or transport for another vehicle to retrieve or receive the stored state was found. |
| Valid route identifiers are `wp1` through `wp5`. | Verified | The edge and VLM lists are at `edge_modules/config.py:32-34` and `vlm_server.py:9-12`; route definitions export the same identifiers in `waypoint_tools/waypoint_routes/routes.py:1-81`. |
| Invalid or unavailable VLM output keeps the robot stopped and publishes no route. | Partially verified | The failure branch publishes `stop` and records failure at `edge_threads/infer_thread.py:195-207`, and both followers stop for invalid route input at `waypoint_tools/point_follower.py:75-81` and `waypoint_tools/pure_pursuit_follower.py:94-101`. However, unconditional duplicate code then sets waypoint mode and publishes `/selected_route` even when `selected_wp` is `None` at `edge_threads/infer_thread.py:235-244`. |
| A valid goal-aware VLM result publishes only `/selected_route_goal`. | Partially verified | The goal-aware publication exists at `edge_threads/infer_thread.py:220-229`, but the same result is then also unconditionally published on `/selected_route` at `edge_threads/infer_thread.py:235-244`. |
| Only one process publishes `/sim/cmd_vel` at a time. | Assumption | Two separate controllers can create that publisher (`waypoint_tools/point_follower.py:50-64`; `waypoint_tools/pure_pursuit_follower.py:48-64`). No lock, launch constraint, or runtime mutual-exclusion enforcement was found. |
| Emergency-stop behavior remains active during waypoint operation. | Verified | The edge publishes `stop` whenever the emergency threshold is met at `edge_threads/infer_thread.py:339-355`; both followers subscribe to `/navigation_stop` and publish zero velocity on stop at `waypoint_tools/point_follower.py:35-40,220-235,395-399` and `waypoint_tools/pure_pursuit_follower.py:74-80,168-187,471-475`. |
| Offline verification precedes simulator and physical-robot validation. | Assumption | This is an operational policy in `AGENTS.md:52-55` and `docs/safety/robot-safety.md:57-70`; application source cannot enforce the validation sequence. |
| The documented OS, ROS2, Isaac Sim, Python, YOLO, and Ollama versions describe the active runtime. | Assumption | Model names are hard-coded at `edge_control.py:36-38` and `vlm_server.py:11-12`, but static source does not verify installed runtime versions or the active simulator scene. |

## Runtime processes and entry points

### Application and ROS2 entry points

| Process or entry point | Status | Evidence and behavior |
|---|---|---|
| `edge_control.py` | Verified | `main()` at `edge_control.py:36-104`, invoked at `edge_control.py:107-108`; starts five worker threads at `edge_control.py:46-85`. Module import also performs live camera-info and scan reads at `edge_control.py:32-33`. |
| Camera capture worker | Verified | `capture_loop()` at `edge_threads/capture_thread.py:5-20`, launched by `edge_control.py:46-46`. |
| Odometry polling worker | Verified | `odom_loop()` at `edge_threads/odom_thread.py:7-32`, launched by `edge_control.py:47-51`. |
| LiDAR polling worker | Verified | `lidar_loop()` at `edge_threads/lidar_thread.py:5-29`, launched by `edge_control.py:52-56`. |
| Inference/decision worker | Verified | `infer_loop()` at `edge_threads/infer_thread.py:143-459`, launched by `edge_control.py:57-76`. |
| Logging sender worker | Verified | `sender_loop()` at `edge_threads/sender_thread.py:5-24`, launched by `edge_control.py:77-81`. |
| `imo_server_lidar.py` | Verified | Main block at `imo_server_lidar.py:161-178`; starts a ROS2 subscription process and Flask on port 8000. |
| `k8s_server.py` | Verified | Main block at `k8s_server.py:55-57`; starts Flask on port 8080. |
| `vlm_server.py` | Verified | Main block at `vlm_server.py:236-237`; starts threaded Flask on port 8090. |
| `imo_control.py` | Verified | Main block at `imo_control.py:183-193`; starts a ROS thread plus threaded Flask on port 8001. Its ROS output topic is `/cmd_vel`, not `/sim/cmd_vel` (`imo_control.py:36-68`). |
| `intent_server.py` | Verified | `app.run()` is unconditional at `intent_server.py:26-26`; importing this module starts Flask on port 5000 because there is no `__main__` guard. |
| `waypoint_tools/intent_decision.py` | Verified | ROS2 `main()` and main guard at `waypoint_tools/intent_decision.py:260-276`. |
| `waypoint_tools/point_follower.py` | Verified | ROS2 `main()` and main guard at `waypoint_tools/point_follower.py:402-417`. |
| `waypoint_tools/pure_pursuit_follower.py` | Verified | ROS2 `main()` and main guard at `waypoint_tools/pure_pursuit_follower.py:481-496`. |
| `waypoint_tools/marker.py` | Verified | ROS2 `main()` and main guard at `waypoint_tools/marker.py:174-188`. |
| `sensor/lidar_length.py` | Verified | Standalone diagnostic main block at `sensor/lidar_length.py:63-65`; the callable reader is at `sensor/lidar_length.py:34-60`. |
| `sensor/camera_fov.py` | Verified | Callable ROS2 diagnostic entry `get_camera_hfov()` is at `sensor/camera_fov.py:31-50`; it has no standalone main block and is invoked during `edge_control.py` import. |

### Offline evaluation and harness entry points

| Entry point | Status | Evidence |
|---|---|---|
| Stop-count calculation | Verified | `ictc_test/stop_count_test/calculate_stop_count.py:115-176`. |
| Stop-count plotting | Verified | The module executes at import from `ictc_test/stop_count_test/plot_stop_count.py:1-158`; it has no main guard. |
| Tracking-error calculation | Verified | `ictc_test/tracking_error_test/calculate_tracking_error.py:130-206`. |
| Per-route trajectory plotting | Verified | `ictc_test/trajectory_test/plot_trajectory.py:264-267`. |
| Combined trajectory plotting | Verified | The module executes at import from `ictc_test/trajectory_test/plot_trajectory_2x3.py:1-50`; it has no main guard. |
| Travel-time calculation | Verified | `ictc_test/travel_time_test/calculate_travel_time.py:70-129`. |
| Per-route velocity plotting | Verified | `ictc_test/velocity_profile_test/plot_velocity_profile.py:186-192`. |
| Combined velocity plotting | Verified | The module executes at import from `ictc_test/velocity_profile_test/plot_velocity_profile_2x3.py:1-53`; it has no main guard. |
| VLM route-switch plotting | Verified | `ictc_test/vlm_suggestion_test/plot_vlm_trajectory.py:123-413`. |
| General validation harness | Verified | `scripts/check.sh:1-45` compiles project Python and invokes the offline tests. |
| Offline unit harness | Verified | `scripts/test_offline.sh:1-14` runs `unittest` discovery under `tests/unit`. |

## ROS2 interface inventory

### Explicit publishers

| Topic and type | Publisher | Status | Evidence |
|---|---|---|---|
| `/navigation_stop` (`std_msgs/String`) | One-shot `ros2 topic pub` subprocesses from the inference worker | Verified | Publisher helper: `edge_threads/infer_thread.py:23-37`; stop calls: `edge_threads/infer_thread.py:195-200,351-376`. |
| `/selected_route` (`std_msgs/String`) | One-shot subprocesses from inference; persistent publisher from intent decision | Partially verified | Inference calls: `edge_threads/infer_thread.py:220-244`; intent publisher: `waypoint_tools/intent_decision.py:18-42,102-104`. The inference path may publish `None` and duplicates valid goal-aware results. |
| `/selected_route_goal` (`std_msgs/String`) | One-shot subprocess from inference | Verified | `edge_threads/infer_thread.py:220-227`. |
| `/intent_feedback` (`std_msgs/String`) | Intent decision | Verified | `waypoint_tools/intent_decision.py:18-42,208-211`. |
| `/sim/cmd_vel` (`geometry_msgs/Twist`) | Point Follower | Verified | Creation: `waypoint_tools/point_follower.py:15-15,50-51`; moving and stop publications: `waypoint_tools/point_follower.py:350-399`. |
| `/sim/cmd_vel` (`geometry_msgs/Twist`) | Pure Pursuit | Verified | Creation: `waypoint_tools/pure_pursuit_follower.py:14-14,48-49`; moving and stop publications: `waypoint_tools/pure_pursuit_follower.py:430-475`. |
| `/cmd_vel` (`geometry_msgs/Twist`) | Flask/ROS LIMO controller | Verified | `imo_control.py:36-68`. This is not `/sim/cmd_vel`. |
| `/waypoint_markers` (`visualization_msgs/MarkerArray`) | Waypoint viewer | Verified | `waypoint_tools/marker.py:7-12,108-171`. |

### Explicit subscribers

| Topic and type | Subscriber | Status | Evidence |
|---|---|---|---|
| `/sim/odom` (`nav_msgs/Odometry`) | Robot sensor streamer | Verified | `imo_server_lidar.py:85-93`. |
| `/sim/camera/color/image_raw` (`sensor_msgs/Image`) | Robot sensor streamer | Verified | `imo_server_lidar.py:94-95,139-147`. |
| `/sim/scan` (`sensor_msgs/LaserScan`) | Robot sensor streamer | Verified | `imo_server_lidar.py:97-104,124-137`. |
| `/sim/camera/camera_info` (`sensor_msgs/CameraInfo`) | Camera FOV reader | Verified | `sensor/camera_fov.py:7-18,31-50`. |
| `/sim/scan` (`sensor_msgs/LaserScan`) | LiDAR length reader | Verified | `sensor/lidar_length.py:6-19,34-60`. |
| `/user_intent_goal` (`std_msgs/String`) | Intent decision | Verified | `waypoint_tools/intent_decision.py:18-30`. |
| `/selected_route` (`std_msgs/String`) | Point Follower and Pure Pursuit | Verified | `waypoint_tools/point_follower.py:50-57`; `waypoint_tools/pure_pursuit_follower.py:51-57`. |
| `/selected_route_goal` (`std_msgs/String`) | Point Follower and Pure Pursuit | Verified | `waypoint_tools/point_follower.py:59-64`; `waypoint_tools/pure_pursuit_follower.py:59-64`. |
| `/navigation_stop` (`std_msgs/String`) | Point Follower and Pure Pursuit | Verified | `waypoint_tools/point_follower.py:35-40`; `waypoint_tools/pure_pursuit_follower.py:74-80`. |
| `/tf` and `/tf_static` (implicit TF2 subscriptions) | Point Follower and Pure Pursuit transform listeners | Partially verified | Listener creation is explicit at `waypoint_tools/point_follower.py:66-68` and `waypoint_tools/pure_pursuit_follower.py:82-84`; topic creation occurs internally in TF2 and was not live-inspected. |
| `/intent_goal` | Commented-out follower subscriptions | Assumption | The blocks are inactive at `waypoint_tools/point_follower.py:28-33` and `waypoint_tools/pure_pursuit_follower.py:66-72`; this is not a current interface. |

No application subscriber for `/intent_feedback` or `/waypoint_markers` was
found. ROS2 CLI one-shot publications create transient publisher processes; the
inference worker itself is not an `rclpy` node (`edge_threads/infer_thread.py:23-37`).

## HTTP interface inventory

### Incoming server endpoints

| Bind port | Method and path | Process | Status | Evidence |
|---:|---|---|---|---|
| 8000 | `GET /video` | `imo_server_lidar.py` | Verified | Route at `imo_server_lidar.py:33-51`; bind at `imo_server_lidar.py:161-177`. |
| 8000 | `GET /odometry` | `imo_server_lidar.py` | Verified | `imo_server_lidar.py:54-61`. |
| 8000 | `GET /lidar` | `imo_server_lidar.py` | Verified | `imo_server_lidar.py:64-78`. |
| 8080 | `POST /inference` | `k8s_server.py` | Verified | `k8s_server.py:18-53,55-57`. |
| 8090 | `GET /health` | `vlm_server.py` | Verified | `vlm_server.py:158-165,236-237`. |
| 8090 | `POST /select_wp` | `vlm_server.py` | Verified | `vlm_server.py:168-233,236-237`. |
| 8001 | `POST /control/distance` | `imo_control.py` | Verified | `imo_control.py:80-111,183-191`. |
| 8001 | `POST /control/cmd_vel` | `imo_control.py` | Verified | `imo_control.py:117-148,183-191`. |
| 8001 | `GET /control/state` | `imo_control.py` | Verified | `imo_control.py:154-158,183-191`. |
| 5000 | `POST /receive_policy` | `intent_server.py` | Verified | `intent_server.py:4-26`. |

Flask supplies `HEAD` automatically for the GET routes and commonly supplies
`OPTIONS`; the table records only methods declared by project source.

### Outbound HTTP dependencies

| Destination | Caller | Status | Evidence |
|---|---|---|---|
| `http://192.168.50.17:8000/video` | Edge camera worker | Verified | URL construction: `edge_modules/config.py:1-6`; use: `edge_threads/capture_thread.py:5-19`. |
| `http://192.168.50.17:8000/odometry` | Edge odometry worker | Verified | `edge_modules/config.py:1-6`; `edge_threads/odom_thread.py:7-25`. |
| `http://192.168.50.17:8000/lidar` | Edge LiDAR worker | Verified | `edge_modules/config.py:1-6`; `edge_threads/lidar_thread.py:5-23`. |
| `http://localhost:8080/inference` | Edge sender | Verified | `edge_modules/config.py:2-7`; `edge_threads/sender_thread.py:5-20`. |
| `http://localhost:8090/select_wp` | Edge inference | Verified | `edge_modules/config.py:2-10`; `edge_threads/infer_thread.py:114-141`. |
| `http://localhost:11434/api/chat` | VLM server | Verified | `vlm_server.py:11-12,130-155`. |
| `http://192.168.50.17:8001/control/distance` | Reusable robot-control helper | Partially verified | URL and helper: `edge_modules/config.py:8-9`; `edge_modules/robocar_api.py:7-34`. The only inference call is inside an inactive triple-quoted block at `edge_threads/infer_thread.py:335-337`. |
| `http://192.168.50.17:8001/control/cmd_vel` | Reusable robot-control helper | Partially verified | URL and helper: `edge_modules/config.py:8-9`; `edge_modules/robocar_api.py:37-48`. No active caller was found. |

## `/sim/cmd_vel` publisher inventory

Exactly two repository-owned files can create a `/sim/cmd_vel` publisher:

| File | Status | Evidence |
|---|---|---|
| `waypoint_tools/point_follower.py` | Verified | Topic selection and publisher creation at `waypoint_tools/point_follower.py:15-15,50-51`; publish sites at `waypoint_tools/point_follower.py:393-399`. |
| `waypoint_tools/pure_pursuit_follower.py` | Verified | Topic selection and publisher creation at `waypoint_tools/pure_pursuit_follower.py:14-14,48-49`; publish sites at `waypoint_tools/pure_pursuit_follower.py:469-475`. |

`imo_control.py` is a velocity publisher, but it publishes `/cmd_vel`, not
`/sim/cmd_vel` (`imo_control.py:36-68`). Offline evaluation files mentioning
`/sim/cmd_vel` only read recorded bags, for example
`ictc_test/stop_count_test/calculate_stop_count.py:20-34` and
`ictc_test/velocity_profile_test/plot_velocity_profile.py:28-53`.

## VLM failure and timeout handling

| Finding | Status | Evidence |
|---|---|---|
| The edge rejects an empty filtered candidate list without calling the VLM. | Verified | `edge_threads/infer_thread.py:80-95`. |
| The edge request timeout is 60 seconds; HTTP errors, JSON errors, and timeouts are caught together and returned as `(None, reason)`. | Verified | `edge_threads/infer_thread.py:114-141`. |
| The VLM server's Ollama timeout is 180 seconds. Exceptions, including timeout or malformed Ollama JSON, become HTTP 200 with `selected_wp: null`. | Verified | `vlm_server.py:130-155,226-233`. |
| VLM text is parsed as JSON first, then searched for any `wp1`–`wp5` token. | Verified | `vlm_server.py:14-58`. |
| The server filters request candidates and rejects parsed routes outside that set. | Verified | `vlm_server.py:168-209`. |
| The edge independently rejects a server-selected route outside the current candidate set. | Verified | `edge_threads/infer_thread.py:121-136`. |
| Failure sends another `/navigation_stop` command and sets failure fields. | Verified | `edge_threads/infer_thread.py:195-207`. |
| Failure publishes no route and leaves consistent failure state. | Partially verified | Contradicted by unconditional code at `edge_threads/infer_thread.py:235-244`, which changes `wp_mode` to true and publishes `/selected_route` with `None`. Followers reject that unknown route and publish zero velocity (`waypoint_tools/point_follower.py:75-81`; `waypoint_tools/pure_pursuit_follower.py:94-101`), so static source supports stopping but not the “no route publication” or consistent-state claims. |
| Successful goal-aware selection preserves the goal endpoint. | Partially verified | `/selected_route_goal` is published at `edge_threads/infer_thread.py:220-227`, but the unconditional `/selected_route` publication at `edge_threads/infer_thread.py:235-244` can subsequently select the full route in both followers. |

The 60-second edge timeout is shorter than the server's 180-second Ollama
timeout. Therefore, the edge can time out and remain stopped while the server
continues waiting for Ollama; there is no cancellation protocol in source.

## Inter-module JSON contracts

| Producer → consumer | Fields used by the consumer | Status | Evidence and enforcement |
|---|---|---|---|
| Sensor server `/odometry` → edge odometry worker | `pose.position.x`, `pose.position.y`, `twist.linear.x`; server also emits `timestamp`, full position/orientation, and full linear/angular twist | Verified | Producer: `imo_server_lidar.py:106-122`; direct-index consumer: `edge_threads/odom_thread.py:14-24`. The three consumed values are required for a successful update. |
| Sensor server `/lidar` → edge LiDAR worker/inference | `angle_min`, `angle_max`, `angle_increment`, `ranges`; server also emits `ready`, `timestamp`, `stamp_sec` | Partially verified | Producer: `imo_server_lidar.py:124-137`; consumer: `edge_threads/lidar_thread.py:12-19`; use: `edge_threads/infer_thread.py:281-333`. Consumer `.get()` calls tolerate missing fields but disable or degrade fusion, so no formal validator exists. |
| Intent node → `/tmp/current_intent_state.json` → edge inference | Intended fields: `timestamp`, `goal`, `selected_wp`, `candidate_routes`, `valid`, `feedback` | Partially verified | Intended producer shape: `waypoint_tools/intent_decision.py:213-237`; consumer/defaults: `edge_threads/infer_thread.py:39-78`. Valid intents never call the writer (`waypoint_tools/intent_decision.py:96-120`), and invalid intents use an undefined path attribute (`waypoint_tools/intent_decision.py:84-92,231-245`). |
| Edge inference → VLM `/select_wp` | Request emits `image`, `image_width`, `image_height`, `goal`, `obstacle`, `candidate_routes`, `instruction` | Verified | Producer: `edge_threads/infer_thread.py:97-118`; consumer uses all except `instruction`: `vlm_server.py:78-127,168-195`. Candidate routes are the only safety-critical validated request field. |
| VLM server → edge inference | `selected_wp` is required for success; `reason` is optional; server may also emit `raw_answer` | Verified | Producer variants: `vlm_server.py:181-185,205-209,220-233`; consumer: `edge_threads/infer_thread.py:121-141`. |
| Edge inference → logging server `/inference` | Edge emits `timestamp`, `gps`, `robocar_speed`, `objects`, `lidar_available`, `closest_person`, `avoid_active`, `avoid_stage`, `route_select_trigger`, `emergency_stop_trigger`, `current_goal`, `current_goal_candidate_routes`, `current_goal_selected_wp`, `wp_mode`, `vlm_selected_wp`, `vlm_reason`, `waiting_vlm`, `vlm_failed`, `vlm_failed_reason`, `image` | Partially verified | Producer: `edge_threads/infer_thread.py:407-451`. `k8s_server.py:18-49` accepts and stores any JSON object; only `timestamp`, `image`, and `objects` are accessed, all with defaults or optional checks. There is no required-field or schema validation. |
| Edge helper → controller `/control/distance` | Request: required `distance`; response: `ok`, `distance`, `e_stop` or `ok`, `error` | Partially verified | Caller: `edge_modules/robocar_api.py:7-34`; endpoint: `imo_control.py:80-111`. The active inference call is disabled at `edge_threads/infer_thread.py:335-337`. |
| Edge helper → controller `/control/cmd_vel` | Request: optional `linear_x`, `angular_z`; response echoes `ok`, `linear_x`, `angular_z` or `ok`, `error` | Partially verified | Caller: `edge_modules/robocar_api.py:37-48`; endpoint: `imo_control.py:117-148`. No active caller was found. |
| Policy server → policy reader | YAML path and nested keys `i2nsf-security-policy.rules.action.packet-action.ingress-action` | Partially verified | Writer: `intent_server.py:6-20`; reader: `edge_modules/policy_utils.py:4-13`; configured relative read path: `edge_modules/config.py:12-12`. Writer and reader paths do not match under normal repository execution. |

Object entries emitted to logging contain `class`, `conf`, and `bbox`; the
closest-person object additionally contains `distance`, `angle`, `center_x`,
`center_y`, `lidar_idx`, and `lidar_points_used`
(`edge_threads/infer_thread.py:264-269,300-329,418-445`). The code stores
`angle` in degrees (`edge_threads/infer_thread.py:298-324`).

## Hard-coded paths and locations

| Location | Status | Evidence and impact |
|---|---|---|
| `/tmp/current_intent_state.json` | Verified | Hard-coded in `edge_threads/infer_thread.py:39-39`. The intent node does not initialize its corresponding instance attribute (`waypoint_tools/intent_decision.py:11-50,213-245`). |
| `/received_policy.yaml` | Verified | Hard-coded write destination at `intent_server.py:18-20`; it differs from the relative `received_policy.yaml` read path at `edge_modules/config.py:12-12`. |
| `/home/cowltnr/PycharmProjects/SDV_Robocar/IsaacSim/bin/python3` | Verified | Absolute shebang at `IsaacSim/bin/jp.py:1-1`. `IsaacSim/` is untracked embedded third-party/runtime content, not project-owned application source. |
| `~/nav2_ws`, `~/SDV_Robocar`, and `~/PycharmProjects/SDV_Robocar` | Assumption | Deployment paths appear in `README.md:356-362,397-416,431-457,492-547`; source does not establish that any exists, and the README uses inconsistent repository locations. |
| `http://192.168.50.17`, `http://localhost`, and fixed ports | Verified | Hard-coded network locations are in `edge_modules/config.py:1-10` and `vlm_server.py:11-12`. They are locations rather than filesystem paths, but are deployment-specific constants. |

Project-owned production code otherwise uses relative locations for model,
policy, and log files (`edge_control.py:36-38`; `edge_modules/config.py:12-12`;
`k8s_server.py:10-16`). The offline evaluation scripts derive paths from
`Path(__file__).resolve()` rather than embedding a user home path.

## Documentation and code mismatches

| Mismatch | Status | Evidence |
|---|---|---|
| README says `ROUTE_SELECT_TRIGGER = 4.0`; code uses `6.0`. | Verified | `README.md:140-145`; `edge_modules/config.py:32-34`. |
| README says an invalid/unavailable VLM result publishes no route; inference unconditionally publishes `/selected_route` after both success and failure. | Verified | Documentation: `README.md:135-136`; code: `edge_threads/infer_thread.py:195-244`. |
| README says goal-aware VLM navigation publishes `/selected_route_goal`; code also publishes `/selected_route`, allowing followers to replace the goal-trimmed route with a full route. | Verified | Documentation: `README.md:207-214,564-570`; code: `edge_threads/infer_thread.py:220-244`; follower callbacks: `waypoint_tools/point_follower.py:75-117` and `waypoint_tools/pure_pursuit_follower.py:94-129`. |
| README says publishing the user goal should create `/tmp/current_intent_state.json`; current intent code does not write valid intents and cannot write invalid intents through the undefined path attribute. | Verified | Documentation: `README.md:526-543`; code: `waypoint_tools/intent_decision.py:74-120,213-245`. |
| README describes cloud logs as shared with other vehicles; code only writes local files and exposes no read/share endpoint. | Verified | Documentation: `README.md:5-5,291-311`; code: `k8s_server.py:18-57`. |
| README warns that `imo_control.py` also publishes the simulator velocity topic; code publishes `/cmd_vel`, while the followers publish `/sim/cmd_vel`. | Verified | Documentation: `README.md:403-403`; code: `imo_control.py:36-68`, `waypoint_tools/point_follower.py:15-51`, and `waypoint_tools/pure_pursuit_follower.py:14-49`. |
| README recommends package-qualified route imports, but Pure Pursuit and marker use `from waypoint_routes...` while Point Follower and intent decision use `from waypoint_tools.waypoint_routes...`. | Verified | Documentation: `README.md:388-392`; source: `waypoint_tools/pure_pursuit_follower.py:7-7`, `waypoint_tools/marker.py:5-5`, `waypoint_tools/point_follower.py:7-7`, `waypoint_tools/intent_decision.py:5-5`. Which form works depends on the external ROS2 package layout and was not live-tested. |
| README describes the logged closest-person `angle` without a unit; source records degrees. | Partially verified | Example: `README.md:103-114`; calculation: `edge_threads/infer_thread.py:298-324`. The example value cannot be validated without its original sensor frame. |

## Remaining assumptions and limitations

- **Assumption:** Exact QoS compatibility with Isaac Sim publishers; only the
  subscriber-side settings are visible (`imo_server_lidar.py:88-104`).
- **Assumption:** Runtime TF frame availability for `odom` and `base_link`; the
  followers request these frames but no broadcaster is defined in repository
  source (`waypoint_tools/point_follower.py:15-18,66-68`;
  `waypoint_tools/pure_pursuit_follower.py:14-16,82-84`).
- **Assumption:** The external ROS2 workspace installs `waypoint_tools` with an
  import layout compatible with all four node files; no tracked `setup.py`,
  `setup.cfg`, or ROS package manifest exists in this checkout.
- **Partially verified:** Emergency-stop source behavior is present, but no live
  ROS2, replay, Isaac Sim, or physical test was authorized in this audit.
- **Partially verified:** HTTP handlers and clients were inspected statically;
  endpoint availability, bind conflicts, authentication, and network reachability
  were not tested.
