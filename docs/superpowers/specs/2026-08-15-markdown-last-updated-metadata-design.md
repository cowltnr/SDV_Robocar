> Last updated: 2026-08-15 21:16 KST

# Markdown Last-Updated Metadata Design

## Objective

Make the most recent document-edit time immediately visible at the top of each
project Markdown file, and make Codex maintain that value whenever it creates
or changes Markdown documentation.

## Scope

Apply the metadata rule to every `.md` file under the repository root,
including tracked files, intentional untracked project documents, and the
local-only `WEEKLY_REPORT_AUTOMATION.md` file.

Exclude these trees because they are embedded runtimes, repository internals,
generated work state, or caches rather than maintained project documentation:

- `IsaacSim/`
- `.git/`
- `.superpowers/sdd/`
- directories named `__pycache__`

The implementation must not edit production Python or ROS2 files and must not
start any server, ROS2 node, simulator, Ollama process, or robot process.

## Metadata format and position

The first line of every in-scope Markdown document must use this exact format:

```text
> Last updated: YYYY-MM-DD HH:MM KST
```

One blank line separates the metadata from the document's existing first
content line. The timestamp records the time of the content or metadata edit
in the repository's `Asia/Seoul` timezone. A single timestamp may be used for
all files in one atomic batch update.

## Maintenance rule

Add a rule to `AGENTS.md` requiring Codex to:

1. put the metadata line at the top of every new in-scope Markdown document;
2. update the timestamp whenever it changes an in-scope Markdown document;
3. preserve the exact format and `KST` timezone label; and
4. apply the documented exclusions consistently.

An explicitly requested document path does not override the timestamp rule;
it only determines where the document is stored.

## Enforcement

Extend `tests/unit/test_harness_contract.py` with a filesystem-based contract
test. The test enumerates current `.md` files below the repository root,
filters the excluded trees, and verifies that the first line matches the exact
timestamp pattern.

The test intentionally evaluates existing untracked and local-only Markdown
files when they are present. In a clean checkout it evaluates only files that
exist there, so it does not require local-only documents to be committed.

The timestamp pattern must validate the visible structure, including a
four-digit year, two-digit month/day/hour/minute, and the literal `KST` label.
Calendar validity remains the responsibility of the timestamp producer; no
new third-party date-parsing dependency is required.

## Implementation sequence

1. Capture one `Asia/Seoul` timestamp for the batch.
2. Add or update the focused contract test and confirm it fails before the
   metadata is added.
3. Add the maintenance rule to `AGENTS.md`.
4. Insert the same metadata line at the top of every in-scope Markdown file.
5. Run the focused contract test.
6. Run `bash scripts/check.sh`.
7. Run `bash scripts/test_offline.sh`.
8. Review the complete Markdown-only and test-only diff, preserving unrelated
   local changes.

## Acceptance criteria

- Every in-scope Markdown file present during validation begins with the exact
  `> Last updated: YYYY-MM-DD HH:MM KST` format.
- `AGENTS.md` requires future Markdown creation and edits to maintain the
  timestamp.
- The contract test detects a missing or malformed first-line timestamp.
- `bash scripts/check.sh` and `bash scripts/test_offline.sh` pass, or an exact
  environment-related failure is reported without claiming success.
- No excluded Markdown file, production Python/ROS2 file, live runtime, ROS2
  topic, simulator, or robot state is changed.
- Existing unrelated staged, unstaged, and untracked work remains preserved.

## Limitations

- The timestamp reflects disciplined document maintenance, not filesystem
  `mtime` or Git commit time.
- Direct edits made outside Codex can leave a stale timestamp until the author
  updates it or the contract test reports it.
- A batch metadata migration changes every in-scope Markdown document once,
  producing a deliberately broad documentation diff.
