# Robot and Simulator Safety

## Scope

These safety rules apply to:

- NVIDIA Isaac Sim
- ROS2 nodes and topics
- Flask control and sensor servers
- Ollama and the VLM server
- The simulated LIMO robot
- The physical LIMO robot

## Non-negotiable safety rules

1. Only one process may publish `/sim/cmd_vel` at a time.
2. Emergency-stop behavior must not be removed, bypassed, or weakened.
3. Invalid, unavailable, or timed-out VLM output must keep the robot stopped.
4. Motion may resume only after the selected route has been validated.
5. Physical-robot testing is allowed only after offline and Isaac Sim validation.
6. Speed limits and stopping thresholds require explicit human approval to change.
7. Rosbag files, logs, models, datasets, and experiment artifacts must not be
   deleted automatically.
8. Codex must not assume that a sensor, server, controller, or emergency-stop
   process is active without checking its status.

## Commands Codex must not run automatically

Codex must not automatically execute commands that directly change robot or
simulator motion state, including:

- `ros2 topic pub ...`
- Direct publication to `/sim/cmd_vel`
- Publication to `/selected_route`
- Publication to `/selected_route_goal`
- Publication to `/user_intent_goal`
- Publication to `/navigation_stop`
- Physical-robot velocity commands
- Commands that recursively delete logs, bags, models, datasets, or artifacts

These commands must be reviewed and explicitly approved by the user before
execution.

## Commands requiring user approval

The following commands may start services, create ROS2 publishers, modify the
workspace, download models, or consume significant system resources:

- `ros2 run ...`
- `ros2 launch ...`
- `colcon build ...`
- `python edge_control.py`
- `python imo_control.py`
- `python imo_server_lidar.py`
- `python intent_server.py`
- `python k8s_server.py`
- `python vlm_server.py`
- `ollama serve`
- `ollama pull ...`
- `ollama run ...`

Before suggesting one of these commands, Codex must explain its purpose,
expected effect, and possible effect on the current runtime state.

## Required validation order

Use the following validation order:

~~~text
1. Static and syntax checks
2. Offline unit tests
3. Recorded image, LiDAR, JSON, CSV, or rosbag evaluation
4. Isaac Sim test with the robot initially stopped
5. Low-speed, single-route Isaac Sim test
6. Full Isaac Sim scenario test
7. Physical LIMO test
~~~

A later validation level must not be used as a substitute for a missing earlier
validation level.

## Before an Isaac Sim motion test

Confirm all of the following:

- Isaac Sim is running the intended scene.
- ROS2 Bridge is active.
- The robot starts from the expected pose.
- The emergency-stop path is available.
- Only the intended controller publishes `/sim/cmd_vel`.
- No previous controller or Flask control process remains active.
- The selected route and goal are correct.
- Linear and angular speed limits match the approved configuration.
- Sensor topics contain valid and recent data.
- A human is watching the test and can stop it immediately.

If any item cannot be confirmed, do not begin motion.

## Before a physical LIMO test

Confirm all Isaac Sim requirements and the following additional conditions:

- Network connectivity is stable.
- The correct physical robot is connected.
- The test area is clear of people and unexpected obstacles.
- A physical emergency-stop method is available.
- The initial speed limit is conservative.
- Camera, LiDAR, odometry, and control topics are valid before motion.
- The operator can stop the robot immediately.
- The robot has first completed the same scenario successfully in Isaac Sim.

If any item cannot be confirmed, do not begin the physical-robot test.

## Failure policy

When a required sensor, server, controller, route, or VLM response is
unavailable:

- Do not guess missing values.
- Do not substitute an unvalidated route.
- Do not resume movement.
- Publish no new motion command automatically.
- Record the failure reason when logging is available.
- Keep the robot stopped or return it to a stopped state.
- Report which dependency failed and what must be checked.

## Multiple-controller policy

Before starting a route follower or control process:

1. Check the active ROS2 nodes.
2. Check the publishers of `/sim/cmd_vel`.
3. Stop or disable conflicting controllers.
4. Confirm that only the intended controller will publish velocity commands.
5. Start motion only after explicit user approval.

The Point Follower, Pure Pursuit Follower, Flask control process, and any manual
velocity publisher must not control the robot at the same time.

## Data preservation policy

The following files must be preserved unless the user explicitly approves
their removal:

- Rosbag recordings
- Camera images
- LiDAR data
- JSON logs
- CSV metric files
- Model weights
- Evaluation fixtures
- Experiment configurations
- Generated plots
- Run manifests

New experiment outputs must use a new run directory instead of overwriting a
previous result.
