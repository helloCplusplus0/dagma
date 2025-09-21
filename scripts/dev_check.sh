#!/usr/bin/env bash
set -euo pipefail

# scripts/dev_check.sh - 本地快速诊断
# 支持 LANGFLOW_API_KEY 缺省，使用空值避免 compose 环境变量警告

export LANGFLOW_API_KEY=${LANGFLOW_API_KEY:-}

# 保持原有逻辑
export PATH="$HOME/.local/bin:$PATH"

run() {
  if command -v uv >/dev/null 2>&1; then uv run "$@"; else "$@"; fi
}

run ruff format
run ruff check .
run mypy src
run pytest -q
