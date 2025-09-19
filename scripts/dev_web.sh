#!/usr/bin/env bash
set -euo pipefail
# 固定以 127.0.0.1 绑定启动 Dagster Web UI，避免某些预览/代理环境下 0.0.0.0 导致的白屏问题。
# 用法：bash scripts/dev_web.sh [--check] [PORT]
#  - --check, -c：可选，启动前先运行质量检查脚本（ruff/mypy/pytest），检查通过后再启动
#  - PORT：可选端口，默认 3333

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CHECK=false
PORT="3333"
PORT_SET=false
HOST="127.0.0.1"
export PATH="$HOME/.local/bin:$PATH"

# 说明：
# - 明确指定模块 -m dagma.definitions，确保与 pyproject.toml 一致，亦便于在多入口项目中显式控制加载来源。
# - 默认 PORT=3333，如需多实例或端口冲突，可传入其他端口。
# - 支持 --check 在启动前先进行质量检查。

# 参数解析
while (( "$#" )); do
  case "$1" in
    --check|-c)
      CHECK=true
      shift
      ;;
    -*)
      echo "[dev_web] 未知参数: $1" >&2
      exit 2
      ;;
    *)
      if [ "$PORT_SET" = false ]; then
        PORT="$1"
        PORT_SET=true
        shift
      else
        echo "[dev_web] 多余的位置参数: $1" >&2
        exit 2
      fi
      ;;
  esac
done

if "$CHECK"; then
  echo "[dev_web] 运行质量检查 (--check) ..."
  bash "$ROOT_DIR/scripts/dev_check.sh"
  echo "[dev_web] 质量检查通过，启动 Dagster Web ..."
fi

exec uv run dagster dev -m dagma.definitions --host "$HOST" --port "$PORT"
