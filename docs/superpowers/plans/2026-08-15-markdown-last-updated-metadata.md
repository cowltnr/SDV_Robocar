> Last updated: 2026-08-15 21:40 KST

# Markdown Last-Updated Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put a visible KST last-updated timestamp on every maintained project Markdown document and enforce future updates through repository instructions and an offline contract test.

**Architecture:** `AGENTS.md` defines the authoring rule, while `tests/unit/test_harness_contract.py` prunes excluded runtime/work-state trees and checks the first line of every remaining `.md` file. A one-time mechanical migration stamps all currently present in-scope documents without adding a permanent timestamp-generation utility.

**Tech Stack:** Markdown, Python 3 standard library (`os`, `pathlib`, `re`, `unittest`), Bash, ripgrep, Perl for the one-time mechanical rewrite.

## Global Constraints

- The exact first-line format is `> Last updated: YYYY-MM-DD HH:MM KST`.
- The timestamp uses the `Asia/Seoul` timezone and the literal `KST` label.
- Exclude `IsaacSim/`, `.git/`, `.superpowers/sdd/`, and directories named `__pycache__`.
- Include tracked Markdown, intentional untracked project Markdown, and local-only `WEEKLY_REPORT_AUTOMATION.md` when present.
- Do not edit production Python or ROS2 files.
- Do not start servers, ROS2 nodes, Isaac Sim, Ollama, or a robot, and do not publish ROS2 topics.
- Preserve unrelated staged, unstaged, and untracked work. Do not add an entire pre-existing untracked document to Git merely because its timestamp was updated.
- Validate in this order: focused offline test, `bash scripts/check.sh`, `bash scripts/test_offline.sh`, final diff review.

---

### Task 1: Add the Markdown timestamp contract and migrate current documents

**Files:**
- Create: `docs/exec-plans/active/2026-08-15-markdown-last-updated-metadata.md`
- Modify: `AGENTS.md`
- Modify: every `.md` returned by the approved inventory command
- Modify: `tests/unit/test_harness_contract.py`
- Reference: `docs/superpowers/specs/2026-08-15-markdown-last-updated-metadata-design.md`

**Interfaces:**
- Consumes: repository root `ROOT: pathlib.Path` and the filesystem tree below it.
- Produces: `iter_project_markdown_files() -> Iterator[pathlib.Path]`, `HarnessContractTest.test_markdown_files_start_with_last_updated_timestamp()`, the `AGENTS.md` maintenance rule, and a green in-scope Markdown tree.

- [x] **Step 1: Record the active execution baseline**

Create `docs/exec-plans/active/2026-08-15-markdown-last-updated-metadata.md` with the required first-line timestamp and these concrete facts:

- Baseline: 37 in-scope Markdown files existed before the implementation plan was added; only the approved design already had the timestamp.
- Fixed conditions: current `harness/bootstrap` checkout, no production Python/ROS2 edits, no live runtime commands, the four documented exclusions, and unrelated work preserved.
- Metric: number and paths of in-scope Markdown files with a missing or malformed first line.
- Acceptance: zero invalid files, focused test green, both standard scripts green, tracked commit scope reviewed, untracked documents preserved.
- Progress and decision logs: record the RED result, batch timestamp, validation results, and why untracked content is not staged wholesale.

- [x] **Step 2: Write the failing filesystem contract test**

Add `from collections.abc import Iterator`, `import os`, and `import re` to
`tests/unit/test_harness_contract.py`, then add this helper above the test
class:

```python
EXCLUDED_MARKDOWN_ROOTS = {".git", "IsaacSim"}
LAST_UPDATED_PATTERN = re.compile(
    r"^> Last updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2} KST$"
)


def iter_project_markdown_files() -> Iterator[Path]:
    for directory, dirnames, filenames in os.walk(ROOT):
        relative_directory = Path(directory).relative_to(ROOT)
        kept_directories = []
        for name in dirnames:
            relative_child = relative_directory / name
            if name == "__pycache__":
                continue
            if relative_child.parts[0] in EXCLUDED_MARKDOWN_ROOTS:
                continue
            if relative_child.parts[:2] == (".superpowers", "sdd"):
                continue
            kept_directories.append(name)
        dirnames[:] = kept_directories

        for filename in filenames:
            if filename.endswith(".md"):
                yield Path(directory) / filename
```

