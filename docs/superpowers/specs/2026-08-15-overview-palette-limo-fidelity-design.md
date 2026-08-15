# ROS2 Topic Control Figure Design

## Objective

Create two corrected 1672×941 PNG figures using the immutable backup images as
the visual baseline:

1. the control architecture implemented by the current production code;
2. the proposed direction for safer, single-owner velocity control.

The figures must be readable as ROS2 topic-flow diagrams, preserve the approved
backup composition, and continue to use the palette and curvature derived from
`ictc_test/overview.png`.

## Mandatory LIMO asset rule

Every robot-control architecture figure in this repository must use the LIMO
image from this exact RobotLAB URL:

`https://new.robotlab.com/hubfs/LIMO%20ROS2_20231018_2-1.png`

Do not replace it with an AI-redrawn robot, a generic mobile robot, or a
different LIMO photograph. The source PNG has an alpha channel; composite its
original pixels directly so that `LIMO`, `AGILE·X`, the green light, and vehicle
number `03` remain intact.

## Visual language

- Canvas: 1672×941, warm off-white `#F7F9F8`.
- Structural stroke and arrows: neutral gray near `#666767`.
- Perception: pale blue group with a `#B4DBEB` title tab.
- Decision: pale cream group with a cream title tab.
- VLM/advisory: pale sage with olive dotted request/response arrows.
- Control: pale lavender group with a lavender title tab.
- TF/state feedback: cyan dotted arrow.
- Safety and verified caveats: restrained pastel red.
- Use rounded rectangles, approximately 18 px group radius and 12 px module
  radius, matching the curvature of `overview.png`.
- Use straight or orthogonal arrows. Every arrow must start and end at a named
  producer, consumer, or interface pill.
- Arrow labels sit in white rounded pills and must not overlap lines, boxes, or
  other text.
- Multiprocessing appears only as a small note under the ROS2 sensor subscriber.

## Current implementation content

The production-code figure shows these verified ROS2 interfaces:

- Sensor subscriptions: `/sim/camera/color/image_raw`, `/sim/scan`, `/sim/odom`.
- Intent subscription: `/user_intent_goal`.
- Decision outputs: `/selected_route`, `/selected_route_goal`,
  `/navigation_stop`.
- Controller subscriptions: `/selected_route`, `/selected_route_goal`,
  `/navigation_stop`.
- Controller pose lookup: TF `odom → base_link`.
- Controller output: `/sim/cmd_vel` with `geometry_msgs/Twist`.

HTTP paths from `IETF125.png` and production code are shown separately:
`GET /video`, `GET /odometry`, `GET /lidar`, `POST /select_wp`, and
`POST /inference`.

The figure must preserve the verified current limitations: route-selection
stop at 6.0 m, emergency stop at 1.2 m, incomplete intent-state handoff,
duplicate route publication after VLM handling, and no code-level arbitration
between Point Follower and Pure Pursuit.

## Proposed-direction content

The proposed figure keeps the existing public topic names and introduces no
unverified topic names. It shows:

- validated route and stop ownership;
- VLM output used as advisory input to deterministic validation;
- `/navigation_stop` priority;
- exclusive controller selection;
- internal velocity proposals rather than direct controller publication;
- Command Arbitration as the sole `/sim/cmd_vel` publisher;
- state/health validation and safe stop on fault or stale state.

Every proposed component is labeled `PROPOSED` so it cannot be mistaken for
current production behavior.

## Backup rule for this redesign

Before replacing the active figures, preserve the earliest identifiable image
generated on 2026-08-15. Filesystem evidence identifies the 18:11:07 image as
the earliest candidate available in the generation cache.

The following files are immutable visual baselines and must never be edited or
overwritten:

- `ictc_test/backup/2026-08-15_first_generated_robot_motion_control.png`
- `ictc_test/backup/2026-08-15_first_generated_robot_motion_control_future.png`

The active outputs, and only the active outputs, are replaced:

- `ictc_test/robot_motion_control_current.png`
- `ictc_test/robot_motion_control_future.png`

## Approved topology corrections

The active figures retain the 1672×941 baseline composition, rounded boxes,
pastel palette, and restrained orthogonal arrows of the immutable backups.
They correct the topology instead of painting over individual pixels.

### Current figure

- Fused detections and Camera–2D LiDAR distance flow to the edge safety and
  route-decision logic, not to `IntentDecisionNode`.
- `IntentDecisionNode` receives only `/user_intent_goal` and publishes
  `/selected_route` and `/intent_feedback`.
- The edge decision sends `POST /select_wp` to the VLM server and receives the
  selected waypoint and reason as the response.
- Logging flows from edge inference through `POST /inference` to the JSON and
  image logging server. The logging server does not feed the safety decision.
- The current controller subscribes to `/selected_route`,
  `/selected_route_goal`, and `/navigation_stop`, performs TF
  `odom → base_link`, and publishes `/sim/cmd_vel` directly to the robot.
- Point Follower and Pure Pursuit remain alternative direct publishers, with
  an explicit operational constraint that only one may run.

### Proposed figure

- A compact current baseline remains visible with the actual direct
  `/sim/cmd_vel` path to the robot.
- ROS2 route and stop topics point toward the subscribing controller rather
  than away from it.
- The target path is visually separate: controller velocity proposal →
  Command Arbitration → `/sim/cmd_vel` → robot.
- Command Arbitration, Controller Manager, deterministic Safety Supervisor,
  State & Health Monitor, and Fallback Safe Stop are all explicitly marked
  `TARGET` or `PROPOSED`.
- No new public ROS2 topic name is invented. Internal velocity proposals and
  health/fault signals are conceptual internal interfaces.

## Layout and verification acceptance criteria

- No text, topic badge, box, or arrow overlaps another text element.
- No arrow crosses a group title tab or terminates in empty space.
- Each arrow points from producer to consumer; bidirectional HTTP interaction
  uses two separately directed paths.
- Current and proposed paths use visibly distinct line styles and a legend.
- The exact RobotLAB LIMO PNG is composited without redrawing or recoloring.
- Both active outputs are 1672×941 PNG files and are visually inspected at
  original resolution.
- The two backup SHA-256 values remain unchanged after generation.
- Verification is static and offline only; no ROS2, simulator, Flask, Ollama,
  or robot process is started.
