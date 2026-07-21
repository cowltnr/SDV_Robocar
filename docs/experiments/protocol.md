# Experiment Protocol

## Purpose

This document defines the minimum requirements for reproducible experiments
in the SDV Robocar project.

The protocol applies to Camera–2D LiDAR fusion, VLM route selection,
route-following controllers, and related safety evaluations.

## General principles

- Preserve the original baseline implementation.
- Add experimental methods as separately selectable candidates.
- Compare the baseline and candidate using the same inputs and metrics.
- Define metrics and acceptance criteria before reviewing final results.
- Record negative and neutral results as well as improvements.
- Do not overwrite previous experiment outputs.
- Do not remove raw results after aggregate metrics are generated.
- Do not change metrics after viewing final results without documenting why.
- Clearly separate measured results from assumptions and interpretations.
- Use the lowest-risk validation level capable of answering the research question.

## Required experiment definition

Every non-trivial experiment must define:

- Experiment ID
- Research question
- Baseline method
- Candidate method
- Input dataset or recorded run
- Fixed conditions
- Changed variables
- Evaluation metrics
- Acceptance criteria
- Validation level
- Reproduction command
- Output directory
- Expected risks and limitations

The experiment definition must be written before candidate results are
reviewed.

## Validation levels

Each experiment must use one of the following validation levels:

- `offline`: saved image, LiDAR, JSON, CSV, or other static data
- `replay`: recorded ROS2, sensor, or rosbag data replay
- `isaac_sim`: live NVIDIA Isaac Sim evaluation
- `real_limo`: physical LIMO robot evaluation

Use the lowest validation level capable of answering the research question.

Validation should normally progress in this order:

~~~text
offline
  -> replay
  -> isaac_sim
  -> real_limo
~~~

An experiment must not move to a higher validation level merely because a
lower-level test is missing or failing.

## Baseline preservation

The existing baseline must remain available after an experimental method is
added.

A candidate method should be selected through a configuration value, command
argument, or clearly separated module. Do not replace the baseline
implementation in place unless the change is an approved bug fix.

Baseline and candidate evaluations must use:

- The same evaluation samples
- The same ground-truth data
- The same preprocessing
- The same metric implementation
- The same hardware mode when latency is compared
- The same success and failure criteria

Any unavoidable difference must be recorded in the experiment report.

## Fusion comparison requirements

Keep the following fixed unless one of them is the tested variable:

- Input camera frame
- LiDAR scan
- YOLO detections
- Camera resolution
- Camera calibration
- Camera horizontal field of view
- LiDAR angular configuration
- Valid LiDAR distance range
- Object class
- Ground-truth distance
- Evaluation samples

Recommended fusion metrics include:

- Mean Absolute Error (MAE)
- Root Mean Square Error (RMSE)
- Invalid estimate rate
- Valid estimate rate
- Processing latency
- Error by distance range
- Error by image angle
- Error by bounding-box size
- Error by object count
- Failure cases involving walls or overlapping objects

A fusion comparison must state whether YOLO detections are fixed or generated
again for each run.

## Controller comparison requirements

Keep the following fixed unless one of them is the tested variable:

- Reference route
- Initial robot pose
- Goal point
- Maximum linear speed
- Maximum angular speed
- Goal tolerance
- Control frequency
- Simulation environment
- Obstacle arrangement
- Sensor configuration
- Route completion condition

Recommended controller metrics include:

- Mean tracking error
- RMSE when required
- Maximum tracking error
- Travel time
- Linear stop count
- Route completion
- Collision count
- Boundary violation
- Command smoothness
- Final goal error

Controller comparisons must record whether travel time is measured from the
rosbag recording interval or from actual motion start to route completion.

Only one controller may publish `/sim/cmd_vel` during a live comparison.

## VLM comparison requirements

Keep the following fixed unless one of them is the tested variable:

- Input image
- Obstacle JSON
- User goal
- Candidate-route list
- Prompt structure
- Response schema
- Timeout
- VLM model and version
- Inference settings
- Safety validator
- Route-validity rules