Add this test method to `HarnessContractTest`:

```python
    def test_markdown_files_start_with_last_updated_timestamp(self) -> None:
        invalid = []
        for path in sorted(iter_project_markdown_files()):
            lines = path.read_text(encoding="utf-8").splitlines()
            first_line = lines[0] if lines else ""
            if LAST_UPDATED_PATTERN.fullmatch(first_line) is None:
                invalid.append(str(path.relative_to(ROOT)))

        self.assertEqual(
            [],
            invalid,
            f"Markdown files missing valid last-updated metadata: {invalid}",
        )
```

- [x] **Step 3: Run the focused test and verify RED**

Run:

```bash
python3 -m unittest tests.unit.test_harness_contract.HarnessContractTest.test_markdown_files_start_with_last_updated_timestamp -v
```

Expected: FAIL listing the currently unstamped in-scope Markdown files. Record the exact invalid-file count in the active execution plan. Failure for another reason must be investigated before continuing.

#### Implementation phase: define the authoring rule and migrate current documents

**Files:**
- Modify: `AGENTS.md`
- Modify: every `.md` returned by the approved inventory command
- Modify: `docs/exec-plans/active/2026-08-15-markdown-last-updated-metadata.md`
- Test: `tests/unit/test_harness_contract.py`

**Interfaces:**
- Consumes: the exact first-line contract from Task 1 and the four exclusion rules.
- Produces: an in-scope Markdown tree in which every current document satisfies `LAST_UPDATED_PATTERN`.

- [x] **Step 1: Add the future-maintenance rule to `AGENTS.md`**

Under `## Markdown documentation locations`, add these exact requirements:

```markdown
- Start every maintained project Markdown file with
  `> Last updated: YYYY-MM-DD HH:MM KST`, followed by one blank line.
- Whenever Codex creates or changes a maintained Markdown file, update that
  timestamp using the current `Asia/Seoul` time.
- Apply the timestamp rule to tracked, intentional untracked, and local-only
  project documents. Exclude `IsaacSim/`, `.git/`, `.superpowers/sdd/`, and
  directories named `__pycache__`.
```

- [x] **Step 2: Capture one batch timestamp**

Run:

```bash
DOC_TIMESTAMP="$(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M KST')"
export DOC_TIMESTAMP
```

Record the resulting value in the active execution plan. Do not reuse the plan-writing timestamp unless it is still the actual implementation minute.

- [x] **Step 3: Mechanically stamp every in-scope Markdown file**

First preview the exact inventory:

```bash
rg --files -uu -g '*.md' -g '!IsaacSim/**' -g '!.git/**' -g '!.superpowers/sdd/**' -g '!**/__pycache__/**' | sort
```

Then perform the one-time bulk rewrite:

```bash
rg --files -0 -uu -g '*.md' -g '!IsaacSim/**' -g '!.git/**' -g '!.superpowers/sdd/**' -g '!**/__pycache__/**' | xargs -0 perl -0pi -e 'BEGIN { $stamp = $ENV{"DOC_TIMESTAMP"} } s/\A(?:> Last updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2} KST\R\R)?/> Last updated: $stamp\n\n/'
```

This is a formatting-only bulk mechanical rewrite. It inserts the line when absent and replaces an existing valid first-line timestamp without duplicating it.

