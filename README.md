> Last updated: 2026-08-15 21:16 KST

# SDV Robocar Framework

Camera–2D LiDAR fusion, obstacle-aware stopping, VLM-based route selection, and waypoint following framework for a LIMO robot in Isaac Sim / ROS2.

This repository implements an edge-to-cloud robotic perception pipeline. A robot-side Flask server streams camera, odometry, and 2D LiDAR data. An edge controller runs YOLOv8 detection, estimates person distance using lightweight Camera–2D LiDAR fusion, triggers emergency stopping or VLM-based route selection, and sends structured JSON/image logs to a cloud logging server. The cloud logs can be reused as shared situational information for other robots, allowing multiple robots to reference detected obstacles, VLM route decisions, and route-selection context.

<img width="1920" height="1080" alt="Figure2" src="https://github.com/user-attachments/assets/88e4196c-bbf9-4bfb-bd2e-1c5031375b75" />


---

## Environment

```text
Ubuntu 22.04
ROS2 Humble
NVIDIA Isaac Sim 4.5.0
Python 3.10
Ultralytics YOLOv8s
Ollama-based VLM server (qwen2.5vl:3b)
```

---


## 1. Framework Overview

This framework connects four functional layers:

1. **Perception**
   - Receives camera, 2D LiDAR, and odometry data from the ego vehicle.
   - Detects dynamic obstacles using a YOLO-based detection model.
   - Estimates obstacle distance by projecting camera bounding boxes onto 2D LiDAR scan angles.
   - Generates a structured perception state containing timestamp, ego pose/speed, detected objects, obstacle distance, and image context.

2. **Decision**
   - Receives user intent and checks whether the requested goal is feasible on the predefined waypoint routes.
   - Stops the ego vehicle when a person or obstacle is detected within the route-selection threshold.
   - Activates the VLM server when the original intent becomes infeasible or blocked.
   - Publishes a behavior command or an alternative route command for the ego vehicle.

3. **VLM Server**
   - Receives the current image, obstacle information, user goal, and candidate waypoint routes.
   - Performs intent-aware context understanding and alternative route reasoning.
   - Returns an alternative waypoint route and a natural-language reason for the decision.

4. **Cloud / Shared Environment Update**
   - Stores perception, decision, and VLM suggestion logs as JSON files.
   - Stores synchronized image frames for later inspection.
   - Shares the updated environment state, obstacle context, selected route, and VLM reasoning with other vehicles.

## 2. Framework Flow

```text
Sensor Input
  └── Camera / 2D LiDAR / Odometry
        ↓
Perception Processing
  └── YOLO Detection + Camera–LiDAR Distance Estimation
        ↓
Perception State
  └── Object class, confidence, bbox, distance, angle, image, ego state
        ↓
Decision Layer
  ├── User Intent Processing
  ├── Intent Feasibility Check
  ├── Safety Stop
  └── VLM Activation
        ↓
VLM Server
  ├── Intent-aware Context Understanding
  ├── Alternative Plan Reasoning
  └── Alternative Suggestion
        ↓
Control
  └── Speed / Steering command through /sim/cmd_vel
        ↓
Environment Update
  └── JSON and image logs shared with other vehicles
```

## 3. Perception Layer

The perception layer receives synchronized sensor information from the ego vehicle and converts it into a compact structured state for decision making and sharing.

### Sensor Inputs

| Sensor | Role |
|---|---|
| Camera | Provides image frames for object detection and VLM context input. |
| 2D LiDAR | Provides range measurements for obstacle distance estimation. |
| Odometry | Provides ego vehicle pose and speed information. |

### Detection Model

| Item | Description |
|---|---|
| Model family | Ultralytics YOLOv8 |
| Model file | `detector/yolov8s.pt` |
| Main target class | `person` |
| Output | object class, confidence score, bounding box |
| Usage in framework | Dynamic obstacle detection and VLM context generation |

The detection model is used to identify people or obstacles in the camera image. For each detected person, the framework extracts the bounding box and maps the bounding box region to the corresponding 2D LiDAR scan indices. The distance is estimated from valid LiDAR samples inside the bounding box region.