Recommended VLM metrics include:

- Valid candidate selection rate
- Invalid route rejection rate
- Timeout rate
- Response latency
- JSON parsing success rate
- Stopped-state preservation rate
- Route-selection consistency
- Goal-preservation rate
- Safety-rule violation rate

A VLM output is valid only when the selected route belongs to the supplied
candidate-route list and passes the deterministic safety validator.

An invalid, unavailable, malformed, or timed-out VLM response must not resume
robot motion.

## Ground-truth and dataset requirements

Each dataset or recorded run must have a stable identifier.

Record:

- Dataset or run name
- Data collection date when available
- Evaluation split
- Sample count
- Ground-truth source
- Excluded samples
- Exclusion reasons
- File checksum or version when practical

Do not evaluate a candidate only on samples selected after reviewing its
results.

Training, validation, tuning, and final evaluation data must be separated
when model learning or parameter tuning is involved.

## Required run metadata

Each run must record:

- Run ID
- Date and time
- Git commit
- Git branch
- Experiment ID
- Method name
- Configuration file
- Input data identifier
- Model name and version when applicable
- Random seed when applicable
- Validation level
- Command used
- Hardware or execution environment
- Success or failure
- Failure reason
- Metric output location
- Plot output location

## Run ID format

Use a run ID that is unique and easy to sort.

Recommended format:

~~~text
YYYY-MM-DD_HHMM_<experiment-id>_<method>_<git-short-commit>
~~~

Example:

~~~text
2026-07-21_1530_fusion-sampling_baseline_ab12cd3
~~~

## Result storage

Store each run in a separate directory:

~~~text
artifacts/runs/<run-id>/
├── manifest.json
├── config.yaml
├── metrics.json
├── per_sample.csv
├── environment.txt
├── stdout.log
├── stderr.log
└── plots/
~~~

Do not overwrite an existing run directory.

Large raw datasets, rosbag files, and model weights must not be copied into
every run directory. Store their paths, identifiers, versions, and checksums
in `manifest.json` instead.

## Minimum manifest fields

The run manifest should contain at least:

~~~json
{
  "run_id": "",
  "experiment_id": "",
  "git_commit": "",
  "git_branch": "",
  "method": "",
  "config": "",
  "input_data": "",
  "validation_level": "",
  "command": "",
  "success": false,
  "failure_reason": "",
  "metrics_file": "metrics.json"
}
~~~

Additional fields may be added when required by a specific experiment.

## Result interpretation

Experiment reports must distinguish:

- Directly measured results
- Calculated aggregate metrics
- Observed qualitative behavior
- Possible explanations
- Unverified assumptions
- Known limitations

Do not describe a method as better based only on one example, one route, or
one successful run unless the scope of the claim is explicitly limited.

Performance improvement claims must include the baseline value, candidate
value, absolute difference, and percentage difference when meaningful.

## Failure handling

A failed experiment is still a valid recorded result.

When a run fails:

- Preserve available logs and partial outputs.
- Set `success` to `false` in the manifest.
- Record the failure reason.
- Record the last completed validation step.
- Do not silently remove the failed run.
- Do not report partial metrics as complete results.

## Reproducibility requirements

A completed experiment must provide enough information to repeat the run.

At minimum, another run must be able to recover:

- The evaluated code revision
- The experiment configuration
- The input dataset or recorded run
- The execution command
- The metric definitions
- The output location
- Any required manual preparation

Manual preparation steps must be documented explicitly.

## Completion rule

An experiment is complete only when:

- The research question and tested variable are clear.
- The baseline remains available and reproducible.
- Baseline and candidate conditions are comparable.
- The procedure can be reproduced.
- Raw or per-sample results are available.
- Aggregate metrics are saved.
- Execution metadata is recorded.
- Failures and limitations are documented.
- Safety requirements for the validation level are satisfied.
- The result does not depend on an undocumented manual step.
- The related execution plan is updated.