- [x] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
python3 -m unittest tests.unit.test_harness_contract.HarnessContractTest.test_markdown_files_start_with_last_updated_timestamp -v
```

Expected: PASS.

- [x] **Step 5: Inspect exclusion and formatting invariants**

Run:

```bash
rg --files -uu -g '*.md' -g '!IsaacSim/**' -g '!.git/**' -g '!.superpowers/sdd/**' -g '!**/__pycache__/**' | wc -l
```

Run the focused test from Step 4 again after any inventory change.

Expected: the focused test reports no invalid in-scope file and no excluded
file appears in the implementation diff.

- [x] **Step 6: Commit the green migration task**

Review and stage `AGENTS.md`, `tests/unit/test_harness_contract.py`, the active
execution plan, this implementation plan, and timestamp-only changes to
tracked Markdown. Preserve pre-existing unrelated `docs/index.md` content by
staging only this task's hunk, and do not stage pre-existing untracked Markdown
wholesale. Confirm the staged paths contain no production Python/ROS2 file or
excluded tree, then run:

```bash
git diff --cached --check
git commit -m "docs: add Markdown update timestamps"
```

---

### Task 2: Validate, preserve local work, and complete the execution record

**Files:**
- Modify/move: `docs/exec-plans/active/2026-08-15-markdown-last-updated-metadata.md` to `docs/exec-plans/completed/2026-08-15-markdown-last-updated-metadata.md`
- Review: all tracked Markdown timestamp changes, `AGENTS.md`, `tests/unit/test_harness_contract.py`, and this implementation plan
- Preserve without wholesale staging: pre-existing untracked Markdown and unrelated `docs/index.md` content

**Interfaces:**
- Consumes: the green focused test and migrated document tree from Task 2.
- Produces: validated documentation/test changes, a completed execution record, and a commit containing only intended tracked changes.

- [x] **Step 1: Run the repository standard check**

Run:

```bash
bash scripts/check.sh
```

Expected: static compilation succeeds and all offline tests pass. If LibreOffice or `dconf` is blocked by the sandbox, rerun the same approved command outside the sandbox and record both results.

- [x] **Step 2: Run the offline suite separately**

Run:

```bash
bash scripts/test_offline.sh
```

Expected: all offline tests pass.

- [x] **Step 3: Complete the execution record**

Update the progress and decision logs with:

- RED and GREEN focused-test evidence;
- the exact batch timestamp and final in-scope file count;
- `scripts/check.sh` and `scripts/test_offline.sh` results;
- confirmation that excluded trees and production Python/ROS2 files were untouched;
- confirmation that no live or safety-sensitive command ran;
- remaining limitation that direct non-Codex edits can leave a stale but well-formed timestamp.

Mark acceptance criteria complete and move the plan to `docs/exec-plans/completed/2026-08-15-markdown-last-updated-metadata.md`. Update its first-line timestamp because moving/completing changes the document.

- [x] **Step 4: Review and stage only intentional tracked content**

Run:

```bash
git status --short
git diff --check
git diff --name-status
git diff -- tests/unit/test_harness_contract.py AGENTS.md
```

Use `git diff --no-index /dev/null <path>` to inspect intentional untracked Markdown before deciding whether it belongs to this task. Do not stage pre-existing untracked documents wholesale. For tracked files containing unrelated unstaged edits, stage only the timestamp hunk and this task's own changes, then verify the remaining unstaged diff is unchanged.

- [x] **Step 5: Commit the completed execution record and review fixes**

Stage the completed execution record, updated implementation-plan checkboxes,
and any reviewed fixes not already included in Task 1. Confirm the staged paths
contain no production Python/ROS2 file and no excluded tree. If the staged diff
is non-empty, run:

```bash
git diff --cached --check
git commit -m "docs: complete Markdown timestamp rollout"
```

- [x] **Step 6: Verify the committed state**

Run:

```bash
git show --stat --oneline HEAD
git status --short --branch
bash scripts/check.sh
```

Expected: the commit contains only intended documentation and `tests/unit/test_harness_contract.py`; all checks pass; pre-existing unrelated unstaged/untracked files remain present; `harness/bootstrap` remains checked out; no push or merge occurs unless separately requested.
