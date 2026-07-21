# SDV Robocar Codex Guidance

## Read first

Before making non-trivial changes, read:

- `README.md`
- `ARCHITECTURE.md`
- `docs/index.md`
- `docs/safety/robot-safety.md`
- `docs/experiments/protocol.md`

Read the related production code before trusting documentation.
When code and documentation disagree, report the mismatch and treat the code
as the current behavior until the documentation is corrected.

## Project purpose

This repository implements an indoor robotic framework using:

- ROS2 Humble and NVIDIA Isaac Sim
- Camera, 2D LiDAR, and odometry
- YOLO-based object detection
- Training-free Camera–2D LiDAR late fusion
- VLM-based alternative route selection
- Point Follower and Pure Pursuit route following
- JSON and image logging for shared environment information

## Main repository areas

- `detector/`: detection model resources
- `sensor/`: camera, LiDAR, and odometry interfaces
- `edge_modules/`: configuration and shared edge functions
- `edge_threads/`: capture, inference, and transmission workers
- `waypoint_tools/`: route definitions, intent processing, and controllers
- `edge_control.py`: edge pipeline launcher
- `imo_server_lidar.py`: robot-side sensor server
- `vlm_server.py`: VLM route-selection server
- `k8s_server.py`: JSON and image logging server

## Golden rules

- Inspect related code and tests before editing.
- Make the smallest change that satisfies the stated goal.
- Preserve the current baseline when adding an experimental method.
- Add candidate methods as separately selectable implementations.
- Do not silently rename ROS2 topics, HTTP endpoints, JSON fields, or routes.
- Do not invent file paths, topics, endpoints, parameters, or test results.
- Keep reusable parameters in configuration files rather than evaluation code.
- Record negative and neutral experimental results as well as improvements.

## Robot and simulator safety

- Do not automatically start Isaac Sim, Ollama, Flask servers, ROS2 nodes,
  or a real LIMO robot.
- Do not publish ROS2 topics without explicit user approval.
- Never automatically publish `/sim/cmd_vel`, `/selected_route`,
  `/selected_route_goal`, `/user_intent_goal`, or `/navigation_stop`.
- Only one process may publish `/sim/cmd_vel` at a time.
- Preserve emergency-stop and stopped-state behavior.
- When VLM output is invalid or unavailable, keep the robot stopped.
- Validate changes in this order:
  offline test -> recorded-data replay -> Isaac Sim -> real LIMO.
- Do not increase speed limits or weaken stopping thresholds without approval.
- Do not delete rosbag files, logs, models, datasets, or experiment artifacts.

## Required workflow

For non-trivial work:

1. Read the relevant documents and source files.
2. Create or update an execution plan under `docs/exec-plans/active/`.
3. State the baseline, fixed conditions, metrics, and acceptance criteria.
4. Reproduce the current behavior before modifying it.
5. Add or update an offline test where practical.
6. Implement the smallest scoped change.
7. Run `bash scripts/check.sh`.
8. Run the relevant baseline and candidate evaluations.
9. Save reproducible results under `artifacts/runs/`.
10. Review the final diff and document remaining limitations.
11. Move completed execution plans to `docs/exec-plans/completed/`.

## Standard checks

- General checks: `bash scripts/check.sh`
- Offline unit checks: `bash scripts/test_offline.sh`

Live ROS2, Isaac Sim, Ollama, Flask, and real-robot commands require
explicit user approval and are not part of automatic verification.

## Definition of done

A task is complete only when:

- The stated acceptance criteria have been evaluated.
- Relevant checks pass.
- The existing baseline remains reproducible.
- Baseline and candidate use the same inputs and metrics.
- Results and execution metadata are saved.
- Documentation reflects the final behavior.
- Remaining risks and limitations are listed.
- No unapproved live command was executed.
