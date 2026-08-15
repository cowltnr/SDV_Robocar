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

## Markdown documentation locations

- Keep `README.md`, `AGENTS.md`, and `ARCHITECTURE.md` at repository root.
- Use `docs/index.md` as the central document map.
- Store general documents in the closest matching subdirectory under `docs/`.
- Store meeting records in `docs/meetings/`.
- Store safety documents in `docs/safety/`.
- Store experiment protocols and evaluation documents in `docs/experiments/`.
- Store active execution plans in `docs/exec-plans/active/` and move completed
  plans to `docs/exec-plans/completed/`.
- Store Superpowers designs in `docs/superpowers/specs/` and implementation
  plans in `docs/superpowers/plans/`.
- Store automation operations documents in `docs/automation/`.
- If the user specifies a path, use that path. Prefer updating an existing
  document over creating a duplicate.
- Register a new document category in `docs/index.md` before using a new
  directory.

## Golden rules

- Inspect related code and tests before editing.
- Make the smallest change that satisfies the stated goal.
- Preserve the current baseline when adding an experimental method.
- Add candidate methods as separately selectable implementations.
- Do not silently rename ROS2 topics, HTTP endpoints, JSON fields, or routes.
- Do not invent file paths, topics, endpoints, parameters, or test results.
- Keep reusable parameters in configuration files rather than evaluation code.
- Record negative and neutral experimental results as well as improvements.
- Do not modify unrelated files while completing a scoped task.
- Report assumptions and unresolved uncertainties instead of presenting them as
  verified facts.

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
- Do not increase speed limits or weaken stopping thresholds without explicit
  user approval.
- Do not delete rosbag files, logs, models, datasets, or experiment artifacts.
- Do not execute destructive commands, force pushes, or irreversible repository
  operations without explicit user approval.
- Stop and report the issue when the current system state cannot be verified
  safely.

## Communication and change approval

- Respond to the user in Korean unless the user explicitly requests another
  language.
- Preserve the original English spelling of code, file paths, commands, ROS2
  topics, HTTP endpoints, JSON fields, class names, and function names.
- For analysis-only, review, and investigation requests, report the findings
  before modifying any files.
- A direct request to implement, fix, create, or update something counts as
  approval to modify files within the explicitly requested scope.
- Do not modify files when the user has requested analysis only.
- Clearly distinguish verified behavior, inferred behavior, and proposed
  changes.
- Request additional approval before expanding the scope, performing
  destructive actions, or executing safety-sensitive commands.
- When approval is requested for a command, explain its purpose and whether it
  changes files, repository history, running processes, or robot state.

## Required workflow

For substantial, behavior-changing, experimental, or safety-sensitive work:

1. Read the relevant documents and source files.
2. Create or update an execution plan under `docs/exec-plans/active/`.
3. State the baseline, fixed conditions, metrics, and acceptance criteria.
4. Reproduce the current behavior before modifying it when practical.
5. Add or update an offline test where practical.
6. Implement the smallest scoped change.
7. Run `bash scripts/check.sh`.
8. Run `bash scripts/test_offline.sh` when the change affects logic covered by
   offline tests.
9. For experimental or controller changes, run the relevant baseline and
   candidate evaluations.
10. For experiments, save reproducible results under `artifacts/runs/`.
11. Review the final diff and document remaining limitations.
12. Move completed execution plans to `docs/exec-plans/completed/`.

Small documentation-only, formatting-only, or comment-only changes do not
require an execution plan or experimental evaluation unless they alter
documented safety requirements, interfaces, or expected system behavior.

## Experiment requirements

For comparative experiments:

- Use the same routes, inputs, initial conditions, speed limits, tolerances,
  sampling rates, and evaluation metrics for the baseline and candidate.
- Change only the variable under evaluation.
- Preserve the original baseline implementation.
- Record the exact configuration and commit used for each run.
- Record failures, interrupted runs, and excluded samples with reasons.
- Do not claim improvement based only on a single favorable run when repeated
  runs are practical.
- Keep raw measurements separate from derived summaries and plots.
- Do not overwrite earlier experiment outputs.

For route-following evaluations, record at least:

- Route identifier
- Controller identifier
- Tracking error
- Travel time
- Linear stop count
- Speed and controller parameters
- Start and goal conditions
- Run status and failure reason, when applicable

For Camera–2D LiDAR fusion evaluations, record at least:

- Detection source and model
- Camera and LiDAR configuration
- Sampling and aggregation parameters
- Ground-truth or reference distance
- Estimated distance
- Error metric
- Valid and invalid measurement counts
- Processing time, when evaluated

## Standard checks

- General checks: `bash scripts/check.sh`
- Offline unit checks: `bash scripts/test_offline.sh`

Live ROS2, Isaac Sim, Ollama, Flask, and real-robot commands require explicit
user approval and are not part of automatic verification.

When a check cannot run because of a missing dependency or unavailable
environment, report the exact command, error, and unverified behavior. Do not
describe the check as passing.

## Artifact handling

- Store reproducible experiment outputs under `artifacts/runs/`.
- Use a distinct run directory or run identifier for each experiment.
- Preserve raw logs and measurements used to calculate reported results.
- Do not commit generated caches, temporary files, large models, or unrelated
  runtime output.
- Keep `artifacts/runs/.gitkeep` so the directory exists in a clean checkout.
- Review staged files before committing to ensure that only intentional source,
  documentation, test, and lightweight metadata files are included.

## Definition of done

A task is complete only when:

- The stated acceptance criteria have been evaluated.
- Relevant checks pass, or any checks that could not run are explicitly
  documented.
- The final diff contains only intended changes.
- Documentation reflects the final behavior.
- Remaining risks and limitations are listed.
- No unapproved live or safety-sensitive command was executed.
- For behavior-changing work, the existing baseline remains reproducible.
- For comparative experiments, baseline and candidate use the same inputs,
  fixed conditions, and metrics.
- For experiments, results and execution metadata are saved under
  `artifacts/runs/`.
- For work requiring an execution plan, the completed plan is moved to
  `docs/exec-plans/completed/`.
