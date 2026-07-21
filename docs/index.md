# Documentation Index

## Start here

- [`../README.md`](../README.md): user-facing project overview and runtime order
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md): top-level system architecture
- [`safety/robot-safety.md`](safety/robot-safety.md): simulator and robot safety rules
- [`experiments/protocol.md`](experiments/protocol.md): research evaluation protocol

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