### Camera–2D LiDAR Fusion Output

For each closest detected person, the framework stores:

```json
{
  "class": "person",
  "conf": 0.86,
  "bbox": [564, 1, 699, 423],
  "distance": 3.449,
  "angle": -0.42,
  "center_x": 631,
  "center_y": 212,
  "lidar_idx": 1616,
  "lidar_points_used": 86
}
```

## 4. Decision Layer

The decision layer determines whether the ego vehicle can continue the current user intent or needs to stop and request an alternative route.

### Decision Conditions

| Condition | Action |
|---|---|
| No obstacle within threshold | Continue waypoint following. |
| Person distance ≤ route-selection threshold | Publish `/navigation_stop <- stop` and activate VLM route selection. |
| Person distance ≤ emergency-stop threshold | Stop immediately regardless of VLM result. |
| VLM returns valid route | Publish selected route to the waypoint follower. |
| VLM fails or returns invalid route | Keep the robot stopped and do not publish a route. |

The main decision parameters are configured in `edge_modules/config.py`:

```python
ROUTE_SELECT_TRIGGER = 4.0
EMERGENCY_STOP_TRIGGER = 1.2
VALID_WPS = ["wp1", "wp2", "wp3", "wp4", "wp5"]
VLM_SELECT_API = "http://localhost:8090/select_wp"
```
<img width="400" height="300" alt="image" src="https://github.com/user-attachments/assets/02867eda-8c2e-4e76-b8d5-f7aadf9a5dad" />
<img width="400" height="300" alt="image" src="https://github.com/user-attachments/assets/527635b9-66d1-4a56-923e-5532d4273311" />

## 5. VLM-Based Alternative Route Reasoning

The VLM server receives the current obstacle context and selects an alternative waypoint route only from the provided candidate routes.

### VLM Model Information

| Item | Description |
|---|---|
| VLM server file | `vlm_server.py` |
| Local VLM runtime | Ollama |
| VLM model | `qwen2.5vl:3b` |
| API endpoint | `POST http://localhost:8090/select_wp` |
| Input modality | Image + structured obstacle JSON + user goal + candidate routes |
| Output | selected waypoint route and reason |

### VLM Request

```json
{
  "image": "base64 encoded image",
  "image_width": 1280,
  "image_height": 720,
  "goal": [11.0, 0.0],
  "obstacle": {
    "class": "person",
    "conf": 0.86,
    "bbox": [564, 1, 699, 423],
    "distance": 3.449,
    "angle": -0.42,
    "center_x": 631,
    "center_y": 212
  },
  "candidate_routes": ["wp2"]
}
```

### VLM Response

```json
{
  "selected_wp": "wp2",
  "reason": "The obstacle is near the center of the path, so the selected route avoids the blocked region while preserving the user goal."
}
```

The selected route is accepted only when it belongs to `candidate_routes`. This prevents the VLM from selecting a route that does not contain the user-requested goal point.

## 6. Control Layer

The control layer converts the selected route into robot motion.

| Command / Topic | Role |
|---|---|
| `/navigation_stop` | Stops waypoint following when an obstacle blocks the route. |
| `/selected_route` | Publishes a selected route name such as `wp2`. |
| `/selected_route_goal` | Publishes a selected route and goal point in the form `wp2;x,y`. |
| `/sim/cmd_vel` | Sends speed and steering commands to the ego vehicle. |

When goal-aware navigation is used, the framework publishes:

```text
/selected_route_goal <- wp_name;x,y
```

This allows the waypoint follower to follow the selected route only until the requested goal point, instead of driving to the full route endpoint.

## 7. JSON Logs and Shared Environment Update

The cloud/logging server stores framework state in real time. These logs act as a shared situational memory that can be used by other vehicles.

### Saved Files

| File type | Path | Description |
|---|---|---|
| JSON log | `logs/json/<timestamp>.json` | Structured perception, decision, and VLM information. |
| Image frame | `logs/images/<timestamp>.jpg` | Camera image associated with the JSON log. |

