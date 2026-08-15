> Last updated: 2026-08-15 21:16 KST

# Automation Documentation

Store new automation setup, operation, scheduling, and troubleshooting Markdown
documents in this directory.

## Local-only weekly report exception

`WEEKLY_REPORT_AUTOMATION.md` remains at the repository root because the
local-only `scripts/run_weekly_report.sh` reads that exact path. It is
intentionally excluded from Git and must not be moved unless the wrapper and
local exclude rules are updated together and revalidated.
