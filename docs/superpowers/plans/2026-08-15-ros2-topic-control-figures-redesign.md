> Last updated: 2026-08-15 21:16 KST

# ROS2 Topic Control Figures Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two active robot-control PNGs with 1672×941 figures that preserve the immutable backup style while correcting every verified producer-to-consumer connection.

**Architecture:** A temporary deterministic Pillow renderer recreates both figures with a shared palette, rounded-card primitives, orthogonal arrow routing, and the exact RobotLAB LIMO raster. The current figure shows only verified production behavior and explicit caveats; the future figure separates a solid current baseline from dotted proposed safety and command-ownership paths.

**Tech Stack:** Python 3, Pillow, ImageMagick metadata inspection, repository static/offline checks

## Global Constraints

- Do not modify either file under `ictc_test/backup/`.
- Replace `ictc_test/robot_motion_control_current.png` and `ictc_test/robot_motion_control_future.png`, then synchronize `ictc_test/robot_motion_control_architecture_explanation.txt` with the final images.
- Both active outputs must be 1672×941 PNG files with canvas background `#F7F9F8`.
- Preserve the approved backup composition, attached rounded title tabs, inset rounded component boxes, and compact orthogonal arrows.
- Use these exact title/body pairs: Cloud Server `#595959`/`#EEEEEE`; Perception `#B8E9FF`/`#F0FAFF`; Decision `#FEEFC5`/`#FFFAEA`; VLM Server `#E4F0D5`/`#F9FCF5`; Control `#CCD2F0`/`#F1F2F8`.
- Use white `#FFFFFF` for component content boxes by default; any necessary extra color must be a related low-saturation pastel.
- Use only DejaVu Sans: `DejaVuSans-Bold.ttf` for main/group/component titles and badges, `DejaVuSans.ttf` for body/topic text; shared scale is 34 px main title, 18 px group/principal title, 15 px body/interface, and 13 px compact rows/flow labels/notes.
- Do not condense, stretch, italicize, or mix font families; both figures must use the same typography hierarchy.
- Use the exact RobotLAB asset from `https://new.robotlab.com/hubfs/LIMO%20ROS2_20231018_2-1.png`; do not redraw or recolor it.
- Preserve exact spelling of ROS2 topics, HTTP endpoints, TF frames, and `geometry_msgs/Twist`.
- Do not invent a public ROS2 topic for proposed internal velocity or health signals.
- Do not start ROS2, Isaac Sim, Flask, Ollama, or a physical LIMO, and do not publish any ROS2 topic.
- Treat production Python code as current behavior even where documentation differs.
- Preserve these backup SHA-256 values:
  - current: `b9e4806aefe0134fea1716e6c9f8220aadb2ee96833ff2fc583e06b96cfa79af`
  - future: `f0e58e17f3e432da69af7487136594d04737202c7e976c5ab492da0b7bdeb72c`

---

### Task 1: Establish immutable inputs and a deterministic renderer

**Files:**
- Create temporarily: `/tmp/render_corrected_ros2_control_figures.py`
- Read: `ictc_test/backup/2026-08-15_first_generated_robot_motion_control.png`
- Read: `ictc_test/backup/2026-08-15_first_generated_robot_motion_control_future.png`
- Read: `/tmp/limo-ros2-reference.png`

**Interfaces:**
- Consumes: immutable backup dimensions/palette and exact RobotLAB LIMO raster
- Produces: shared drawing functions `rounded_box`, `centered_text`, `topic_row`, `orthogonal_arrow`, `group_box`, and `paste_limo`

- [ ] **Step 1: Record immutable input evidence**

  Run:

  ```bash
  sha256sum ictc_test/backup/2026-08-15_first_generated_robot_motion_control.png \
    ictc_test/backup/2026-08-15_first_generated_robot_motion_control_future.png
  identify ictc_test/backup/2026-08-15_first_generated_robot_motion_control.png \
    ictc_test/backup/2026-08-15_first_generated_robot_motion_control_future.png
  ```

  Expected: the hashes in Global Constraints and two 1672×941 RGB PNG files.

- [ ] **Step 2: Write a failing renderer contract check**

  Add a `verify_contract()` function to the temporary renderer that checks:

  ```python
  assert CANVAS == (1672, 941)
  assert BG == "#F7F9F8"
  assert Path(LIMO_SOURCE).is_file()
  assert Image.open(LIMO_SOURCE).size == (4000, 4000)
  ```

  Run the temporary script before defining these constants. Expected: failure because the renderer contract is incomplete.

