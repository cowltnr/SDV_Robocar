# Codex Harness Bootstrap

## Status

Completed

## Goal

Create the minimum repository structure that allows Codex CLI to inspect,
modify, and validate the ICTC2026 project safely and reproducibly.

## Scope

Included:

- Project instructions
- Architecture and documentation map
- Robot safety policy
- Experiment protocol
- Codex sandbox and approval configuration
- Command rules
- Minimal static and offline checks
- Initial repository inspection

Excluded:

- Fusion algorithm changes
- Controller parameter changes
- VLM model changes
- Isaac Sim motion tests
- Physical LIMO tests
- Skills, MCP, Hooks, Memories, and custom Subagents

## Audit baseline and acceptance method

- Baseline: production source at Git commit `68cb795` on branch
  `harness/bootstrap`, inspected without starting a runtime process.
- Fixed conditions: current checkout, static source inspection only, no changes
  to production Python or ROS2 files, and no live ROS2/HTTP/simulator/robot use.
- Changed files: architecture/documentation, this execution plan, and harness
  contract tests only.
- Metrics: complete static inventories of project entry points, ROS2
  publishers/subscribers, HTTP endpoints/ports, `/sim/cmd_vel` publishers,
  inter-module JSON fields, VLM failure/timeout paths, and absolute paths.
- Acceptance: every architecture claim has a `Verified`, `Partially verified`,
  or `Assumption` label with source file and line-range evidence; README/code
  mismatches are recorded; `bash scripts/check.sh` passes.
- Limitation: static inspection does not prove runtime availability, QoS
  compatibility, network reachability, or robot motion behavior.

## Tasks

- [x] Create `.codex/config.toml`
- [x] Create root `AGENTS.md`
- [x] Create initial `ARCHITECTURE.md`
- [x] Create documentation index
- [x] Create robot safety policy
- [x] Create experiment protocol
- [x] Create project command rules
- [x] Create minimal check scripts
- [x] Create minimal harness contract tests
- [x] Restart Codex and verify loaded instructions
- [x] Inspect source code and update architecture documentation
- [x] Identify all ROS2 topics and HTTP endpoints
- [x] Identify all `/sim/cmd_vel` publishers
- [x] Identify hard-coded paths and external runtime dependencies
- [x] Review the final diff

## Acceptance criteria

- Codex loads the root `AGENTS.md`.
- Project `.codex/config.toml` is active.
- Dangerous commands are prompted or forbidden by rules.
- `bash scripts/check.sh` succeeds.
- No production Python or ROS2 behavior is changed.
- The architecture document distinguishes verified facts from assumptions.
- Live ROS2, Isaac Sim, Ollama, Flask, and robot commands are not executed.

## Progress log

### 2026-07-21

- Initial harness plan created.
- Loaded the repository instructions, architecture, documentation index, robot
  safety policy, experiment protocol, and this plan.
- Defined a static-inspection baseline and explicitly excluded all live ROS2,
  Flask, Ollama, Isaac Sim, and robot activity.
- Inventoried project application/ROS2 entry points and offline evaluation
  entry points.
- Inventoried explicit ROS2 publishers/subscribers, implicit TF2 subscriptions,
  all Flask endpoints and bind ports, and outbound HTTP dependencies.
- Confirmed that only `waypoint_tools/point_follower.py` and
  `waypoint_tools/pure_pursuit_follower.py` create `/sim/cmd_vel` publishers;
  `imo_control.py` publishes `/cmd_vel` instead.
- Traced VLM candidate validation, the 60-second edge timeout, the 180-second
  Ollama timeout, and stopped-state behavior.
- Found duplicate inference code that publishes `/selected_route` even after a
  failed VLM result and after a goal-aware `/selected_route_goal` result.
- Found that valid intents never write the shared intent-state file and invalid
  intents use an undefined `self.current_intent_state_file` attribute.
- Documented inter-module JSON fields, missing schema validation, absolute
  paths, inactive controller HTTP calls, and README/source mismatches in
  `ARCHITECTURE.md`.
- Added an offline harness test requiring the architecture audit sections and
  verification labels; observed the expected pre-documentation test failure.
- Confirmed the new documentation contract test passes, then ran
  `bash scripts/check.sh`; static compilation and all six offline harness tests
  passed.
- Reviewed the final documentation/test scope and validated that cited source
  ranges do not exceed their referenced files.

## Decision log

- Start with one root `AGENTS.md`.
- Store detailed project knowledge under `docs/`.
- Use standard-library tests before adding new Python test dependencies.
- Defer Skills, MCP, Hooks, Memories, and custom Subagents.
- Treat repository-owned tracked application and evaluation code as the audit
  scope; treat the untracked embedded `IsaacSim/` installation as an external
  runtime tree, while recording its project-specific absolute shebang.
- Record code defects as `Partially verified` architecture behavior instead of
  changing production code during the documentation-only harness audit.
- Include transient `ros2 topic pub` subprocesses in the ROS2 publisher
  inventory and distinguish them from persistent `rclpy` publishers.
- Treat the logging server's “shared with other vehicles” behavior as an
  assumption because source implements local storage but no retrieval or
  distribution endpoint.

## Completion notes

- Completed on 2026-07-21 using static inspection only.
- Acceptance criteria evaluated: Codex instructions/configuration were present,
  dangerous commands remained restricted, architecture claims were classified,
  and the full check passed.
- Files changed by this audit were limited to `ARCHITECTURE.md`, the harness
  contract test, and this execution plan.
- No production Python or ROS2 source was edited.
- No live ROS2, Flask, Ollama, Isaac Sim, simulator, or robot command was run,
  and no ROS2 topic was published.
- Remaining limitations and production mismatches are recorded in
  `ARCHITECTURE.md`; correcting them requires a separately approved production
  task with offline tests before any replay or live validation.
