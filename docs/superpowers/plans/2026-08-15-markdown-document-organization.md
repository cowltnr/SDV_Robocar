> Last updated: 2026-08-15 21:16 KST

# Markdown Document Organization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `docs/index.md` the central Markdown map and define deterministic default save locations for new Codex-authored Markdown documents.

**Architecture:** Keep the root discovery documents in place, preserve all existing document paths, and add a central categorized index plus an `AGENTS.md` placement policy. Keep the local-only `WEEKLY_REPORT_AUTOMATION.md` at the root because the local wrapper consumes that exact path; use `docs/automation/` for future automation operations documents.

**Tech Stack:** Markdown, Python standard-library `unittest`, Bash validation scripts

## Global Constraints

- Preserve `README.md`, `AGENTS.md`, and `ARCHITECTURE.md` at repository root.
- Preserve the existing uncommitted Research tracking section in `docs/index.md`.
- Do not move or edit `WEEKLY_REPORT_AUTOMATION.md`, `scripts/run_weekly_report.sh`, `.git/info/exclude`, production Python, or ROS2 files.
- Do not start ROS2, Flask, Ollama, Isaac Sim, or a robot, and do not publish ROS2 topics.
- Store Superpowers design documents in `docs/superpowers/specs/` and implementation plans in `docs/superpowers/plans/`.
- Use `docs/exec-plans/active/` while this documented behavior change is active and move the completed execution record to `docs/exec-plans/completed/`.

---

### Task 1: Add and verify the Markdown location contract

**Files:**
- Create: `docs/exec-plans/active/2026-08-15-markdown-document-organization.md`
- Create: `docs/automation/index.md`
- Modify: `AGENTS.md`
- Modify: `docs/index.md`
- Modify: `tests/unit/test_harness_contract.py`
- Move after verification: `docs/exec-plans/active/2026-08-15-markdown-document-organization.md` to `docs/exec-plans/completed/2026-08-15-markdown-document-organization.md`

**Interfaces:**
- Consumes: the approved design at `docs/superpowers/specs/2026-08-15-markdown-document-organization-design.md`, the current `docs/index.md`, and existing harness test discovery in `scripts/test_offline.sh`.
- Produces: a central Markdown location map, Codex save-location policy, automation documentation entry point, and an offline contract test.

- [x] **Step 1: Create the active execution record**

Create `docs/exec-plans/active/2026-08-15-markdown-document-organization.md` with:

```markdown
# Markdown 문서 위치 정리 실행 계획

## Status

Active

## Baseline and fixed conditions

- Baseline: 현재 checkout의 Markdown 28개와 기존 `docs/index.md`.
- Fixed: 루트 특수 문서와 모든 기존 문서 경로를 유지한다.
- Changed: `AGENTS.md`, `docs/index.md`, `docs/automation/index.md`, harness test.
- Excluded: production Python, ROS2, 자동화 wrapper, 실험 산출물.

## Acceptance criteria

- 중앙 색인에서 문서 범주와 기본 저장 위치를 확인할 수 있다.
- `AGENTS.md`에 Markdown 저장 규칙이 있다.
- 로컬 weekly report 예외가 설명된다.
- offline checks가 통과한다.

## Progress log

- 설계 승인 및 구현 계획 작성 완료.

## Decision log

- 루트 특수 문서를 유지하는 혼합형 구조를 사용한다.
- `WEEKLY_REPORT_AUTOMATION.md`는 wrapper 호환성을 위해 루트에 유지한다.
```

- [x] **Step 2: Write the failing contract test**

Append this method to `HarnessContractTest` in `tests/unit/test_harness_contract.py`:

```python
    def test_markdown_document_locations_are_indexed(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        index = (ROOT / "docs/index.md").read_text(encoding="utf-8")

        required_agent_locations = [
            "## Markdown documentation locations",
            "docs/meetings/",
            "docs/experiments/",
            "docs/exec-plans/active/",
            "docs/superpowers/specs/",
            "docs/superpowers/plans/",
            "docs/automation/",
        ]
        required_index_entries = [
            "## Markdown location map",
            "superpowers/specs/",
            "superpowers/plans/",
            "automation/index.md",
            "WEEKLY_REPORT_AUTOMATION.md",
        ]

        missing_agents = [text for text in required_agent_locations if text not in agents]
        missing_index = [text for text in required_index_entries if text not in index]

        self.assertEqual([], missing_agents, f"Missing AGENTS.md locations: {missing_agents}")
        self.assertEqual([], missing_index, f"Missing docs index entries: {missing_index}")
        self.assertTrue((ROOT / "docs/automation/index.md").is_file())
```

