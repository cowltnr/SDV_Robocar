#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

echo "[check] Verifying required harness files"

required_files=(
  "AGENTS.md"
  "ARCHITECTURE.md"
  ".codex/config.toml"
  ".codex/rules/default.rules"
  "docs/index.md"
  "docs/safety/robot-safety.md"
  "docs/experiments/protocol.md"
  "docs/exec-plans/tech-debt.md"
  "scripts/check.sh"
  "scripts/test_offline.sh"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[check] Missing required file: $file" >&2
    exit 1
  fi
done

echo "[check] Compiling project Python files without executing them"

python3 -m compileall -q \
  detector \
  edge_modules \
  edge_threads \
  ictc_test \
  sensor \
  waypoint_tools

while IFS= read -r -d '' file; do
  python3 -m py_compile "$file"
done < <(find . -maxdepth 1 -type f -name '*.py' -print0)

bash scripts/test_offline.sh

echo "[check] All checks passed"
