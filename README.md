# SDV Robocar

Camera–2D LiDAR fusion, obstacle-aware stopping, VLM-based route selection, and waypoint following framework for a LIMO robot in Isaac Sim / ROS2.

## Environment

```text
Ubuntu 22.04
ROS2 Humble
NVIDIA Isaac Sim 4.5.0
Python 3.10
YOLOv8s
```

## Main Figure

![System overview](Figure2.png)

## Overview

This project connects a simulated or real LIMO robot with an edge perception server, a logging server, and waypoint-based navigation modules.

The robot-side server publishes camera, odometry, and LiDAR data through Flask endpoints. The edge server receives those streams, runs YOLO detection, estimates the distance to detected people by mapping camera bounding boxes to 2D LiDAR angles, and sends structured JSON logs to the cloud/logging server.

When a person is detected within the route-selection threshold, the edge server first publishes a stop command to `/navigation_stop`. Then it requests a waypoint route from a VLM selection server through `/select_wp`. The selected route is published to ROS2 so that a waypoint follower can continue navigation through an alternative path.

## Repository Structure

```text
SDV_Robocar/
├── detector/                  # YOLO model files
├── edge_control.py             # Main edge-side launcher
├── edge_modules/
│   ├── config.py               # URLs, thresholds, VLM API, waypoint names
│   ├── navigation_utils.py     # GPS conversion and Camera–LiDAR mapping utilities
│   ├── shared_state.py         # Shared queues and runtime state
│   ├── policy_utils.py
│   └── robocar_api.py
├── edge_threads/
│   ├── capture_thread.py       # Camera stream receiver
│   ├── odom_thread.py          # Odometry receiver
│   ├── lidar_thread.py         # LiDAR receiver
│   ├── infer_thread.py         # YOLO + LiDAR fusion + VLM route trigger
│   └── sender_thread.py        # JSON/image sender to cloud server
├── sensor/
│   ├── camera_fov.py           # CameraInfo-based horizontal FOV helper
│   └── lidar_length.py         # LaserScan length helper
├── waypoint_tools/
│   ├── marker.py               # RViz route and coordinate markers
│   ├── point_follower.py       # Waypoint-by-waypoint route follower
│   ├── pure_pursuit_follower.py# Pure Pursuit route follower
│   ├── intent_decision.py      # Goal-to-route decision node
│   └── waypoint_routes/
│       └── routes.py           # wp1~wp5 route coordinates
├── imo_server_lidar.py         # Robot-side Flask + ROS2 sensor streaming server
├── imo_control.py              # Optional Flask + ROS2 cmd_vel controller
├── k8s_server.py               # JSON/image logging server
├── intent_server.py            # YAML policy receiver
└── README.md
```

> Note: In the current test setup, the ROS2 `waypoint_tools` package may also be maintained separately under `~/nav2_ws/src/waypoint_tools`. In that case, edit and build the package in `~/nav2_ws`, not only the copy inside this repository.

## Core Modules

### 1. Robot Sensor Server

`imo_server_lidar.py` subscribes to Isaac Sim / ROS2 topics and exposes them through Flask.

ROS2 subscriptions:

```text
/sim/camera/color/image_raw
/sim/odom
/sim/scan
```

Flask endpoints:

```text
GET /video      # MJPEG camera stream
GET /odometry   # Latest odometry JSON
GET /lidar      # Latest LaserScan JSON
```

### 2. Edge Perception and Decision

`edge_control.py` launches the edge-side threads:

```text
capture_loop  -> receives camera stream
odom_loop     -> receives odometry
lidar_loop    -> receives LiDAR
infer_loop    -> YOLO detection + Camera–LiDAR distance estimation + VLM trigger
sender_loop   -> sends logs to cloud server
```

The inference thread performs:

1. YOLOv8 object detection.
2. Person bounding box extraction.
3. Pixel-to-angle conversion using camera horizontal FOV.
4. LiDAR index matching using `angle_min` and `angle_increment`.
5. Median of the closest valid LiDAR samples inside the bounding box.
6. Stop trigger and VLM route-selection trigger.

Main thresholds are defined in `edge_modules/config.py`:

```python
ROUTE_SELECT_TRIGGER = 4.0      # Request VLM route selection when person distance <= 4 m
EMERGENCY_STOP_TRIGGER = 1.2    # Always stop when person distance <= 1.2 m
VALID_WPS = ["wp1", "wp2", "wp3", "wp4", "wp5"]
VLM_SELECT_API = "http://localhost:8090/select_wp"
```

