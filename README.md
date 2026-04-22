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


## Data classes
**yolov8s :**<br/>
{ 0: 'person',
 1: 'bicycle',
 2: 'car',
 3: 'motorcycle',
 4: 'airplane',
 5: 'bus',
 6: 'train',
 7: 'truck',
 8: 'boat',
 9: 'traffic light',
 10: 'fire hydrant',
 11: 'stop sign',
 12: 'parking meter',
 13: 'bench',
 14: 'bird',
 15: 'cat',
 16: 'dog',
 17: 'horse',
 18: 'sheep',
 19: 'cow',
 20: 'elephant',
 21: 'bear',
 22: 'zebra',
 23: 'giraffe',
 24: 'backpack',
 25: 'umbrella',
 26: 'handbag',
 27: 'tie',
 28: 'suitcase',
 29: 'frisbee',
 30: 'skis',
 31: 'snowboard',
 32: 'sports ball',
 33: 'kite',
 34: 'baseball bat',
 35: 'baseball glove',
 36: 'skateboard',
 37: 'surfboard',
 38: 'tennis racket',
 39: 'bottle',
 40: 'wine glass',
 41: 'cup',
 42: 'fork',
 43: 'knife',
 44: 'spoon',
 45: 'bowl',
 46: 'banana',
 47: 'apple',
 48: 'sandwich',
 49: 'orange',
 50: 'broccoli',
 51: 'carrot',
 52: 'hot dog',
 53: 'pizza',
 54: 'donut',
 55: 'cake',
 56: 'chair',
 57: 'couch',
 58: 'potted plant',
 59: 'bed',
 60: 'dining table',
 61: 'toilet',
 62: 'tv',
 63: 'laptop',
 64: 'mouse',
 65: 'remote',
 66: 'keyboard',
 67: 'cell phone',
 68: 'microwave',
 69: 'oven',
 70: 'toaster',
 71: 'sink',
 72: 'refrigerator',
 73: 'book',
 74: 'clock',
 75: 'vase',
 76: 'scissors',
 77: 'teddy bear',
 78: 'hair drier',
 79: 'toothbrush'
 }
 <br/><br/>

 