### JSON Fields Related to Perception

```json
{
  "timestamp": "2026-06-10_12-30-00",
  "gps": {"lat": 37.501, "lon": 127.036},
  "robocar_speed": 0.0,
  "objects": [
    {
      "class": "person",
      "conf": 0.86,
      "bbox": [564, 1, 699, 423]
    }
  ],
  "lidar_available": true,
  "closest_person": {
    "class": "person",
    "conf": 0.86,
    "bbox": [564, 1, 699, 423],
    "distance": 3.449,
    "angle": -0.42,
    "center_x": 631,
    "center_y": 212,
    "lidar_idx": 1616,
    "lidar_points_used": 86
  }
}
```

### JSON Fields Related to VLM Decision

The JSON log stores not only the selected route but also the VLM reasoning state:

```json
{
  "route_select_trigger": 4.0,
  "emergency_stop_trigger": 1.2,
  "current_goal": [11.0, 0.0],
  "current_goal_candidate_routes": ["wp2"],
  "current_goal_selected_wp": "wp2",
  "wp_mode": true,
  "vlm_selected_wp": "wp2",
  "vlm_reason": "The obstacle is near the center, so an alternative route is safer.",
  "waiting_vlm": false,
  "vlm_failed": false,
  "vlm_failed_reason": null
}
```

### Meaning of VLM-Related Log Fields

| Field | Meaning |
|---|---|
| `current_goal` | User-requested goal point. |
| `current_goal_candidate_routes` | Routes that contain or can reach the current goal. |
| `current_goal_selected_wp` | Initial route selected by the intent feasibility check. |
| `wp_mode` | Whether the robot is currently following a selected waypoint route. |
| `vlm_selected_wp` | Route selected by the VLM server. |
| `vlm_reason` | Natural-language reason generated by the VLM. |
| `waiting_vlm` | Whether the ego vehicle is stopped and waiting for VLM output. |
| `vlm_failed` | Whether VLM route selection failed. |
| `vlm_failed_reason` | Error or invalid-selection reason when VLM fails. |

## 8. Information Shared with Other Vehicles

The cloud server shares the updated environment state with other vehicles. A neighboring vehicle can use the JSON logs to understand:

- which obstacle was detected,
- where the obstacle appeared in the camera image,
- how far the obstacle was from the ego vehicle,
- whether the ego vehicle stopped,
- which user goal was being pursued,
- which candidate routes were available,
- which route the VLM selected,
- why the VLM selected that route,
- whether VLM route selection failed.

This enables cooperative decision support. For example, if the ego vehicle detects a person blocking the center path and selects an alternative route, another vehicle can receive the environment update and avoid selecting the same blocked path.

## 9. Framework Modules

| Framework block | Main file | Role |
|---|---|---|
| Sensor streaming | `imo_server_lidar.py` | Streams camera, odometry, and LiDAR data from the robot side. |
| Perception processing | `edge_threads/infer_thread.py` | Runs YOLO detection, Camera–LiDAR fusion, stop trigger, and VLM trigger. |
| Edge launcher | `edge_control.py` | Starts capture, LiDAR, odometry, inference, and sender threads. |
| VLM reasoning | `vlm_server.py` | Selects an alternative route and returns a reason. |
| Cloud logging | `k8s_server.py` | Saves JSON logs and image frames. |
| Route following | `waypoint_tools/pure_pursuit_follower.py` | Follows the selected waypoint route. |
| Intent feasibility | `waypoint_tools/intent_decision.py` | Checks whether the user goal belongs to available routes. |
| Route definition | `waypoint_tools/waypoint_routes/routes.py` | Stores route coordinates for `wp1`–`wp5`. |

## 10. Main Topics and APIs

### ROS2 Topics

| Topic | Purpose |
|---|---|
| `/user_intent_goal` | Receives user-requested goal point. |
| `/intent_feedback` | Publishes goal feasibility feedback. |
| `/navigation_stop` | Stops the robot when the path is blocked. |
| `/selected_route` | Publishes a selected waypoint route. |
| `/selected_route_goal` | Publishes a selected route with final goal point. |
| `/sim/cmd_vel` | Sends velocity commands to the robot. |