- [x] **Step 3: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest tests.unit.test_harness_contract.HarnessContractTest.test_markdown_document_locations_are_indexed -v
```

Expected: `FAIL` because the new section strings and `docs/automation/index.md` do not exist yet.

- [x] **Step 4: Add the Markdown placement policy to `AGENTS.md`**

Add a `## Markdown documentation locations` section after `## Main repository areas`. State these exact defaults:

```markdown
- Keep `README.md`, `AGENTS.md`, and `ARCHITECTURE.md` at repository root.
- Use `docs/index.md` as the central document map.
- Store general documents in the closest matching subdirectory under `docs/`.
- Store meeting records in `docs/meetings/`.
- Store safety documents in `docs/safety/`.
- Store experiment protocols and evaluation documents in `docs/experiments/`.
- Store active execution plans in `docs/exec-plans/active/` and move completed plans to `docs/exec-plans/completed/`.
- Store Superpowers designs in `docs/superpowers/specs/` and implementation plans in `docs/superpowers/plans/`.
- Store automation operations documents in `docs/automation/`.
- If the user specifies a path, use that path. Prefer updating an existing document over creating a duplicate.
- Register a new document category in `docs/index.md` before using a new directory.
```

- [x] **Step 5: Create the automation documentation entry point**

Create `docs/automation/index.md` with:

```markdown
# Automation Documentation

Store new automation setup, operation, scheduling, and troubleshooting Markdown documents in this directory.

## Local-only weekly report exception

`WEEKLY_REPORT_AUTOMATION.md` remains at the repository root because the local-only `scripts/run_weekly_report.sh` reads that exact path. It is intentionally excluded from Git and must not be moved unless the wrapper and local exclude rules are updated together and revalidated.
```

- [x] **Step 6: Expand `docs/index.md` without replacing existing user changes**

Add `## Markdown location map` after `## Start here`. Include a compact table with categories and paths for root discovery documents, general documents, safety, experiments, meetings, research direction, active/completed execution plans, Superpowers specs/plans, automation, and experiment run artifacts. Add links to `superpowers/specs/`, `superpowers/plans/`, and `automation/index.md`. Record `../WEEKLY_REPORT_AUTOMATION.md` as a local-only root exception, not a tracked project document. Preserve the existing Research tracking section verbatim.

- [x] **Step 7: Run the focused test and verify GREEN**

Run:

```bash
python3 -m unittest tests.unit.test_harness_contract.HarnessContractTest.test_markdown_document_locations_are_indexed -v
```

Expected: `PASS`.

- [x] **Step 8: Run full offline verification**

Run:

```bash
bash scripts/check.sh
bash scripts/test_offline.sh
git diff --check
```

Expected: all harness tests pass, compilation succeeds, and `git diff --check` produces no output.

- [x] **Step 9: Review scope and complete the execution record**

Confirm that no production Python, ROS2 file, wrapper, local exclude rule, cache, model, dataset, or experiment artifact is in the diff. Update the execution record with the RED/GREEN commands, final verification output, changed files, limitations, and `Status: Completed`, then move it to `docs/exec-plans/completed/2026-08-15-markdown-document-organization.md`.

- [x] **Step 10: Re-run verification after the plan move**

Run:

```bash
bash scripts/check.sh
bash scripts/test_offline.sh
git diff --check
```

Expected: all checks still pass after the final documentation move.

- [x] **Step 11: Commit only the intentional documentation and test files**

Review `git status --short` and stage only:

```text
AGENTS.md
docs/index.md
docs/automation/index.md
docs/exec-plans/completed/2026-08-15-markdown-document-organization.md
docs/superpowers/plans/2026-08-15-markdown-document-organization.md
tests/unit/test_harness_contract.py
```

Commit with:

```bash
git commit -m "docs: organize Markdown document locations"
```