- [ ] **Step 3: Implement shared drawing primitives**

  Define the canvas and palette constants from the approved design and implement:

  ```python
  def rounded_box(draw, xy, fill, outline="#666767", radius=14, width=2): ...
  def centered_text(draw, xy, text, font, fill="#171717", spacing=4): ...
  def topic_row(draw, x, y, role, topic, role_color): ...
  def orthogonal_arrow(draw, points, color="#666767", width=4, dashed=False): ...
  def group_box(draw, xy, title, header_fill, body_fill): ...
  def paste_limo(canvas, xy, max_size): ...
  ```

  `orthogonal_arrow` must draw an arrowhead at the final point and accept only horizontal/vertical segments. `paste_limo` must alpha-composite the source pixels without color conversion beyond RGBA compositing.

- [ ] **Step 4: Run the renderer contract check**

  Run:

  ```bash
  python /tmp/render_corrected_ros2_control_figures.py --verify-contract
  ```

  Expected: exit code 0 without writing either active PNG.

### Task 2: Render the corrected current implementation figure

**Files:**
- Modify: `ictc_test/robot_motion_control_current.png`
- Modify temporarily: `/tmp/render_corrected_ros2_control_figures.py`

**Interfaces:**
- Consumes: shared renderer and current interfaces in `imo_server_lidar.py`, `edge_threads/infer_thread.py`, `waypoint_tools/intent_decision.py`, `waypoint_tools/point_follower.py`, and `waypoint_tools/pure_pursuit_follower.py`
- Produces: `render_current() -> PIL.Image.Image` and the corrected current PNG

- [ ] **Step 1: Encode the current topology as named nodes and edges**

  Use separate wiring lanes and these exact flows:

  ```text
  /sim/camera/color/image_raw, /sim/scan, /sim/odom
    -> ROS2 Sensor Process -> Queue / Manager -> HTTP Sensor Gateway
    -> GET /video, GET /odometry, GET /lidar -> YOLO + Camera–2D LiDAR Fusion
    -> Edge Safety Decision

  /user_intent_goal -> IntentDecisionNode -> /selected_route
  IntentDecisionNode -> /intent_feedback

  Edge Safety Decision -> POST /select_wp -> VLM Route Selection
  VLM Route Selection -> selected_wp + reason -> Edge Safety Decision
  Edge Safety Decision -> POST /inference -> JSON + Image Logs

  Edge Safety Decision -> /selected_route, /selected_route_goal, /navigation_stop
  route/stop topics -> selected controller
  TF odom -> base_link -> selected controller
  selected controller -> /sim/cmd_vel -> Ego Vehicle
  ```

- [ ] **Step 2: Draw current limitations without adding signal paths**

  Add compact caveats outside the main arrows:

  ```text
  valid intent state handoff is incomplete
  VLM handling can duplicate /selected_route and publish None on failure
  run only one /sim/cmd_vel publisher; no code-level arbitration
  route-select stop ≤ 6.0 m; emergency stop ≤ 1.2 m
  ```

  Multiprocessing appears only as a small note under `ROS2 Sensor Process`.

- [ ] **Step 3: Render the active current PNG**

  Run:

  ```bash
  python /tmp/render_corrected_ros2_control_figures.py --current \
    ictc_test/robot_motion_control_current.png
  ```

  Expected: one 1672×941 PNG; backup hashes remain unchanged.

- [ ] **Step 4: Inspect current at original resolution**

  Verify visually that fusion terminates at `Edge Safety Decision`, both VLM arrows have arrowheads at their consumers, logging points toward `JSON + Image Logs`, and no line crosses text or a group title.

### Task 3: Render the corrected proposed-direction figure

**Files:**
- Modify: `ictc_test/robot_motion_control_future.png`
- Modify temporarily: `/tmp/render_corrected_ros2_control_figures.py`

**Interfaces:**
- Consumes: shared renderer, the current baseline topology, and approved proposed components
- Produces: `render_future() -> PIL.Image.Image` and the corrected future PNG

- [ ] **Step 1: Draw a solid current baseline**

  Show these verified current paths with solid arrows:

  ```text
  ROS2 route/stop topics -> Point Follower OR Pure Pursuit
  selected current controller -> /sim/cmd_vel -> Ego Vehicle
  ```

  The topic arrows must point toward the subscribing controller. The solid current `/sim/cmd_vel` line must not enter `Command Arbitration`.