### HTTP Endpoints

| Server | Port | Endpoint | Method | Purpose |
|---|---:|---|---|---|
| `imo_server_lidar.py` | 8000 | `/video` | GET | Camera MJPEG stream |
| `imo_server_lidar.py` | 8000 | `/odometry` | GET | Latest odometry JSON |
| `imo_server_lidar.py` | 8000 | `/lidar` | GET | Latest LiDAR JSON |
| `k8s_server.py` | 8080 | `/inference` | POST | Save JSON and image logs |
| `vlm_server.py` | 8090 | `/health` | GET | VLM server health check |
| `vlm_server.py` | 8090 | `/select_wp` | POST | Select waypoint route |
| `imo_control.py` | 8001 | `/control/distance` | POST | Distance-based emergency stop |
| `imo_control.py` | 8001 | `/control/cmd_vel` | POST | Direct velocity command |
| `imo_control.py` | 8001 | `/control/state` | GET | Current control state |
| `intent_server.py` | 5000 | `/receive_policy` | POST | Receive and save YAML policy |




## 11. ROS2 Package Build

The ROS2 waypoint-related nodes are located in a separate ROS2 workspace:

```text
~/nav2_ws/src/waypoint_tools
```

After modifying any ROS2 node in `waypoint_tools`, rebuild the package with `colcon`:

```bash
cd ~/nav2_ws
colcon build --symlink-install --packages-select waypoint_tools
source install/setup.bash
```

The main ROS2 files in this package include:

| File | Role |
|---|---|
| `waypoint_tools/intent_decision.py` | Receives the user goal and checks whether the goal is feasible on the waypoint routes. |
| `waypoint_tools/pure_pursuit_follower.py` | Follows the selected route using Pure Pursuit and stops at the requested goal point. |
| `waypoint_tools/marker.py` | Visualizes waypoint routes and labels in RViz. |
| `waypoint_tools/waypoint_routes/routes.py` | Stores predefined route coordinates for `wp1`–`wp5`. |

If a Python import error occurs after adding submodules, check that `setup.py` installs all packages using `find_packages()`:

```python
from setuptools import setup, find_packages

setup(
    name='waypoint_tools',
    packages=find_packages(exclude=['test']),
    ...
)
```

When importing route definitions inside ROS2 nodes, use the package-qualified import path:

```python
from waypoint_tools.waypoint_routes.routes import ROUTES
```

After rebuilding, run the ROS2 nodes from the sourced workspace:

```bash
cd ~/nav2_ws
source install/setup.bash
ros2 run waypoint_tools intent_decision
ros2 run waypoint_tools pure_pursuit_follower
```

> Note: Only one node should publish `/sim/cmd_vel` at the same time. When `pure_pursuit_follower.py` is used, do not run another control node such as `imo_control.py` that also publishes velocity commands.

## 12. Execution Order

The framework should be executed in the following order. Each command should be run in a separate terminal unless otherwise noted.

### [Step 1.] Start Isaac Sim and play the simulation

Start Isaac Sim, load the LIMO robot scene, enable the ROS2 bridge, and press the play button. The robot-side topics such as camera, LiDAR, odometry, and `/sim/cmd_vel` should be available before running the edge pipeline.

### [Step 2.] Start the robot-side sensor server

```bash
cd ~/SDV_Robocar
python imo_server_lidar.py
```

This server provides camera, odometry, and LiDAR data through HTTP endpoints:

```text
/video
/odometry
/lidar
```

### [Step 3.] Start the cloud logging server

```bash
cd ~/SDV_Robocar
python k8s_server.py
```

This server receives inference results from the edge controller and stores synchronized JSON/image logs:

```text
logs/json/<timestamp>.json
logs/images/<timestamp>.jpg
```

### [Step 4.] Start Ollama for the VLM runtime

```bash
ollama serve
```

