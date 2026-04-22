**[ Isaac Sim Ver. ]**

```
Ubuntu 22.04
ROS2 Humble
Nvidia Isaac Sim 4.5.0
python 3.10
```
<br/>

## Main Figure
<img width="1920" height="1080" alt="Figure2" src="https://github.com/user-attachments/assets/037807dc-084b-419d-a8dd-f2d15ea3444f" />
<br/><br/>

**Perception (Edge Server)**<br/>
- Receive camera stream from LIMO<br/>
- Receive odometry data (pose, twist) from LIMO<br/>
- Receive 2D LiDAR data (angle_min, angle_increment, ranges) from LIMO<br/>
- Perform object detection (YOLO) to extract class and bounding box information<br/>
- Convert odometry to approximate GPS coordinates<br/>
- Map image pixels to LiDAR angles using camera FOV<br/>
- Compute object distance using Camera–LiDAR fusion<br/>
- Generate structured perception output (objects, distance, position, sensor data)<br/>
<br/>

**Decision (Edge Server)**<br/>
- Analyze perception results (detected objects and distances)<br/>
- Identify closest obstacle (e.g., person) and evaluate collision risk<br/>
- Determine stop condition based on distance threshold<br/>
- Plan avoidance sequence based on object position (left/right)<br/>
- Example scenario:<br/>
    If the person is on the left → steer right *n* degrees for *k* seconds
    → steer left *n* degrees for *2k* seconds
    → steer right *n* degrees for *k* seconds
    → align wheels to 0 degrees and move forward
- Manage avoidance state (stage, direction, timing)<br/>
<br/>

**Control (Edge Server)**<br/>
- Receive distance from Edge server<br/>
- Apply emergency stop if distance is below threshold<br/>
- Receive velocity commands (linear_x, angular_z) from Edge server<br/>
- Publish control commands to `/cmd_vel` topic<br/>
- Execute real-time motion control (forward, steering, stop)<br/> 
<br/>

**VLM Server**<br/>
- Receive perception outputs (image, objects, distance)<br/>
- Understand high-level context (e.g., blocked path, multi-agent situation)<br/>
- Perform intent-aware reasoning<br/>
- Generate alternative navigation strategies<br/>
- Provide decision suggestions to Decision module<br/> 
<br/>

**Cloud Server (Kubernetes)**<br/>
- Receive inference results (JSON + image) from Edge server<br/>
- Save logs in real time for monitoring and analysis<br/>
- Send user intent (e.g., navigation goal) to Edge server<br/>
- Manage policy (pass/drop) to enable or disable control signals<br/>
- Support system scalability and centralized management<br/>
<br/>

## Execution Flow

### 1. Run IMO server
```
$ python imo_server_lidar.py
```

### 2. Run k8s server (Cloud)
```
$ python k8s_server.py
```

### 3. Intent Sender server (Cloud)
```
$ python intent_server.py
# received_policy.yaml: pass/drop to activate or deactivate stop/detour function
```

### 4. YOLO Detection + Odometry + 2D Lidar
```
$ python edge_control.py
```

### 5. Control IMO
```
$ python imo_control.py
```

<br/>

- YOLO Detection<br/>
<img width="1280" height="720" alt="image" src="https://github.com/user-attachments/assets/f2178f21-3236-4fea-9ce0-4e4b7cd9a30f" />
</br></br>

- Save files in real time (Kubernetes)</br>
<img width="993" height="377" alt="image" src="https://github.com/user-attachments/assets/99f8f2a2-2070-4c68-9ca9-565084ef098e" />
<br/><br/>