### 3. VLM Route Selection

When a person is detected within the route-selection threshold, the edge server publishes:

```text
/navigation_stop <- stop
```

Then it sends a request to the VLM route-selection server:

```text
POST http://localhost:8090/select_wp
```

Expected request fields:

```json
{
  "image": "base64 encoded image",
  "image_width": 1280,
  "image_height": 720,
  "goal": [21.0, 1.0],
  "obstacle": {
    "class": "person",
    "conf": 0.86,
    "bbox": [564, 1, 699, 423],
    "distance": 3.449,
    "angle": -0.42,
    "center_x": 631,
    "center_y": 212
  },
  "candidate_routes": ["wp1", "wp2", "wp3", "wp4", "wp5"]
}
```

Expected response:

```json
{
  "selected_wp": "wp2",
  "reason": "The obstacle is near the center, so an alternative route is safer."
}
```

After receiving a valid route, the edge server publishes:

```text
/selected_route <- wp_name
```

For goal-aware navigation, use `/selected_route_goal` in the form below:

```text
/selected_route_goal <- wp_name;x,y
```

### 4. Waypoint Navigation

The route coordinates are stored in:

```text
waypoint_tools/waypoint_routes/routes.py
```

Available routes:

```text
wp1, wp2, wp3, wp4, wp5
```

Waypoint tools:

```text
marker.py                # Visualize route lines, points, labels, and coordinates in RViz
point_follower.py        # Follow route point-by-point
pure_pursuit_follower.py # Follow route using Pure Pursuit
intent_decision.py       # Select a route that contains the user goal point
```

The Pure Pursuit follower subscribes to:

```text
/selected_route
/selected_route_goal
/navigation_stop
```

It publishes velocity commands to:

```text
/sim/cmd_vel
```

Do not run multiple `/sim/cmd_vel` publishers at the same time. For example, do not run `imo_control.py` and `pure_pursuit_follower.py` together unless only one of them is allowed to publish control commands.

### 5. Cloud / Logging Server

`k8s_server.py` receives structured inference results and saves them in real time.

Endpoint:

```text
POST /inference
```

Saved outputs:

```text
logs/json/<timestamp>.json
logs/images/<timestamp>.jpg
```

Example logged fields:

```json
{
  "timestamp": "2026-06-10_12-30-00",
  "gps": {"lat": 37.501, "lon": 127.036},
  "robocar_speed": 0.0,
  "objects": [],
  "lidar_available": true,
  "closest_person": null,
  "avoid_active": false,
  "avoid_stage": 0,
  "route_select_trigger": 4.0,
  "emergency_stop_trigger": 1.2,
  "wp_mode": false,
  "vlm_selected_wp": null,
  "vlm_reason": null,
  "waiting_vlm": false,
  "image": "base64 encoded image"
}
```

## Execution Flow

### 1. Start Isaac Sim / ROS2 simulation

Make sure the following ROS2 topics are being published:

```bash
ros2 topic list
```

Required topics:

```text
/sim/camera/color/image_raw
/sim/camera/camera_info
/sim/odom
/sim/scan
```

### 2. Run robot-side sensor server

```bash
cd ~/PycharmProjects/SDV_Robocar
python imo_server_lidar.py
```

### 3. Run cloud/logging server

```bash
cd ~/PycharmProjects/SDV_Robocar
python k8s_server.py
```

### 4. Run VLM route-selection server

Run a server compatible with:

```text
POST http://localhost:8090/select_wp
```

If using Ollama-based VLM selection, start Ollama first:

```bash
ollama serve
```

Then run the VLM server:

```bash
cd ~/PycharmProjects/SDV_Robocar
python vlm_server.py
```

### 5. Run waypoint follower

If `waypoint_tools` is used as a ROS2 package under `~/nav2_ws/src/waypoint_tools`, build it first:

```bash
cd ~/nav2_ws
colcon build --symlink-install --packages-select waypoint_tools
source install/setup.bash
```

Run one follower only:

```bash
ros2 run waypoint_tools pure_pursuit_follower
```

Optional RViz marker publisher:

```bash
ros2 run waypoint_tools marker
```

Optional goal-to-route decision node:

```bash
ros2 run waypoint_tools intent_decision
```

Send a user goal point:

```bash
ros2 topic pub --once /user_intent_goal std_msgs/msg/String "{data: '11.0,0.0'}"
```

### 6. Run edge controller

```bash
cd ~/PycharmProjects/SDV_Robocar
python edge_control.py
```

### 7. Optional: run direct IMO controller

Use this only when a waypoint follower is not publishing `/sim/cmd_vel`.

```bash
cd ~/PycharmProjects/SDV_Robocar
python imo_control.py
```

## ROS2 Topics

| Topic | Type | Publisher | Subscriber | Purpose |
|---|---|---|---|---|
| `/sim/camera/color/image_raw` | `sensor_msgs/Image` | Isaac Sim | `imo_server_lidar.py` | Camera image input |
| `/sim/camera/camera_info` | `sensor_msgs/CameraInfo` | Isaac Sim | `sensor/camera_fov.py` | Camera FOV calculation |
| `/sim/odom` | `nav_msgs/Odometry` | Isaac Sim | `imo_server_lidar.py`, waypoint followers | Robot pose and speed |
| `/sim/scan` | `sensor_msgs/LaserScan` | Isaac Sim | `imo_server_lidar.py`, `sensor/lidar_length.py` | 2D LiDAR scan |
| `/navigation_stop` | `std_msgs/String` | `infer_thread.py` | waypoint followers | Stop/resume navigation |
| `/selected_route` | `std_msgs/String` | `infer_thread.py`, `intent_decision.py` | waypoint followers | Selected route name |
| `/selected_route_goal` | `std_msgs/String` | goal-aware selector | `pure_pursuit_follower.py` | Selected route with final goal |
| `/user_intent_goal` | `std_msgs/String` | user / cloud / CLI | `intent_decision.py` | User goal point |
| `/intent_feedback` | `std_msgs/String` | `intent_decision.py` | user / monitor | Goal validation feedback |
| `/waypoint_markers` | `visualization_msgs/MarkerArray` | `marker.py` | RViz | Route visualization |
| `/sim/cmd_vel` | `geometry_msgs/Twist` | waypoint follower / controller | Isaac Sim robot | Robot velocity command |

## HTTP Endpoints

| Server               | Port | Endpoint | Method | Purpose |
|----------------------|---:|---|---|---|
| `imo_server_lidar.py` | 8000 | `/video` | GET | Camera MJPEG stream |
| `imo_server_lidar.py` | 8000 | `/odometry` | GET | Latest odometry JSON |
| `imo_server_lidar.py` | 8000 | `/lidar` | GET | Latest LiDAR JSON |
| `k8s_server.py`      | 8080 | `/inference` | POST | Save JSON and image logs |
| `vlm_server.py`       | 8090 | `/select_wp` | POST | Select waypoint route |
| `imo_control.py`     | 8001 | `/control/distance` | POST | Distance-based emergency stop |
| `imo_control.py`     | 8001 | `/control/cmd_vel` | POST | Direct velocity command |
| `imo_control.py`     | 8001 | `/control/state` | GET | Current control state |
| `intent_server.py`   | 5000 | `/receive_policy` | POST | Receive and save YAML policy |

## Notes

- `edge_control.py` initializes camera FOV from `/sim/camera/camera_info` and LiDAR length from `/sim/scan`. Isaac Sim must be playing before launching the edge controller.
- `infer_thread.py` uses the closest valid LiDAR samples inside the YOLO bounding box to reduce distance noise.
- If VLM inference is slow, reduce image size before sending to the VLM server or warm up the model before running the full system.
- If goal-aware route selection is required, ensure that the route candidate list is filtered by the user goal before sending candidates to the VLM server.
- In ROS2 package execution, imports should use package-qualified paths such as `from waypoint_tools.waypoint_routes.routes import ROUTES`.

## Example Manual Commands

Publish a selected route manually:

```bash
ros2 topic pub --once /selected_route std_msgs/msg/String "{data: 'wp2'}"
```

Publish a selected route with a final goal:

```bash
ros2 topic pub --once /selected_route_goal std_msgs/msg/String "{data: 'wp2;11.0,0.0'}"
```

Stop navigation manually:

```bash
ros2 topic pub --once /navigation_stop std_msgs/msg/String "{data: 'stop'}"
```