> Last updated: 2026-08-15 21:16 KST

# Markdown last-updated metadata migration

## Baseline

- Before this implementation plan was added, 37 in-scope Markdown files
  existed; only the approved design already had the timestamp.
- The current checkout is `harness/bootstrap`.

## Fixed conditions

- No production Python or ROS2 edits.
- No live runtime commands.
- Exclude `IsaacSim/`, `.git/`, `.superpowers/sdd/`, and directories named
  `__pycache__`.
- Preserve unrelated work.

## Metric and acceptance criteria

- Metric: number and paths of in-scope Markdown files with a missing or
  malformed first line.
- Acceptance: zero invalid files, focused test green, both standard scripts
  green, tracked commit scope reviewed, and untracked documents preserved.

## Progress log

- 2026-08-15 21:15 KST: execution plan created. The approved inventory command
  reported 38 currently discoverable in-scope Markdown files before this plan
  was added.
- RED result: focused contract test failed as expected, listing 36 invalid
  in-scope Markdown files.
- Batch timestamp: `2026-08-15 21:16 KST`.
- Validation results: focused contract test passed twice after the rewrite; the
  approved inventory reports 39 in-scope Markdown files.

## Decision log

- Do not stage untracked documents wholesale: their content predates or is
  unrelated to this timestamp migration, so only task-owned files and tracked
  timestamp-only changes will be committed.
- The first bulk-rewrite command was rejected by Perl because its replacement
  delimiter was omitted. It made no file changes; the corrected command using
  the required delimiter completed successfully with the recorded batch
  timestamp.
