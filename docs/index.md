> Last updated: 2026-08-15 21:16 KST

# Documentation Index

## Start here

- [`../README.md`](../README.md): user-facing project overview and runtime order
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md): top-level system architecture
- [`safety/robot-safety.md`](safety/robot-safety.md): simulator and robot safety rules
- [`experiments/protocol.md`](experiments/protocol.md): research evaluation protocol

## Markdown location map

Use this table as the default location guide when creating or looking for a
Markdown document. An explicitly requested path takes precedence.

| Document category | Location | Notes |
|---|---|---|
| Project overview | [`../README.md`](../README.md) | Keep at repository root for GitHub and tool discovery. |
| Codex repository instructions | [`../AGENTS.md`](../AGENTS.md) | Keep at repository root so the rules apply to the whole repository. |
| Top-level architecture | [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | Verified architecture and interface audit. |
| General project documentation | [`./`](./) | Use the closest matching category below instead of adding arbitrary root files. |
| Safety | [`safety/`](safety/) | Robot, simulator, ROS2, and runtime safety rules. |
| Experiments | [`experiments/`](experiments/) | Protocols, evaluation definitions, and reproducibility requirements. |
| Meeting records | `docs/meetings/` | Dated meeting records and their index. |
| Research direction | `docs/research-direction.md` | Current priorities and decision history. |
| Active execution plans | [`exec-plans/active/`](exec-plans/active/) | Work currently in progress. |
| Completed execution plans | [`exec-plans/completed/`](exec-plans/completed/) | Completed work, decisions, and validation evidence. |
| Technical debt | [`exec-plans/tech-debt.md`](exec-plans/tech-debt.md) | Verified issues outside the current task scope. |
| Superpowers designs | [`superpowers/specs/`](superpowers/specs/) | Approved design documents generated during brainstorming. |
| Superpowers implementation plans | [`superpowers/plans/`](superpowers/plans/) | Task-by-task implementation plans. |
| Automation operations | [`automation/index.md`](automation/index.md) | Setup, scheduling, operation, and troubleshooting documents. |
| Experiment run artifacts | [`../artifacts/runs/`](../artifacts/runs/) | Run metadata and results; follow the experiment protocol. |
| Local weekly-report instructions | `../WEEKLY_REPORT_AUTOMATION.md` | Local-only root exception consumed by `scripts/run_weekly_report.sh`; intentionally excluded from Git. |

To enumerate all current project Markdown files while excluding the embedded
Isaac Sim runtime, Git internals, and caches, run:

```bash
rg --files -uu -g '*.md' -g '!IsaacSim/**' -g '!.git/**' -g '!**/__pycache__/**' | sort
```

## Execution plans

- [`exec-plans/active/`](exec-plans/active/): work currently in progress
- [`exec-plans/completed/`](exec-plans/completed/): completed work and decisions
- [`exec-plans/tech-debt.md`](exec-plans/tech-debt.md): known technical debt

## Document responsibilities

### Architecture documents

Describe current system boundaries, modules, interfaces, and data flow.
They must reflect the implementation rather than intended future behavior.

### Safety documents

Describe commands and state transitions that can affect Isaac Sim or a
real robot. Safety rules must also be enforced through code or tests where
practical.

### Experiment documents

Define baselines, fixed conditions, datasets, metrics, result storage,
and the order of offline, simulator, and real-robot validation.

### Execution plans

Record the goal, scope, progress, decisions, validation evidence,
remaining limitations, and completion status of non-trivial work.

## Update rule

When a code change alters architecture, interfaces, safety behavior,
evaluation methods, or runtime commands, update the corresponding document
in the same change.