- [ ] **Step 2: Draw the separately styled target path**

  Use dotted target arrows and explicit `TARGET` badges for:

  ```text
  Intent Manager -> Deterministic Safety Supervisor
  VLM advisory -> Deterministic Safety Supervisor
  State & Health Monitor -> Deterministic Safety Supervisor
  Deterministic Safety Supervisor -> Controller Manager
  Controller Manager -> internal velocity proposal -> Command Arbitration
  fault / stale / invalid VLM -> Fallback Safe Stop -> Command Arbitration
  Command Arbitration -> /sim/cmd_vel -> Ego Vehicle
  ```

  `internal velocity proposal`, health, and fault are conceptual internal labels, not ROS2 topic names.

- [ ] **Step 3: Render the active future PNG**

  Run:

  ```bash
  python /tmp/render_corrected_ros2_control_figures.py --future \
    ictc_test/robot_motion_control_future.png
  ```

  Expected: one 1672×941 PNG with a legend distinguishing current solid and target dotted paths.

- [ ] **Step 4: Inspect future at original resolution**

  Verify that every proposed component has a visible badge, subscriber arrows point toward controllers, the direct current command path remains visible, and the proposed arbitration path is visually distinct and non-overlapping.

### Task 4: Verify content, layout, backups, and repository health

**Files:**
- Review: `ictc_test/robot_motion_control_current.png`
- Review: `ictc_test/robot_motion_control_future.png`
- Modify: `ictc_test/robot_motion_control_architecture_explanation.txt`
- Preserve: `ictc_test/backup/2026-08-15_first_generated_robot_motion_control.png`
- Preserve: `ictc_test/backup/2026-08-15_first_generated_robot_motion_control_future.png`

**Interfaces:**
- Consumes: both active outputs and immutable backups
- Produces: static verification evidence and a final scope review

- [ ] **Step 1: Synchronize the companion TXT explanation**

  Rewrite `ictc_test/robot_motion_control_architecture_explanation.txt` so it
  explains each final PNG separately and includes:

  ```text
  current: sensor subscriptions and multiprocessing boundary; HTTP gateway;
  fusion -> edge safety; /user_intent_goal -> IntentDecisionNode;
  POST /select_wp request/result; POST /inference logging direction;
  route/stop topic subscriptions; TF; direct /sim/cmd_vel; current caveats

  future: solid current baseline; target-only Intent/Safety/Controller managers;
  VLM advisory; state/health validation; Fallback Safe Stop;
  internal velocity proposal; sole target Command Arbitration publisher
  ```

  State explicitly that `TARGET`/`PROPOSED` elements are not production code.
  Do not document any node, topic, endpoint, or arrow absent from the PNGs.

- [ ] **Step 2: Verify file format, dimensions, and required colors**

  Run `file` and `identify` on both active PNGs. Use Pillow to assert each image is 1672×941 RGB and contains canvas `#F7F9F8`, component white `#FFFFFF`, and the exact category pairs `#595959`/`#EEEEEE`, `#B8E9FF`/`#F0FAFF`, `#FEEFC5`/`#FFFAEA`, `#E4F0D5`/`#F9FCF5`, and `#CCD2F0`/`#F1F2F8` whenever that category appears.

  Inspect the renderer font objects and final images to confirm both figures use
  DejaVu Sans regular/bold only and the shared 34/18/15/13 px hierarchy.

- [ ] **Step 3: Verify exact interface strings**

  Review the rendered labels at original resolution against this set:

  ```text
  /sim/camera/color/image_raw
  /sim/scan
  /sim/odom
  /user_intent_goal
  /selected_route
  /intent_feedback
  /selected_route_goal
  /navigation_stop
  /sim/cmd_vel
  odom -> base_link
  GET /video
  GET /odometry
  GET /lidar
  POST /select_wp
  POST /inference
  geometry_msgs/Twist
  ```

- [ ] **Step 4: Recheck immutable backup hashes**

  Run `sha256sum` on both backups. Expected: exact values from Global Constraints.

- [ ] **Step 5: Run repository checks**

  Run:

  ```bash
  bash scripts/check.sh
  bash scripts/test_offline.sh
  ```

  Expected: both commands exit 0. No live ROS2 or simulator command is permitted.

- [ ] **Step 6: Review final scope**

  Run `git status --short` and `git diff --check`. Confirm the implementation changed only the two active PNGs and their companion TXT in addition to the approved design and plan documents; report unrelated pre-existing files separately.
