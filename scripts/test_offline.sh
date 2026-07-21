#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

echo "[offline] Running harness contract tests"

python3 -m unittest discover \
  -s tests/unit \
  -p 'test_*.py' \
  -v

echo "[offline] All offline tests passed"
