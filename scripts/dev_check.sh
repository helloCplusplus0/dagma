#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

run() {
  if command -v uv >/dev/null 2>&1; then uv run "$@"; else "$@"; fi
}

run ruff format
run ruff check .
run mypy src
run pytest -q