If the VLM model is not downloaded yet, pull it first:

```bash
ollama pull qwen2.5vl:3b
```

### [Step 5.] Start the VLM server

```bash
cd ~/SDV_Robocar
python vlm_server.py
```

Check whether the VLM server is running:

```bash
curl http://localhost:8090/health
```

Optional warm-up request:

```bash
curl -X POST http://localhost:8090/select_wp \
  -H "Content-Type: application/json" \
  -d '{
    "image": null,
    "image_width": 1280,
    "image_height": 720,
    "goal": [11.0, 0.0],
    "obstacle": {
      "class": "person",
      "distance": 3.5,
      "angle": 0.0,
      "center_x": 640
    },
    "candidate_routes": ["wp2"]
  }'
```

The warm-up request helps load the VLM model before the real obstacle-triggered route selection occurs.

### [Step 6.] Build and source the ROS2 waypoint package

```bash
cd ~/nav2_ws
colcon build --symlink-install --packages-select waypoint_tools
source install/setup.bash
```

### [Step 7.] Run the ROS2 intent decision node

```bash
cd ~/nav2_ws
source install/setup.bash
ros2 run waypoint_tools intent_decision
```

This node receives the user goal through `/user_intent_goal`, checks which waypoint routes contain the goal, and saves the current intent state for the edge decision module.

### [Step 8.] Run the ROS2 waypoint follower

```bash
cd ~/nav2_ws
source install/setup.bash
ros2 run waypoint_tools pure_pursuit_follower    # or point_follower
```

This node receives `/selected_route_goal` and publishes motion commands to `/sim/cmd_vel`.

### [Step 9.] Publish the user goal

In another terminal, publish the user-requested goal point:

```bash
cd ~/nav2_ws
source install/setup.bash
ros2 topic pub --once /user_intent_goal std_msgs/msg/String "{data: '11.0,0.0'}"
```

The intent decision node should create the current intent state file:

```bash
cat /tmp/current_intent_state.json
```

Example:

```json
{
  "goal": [11.0, 0.0],
  "selected_wp": "wp2",
  "candidate_routes": ["wp2"],
  "valid": true
}
```

### [Step 10.] Start the edge controller

```bash
cd ~/PycharmProjects/SDV_Robocar
python edge_control.py
```

The edge controller starts the capture, LiDAR, odometry, inference, and sender threads. It detects obstacles, estimates distance using Camera–2D LiDAR fusion, stops the robot if needed, calls the VLM server, publishes the selected route, and sends JSON/image logs to the cloud logging server.

### [Step 11.] Monitor route-selection topics

To verify whether the VLM-selected route is published correctly, monitor the following topics:

```bash
ros2 topic echo /navigation_stop
```

```bash
ros2 topic echo /selected_route_goal
```

A normal goal-aware VLM result should look like this:

```text
/selected_route_goal <- wp2;11.0,0.0
```

If `/selected_route` is published instead of `/selected_route_goal`, the robot may follow the full route endpoint rather than stopping at the user-requested goal point.

### Recommended Terminal Layout

| Terminal | Command |
|---:|---|
| 1 | Isaac Sim with ROS2 bridge enabled and simulation playing |
| 2 | `python imo_server_lidar.py` |
| 3 | `python k8s_server.py` |
| 4 | `ollama serve` |
| 5 | `python vlm_server.py` |
| 6 | `ros2 run waypoint_tools intent_decision` |
| 7 | `ros2 run waypoint_tools pure_pursuit_follower` |
| 8 | `ros2 topic pub --once /user_intent_goal std_msgs/msg/String "{data: '11.0,0.0'}"` |
| 9 | `python edge_control.py` |

---
# Summary

This framework provides an intent-aware autonomous driving pipeline in which the ego vehicle detects obstacles using camera and 2D LiDAR, stops when the user-requested route is blocked, asks a VLM server for an alternative route, and stores the resulting perception and decision state as shared JSON logs. The stored VLM decision, reason, obstacle information, and selected route can be shared with other vehicles as an environment update.
