#!/usr/bin/env bash
set -euo pipefail

# 加载 .env（若存在）
if [ -f ./.env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# 规范化代理环境变量（导出大小写，便于各类工具识别）
export HTTP_PROXY="${HTTP_PROXY:-${http_proxy:-}}"
export HTTPS_PROXY="${HTTPS_PROXY:-${https_proxy:-}}"
export NO_PROXY="${NO_PROXY:-${no_proxy:-localhost,127.0.0.1}}"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export no_proxy="$NO_PROXY"

# 选择 compose 前端（优先 Podman）
ENGINE="docker"
COMPOSE_CMD="docker compose"
if command -v podman >/dev/null 2>&1; then
  ENGINE="podman"
  if command -v podman-compose >/dev/null 2>&1; then
    COMPOSE_CMD="podman-compose"
  else
    COMPOSE_CMD="podman compose"
  fi
elif ! command -v docker >/dev/null 2>&1; then
  echo "未找到 docker/podman，请安装其中之一" >&2
  exit 1
fi

# 根据引擎重写 127.0.0.1/localhost 代理主机到内部网关别名（运行期使用）
rewrite_proxy_host() {
  local url="$1"; local alias="$2"
  if [[ -n "$url" ]]; then
    url="${url/localhost/$alias}"
    url="${url/127.0.0.1/$alias}"
  fi
  printf '%s' "$url"
}

PROXY_ALIAS="host.docker.internal"
if [ "$ENGINE" = "podman" ]; then
  PROXY_ALIAS="host.containers.internal"
fi

HTTP_PROXY_REWRITTEN=$(rewrite_proxy_host "$HTTP_PROXY" "$PROXY_ALIAS")
HTTPS_PROXY_REWRITTEN=$(rewrite_proxy_host "$HTTPS_PROXY" "$PROXY_ALIAS")

GROUP=${1:-minimal}
ACTION=${2:-up}

# 组合服务列表
services=(postgres user_code webserver daemon)
case "$GROUP" in
  data)
    services+=(mlflow)
    ;;
  vector)
    services+=(qdrant)
    ;;
  ml)
    services+=(mlflow qdrant)
    ;;
  full)
    services+=(mlflow qdrant)
    ;;
  minimal)
    ;;
  *)
    echo "未知分组: $GROUP (可选: minimal|data|vector|ml|full)" >&2
    exit 1
    ;;
  esac

# 构建参数：透传代理以便镜像构建能访问外网（运行期/compose 构建使用别名）
BUILD_ARGS=(
  --build-arg HTTP_PROXY="$HTTP_PROXY_REWRITTEN"
  --build-arg HTTPS_PROXY="$HTTPS_PROXY_REWRITTEN"
  --build-arg NO_PROXY="$NO_PROXY,$PROXY_ALIAS,::1"
)

if [ "$ACTION" = "up" ]; then
  echo "[start_env] 引擎: $ENGINE; 代理: HTTP=$HTTP_PROXY_REWRITTEN, HTTPS=$HTTPS_PROXY_REWRITTEN, NO_PROXY=$NO_PROXY,$PROXY_ALIAS,::1"
  echo "[start_env] 构建镜像（如需）并启动分组: $GROUP -> ${services[*]}"

  # 在 Podman 环境下预先构建并打标签，避免 compose 误触发远端拉取；并使用主机网络直连宿主代理
  if [ "$ENGINE" = "podman" ]; then
    # 计算适用于 host 网络的构建期代理（强制 127.0.0.1，以复用 clash 本机端口）
    BUILD_HTTP_FOR_HOST="$HTTP_PROXY"
    BUILD_HTTPS_FOR_HOST="$HTTPS_PROXY"
    # 如未显式设置代理则不传
    HOST_BUILD_ARGS=()
    if [[ -n "$BUILD_HTTP_FOR_HOST" ]]; then
      # 将可能的 host.containers.internal 替换回 127.0.0.1，适配 --network=host
      BUILD_HTTP_FOR_HOST="${BUILD_HTTP_FOR_HOST/host.containers.internal/127.0.0.1}"
      BUILD_HTTP_FOR_HOST="${BUILD_HTTP_FOR_HOST/host.docker.internal/127.0.0.1}"
      HOST_BUILD_ARGS+=(--build-arg HTTP_PROXY="$BUILD_HTTP_FOR_HOST")
    fi
    if [[ -n "$BUILD_HTTPS_FOR_HOST" ]]; then
      BUILD_HTTPS_FOR_HOST="${BUILD_HTTPS_FOR_HOST/host.containers.internal/127.0.0.1}"
      BUILD_HTTPS_FOR_HOST="${BUILD_HTTPS_FOR_HOST/host.docker.internal/127.0.0.1}"
      HOST_BUILD_ARGS+=(--build-arg HTTPS_PROXY="$BUILD_HTTPS_FOR_HOST")
    fi
    if [[ -n "$NO_PROXY" ]]; then
      HOST_BUILD_ARGS+=(--build-arg NO_PROXY="$NO_PROXY,127.0.0.1,localhost,::1")
    fi
    echo "[start_env] 预构建（podman build --network=host）dagster 镜像: ${DAGSTER_IMAGE:-dagma/dagster:dev}"
    podman build --network=host -f docker/Dockerfile_dagster -t "${DAGSTER_IMAGE:-dagma/dagster:dev}" "${HOST_BUILD_ARGS[@]}" .
    echo "[start_env] 预构建（podman build --network=host）user_code 镜像: ${USER_CODE_IMAGE:-dagma/user-code:dev}"
    podman build --network=host -f docker/Dockerfile_user_code -t "${USER_CODE_IMAGE:-dagma/user-code:dev}" "${HOST_BUILD_ARGS[@]}" .
    echo "[start_env] 预构建（podman build --network=host）mlflow 镜像: ${MLFLOW_IMAGE:-dagma/mlflow:dev}"
    podman build --network=host -f docker/Dockerfile_mlflow -t "${MLFLOW_IMAGE:-dagma/mlflow:dev}" "${HOST_BUILD_ARGS[@]}" .
  fi

  $COMPOSE_CMD build "${BUILD_ARGS[@]}" "${services[@]}"
  $COMPOSE_CMD up -d "${services[@]}"
  echo "Dagster Web UI: http://127.0.0.1:${DAGSTER_WEBSERVER_PORT:-3000}"
  echo "MLflow UI:      http://127.0.0.1:${MLFLOW_PORT:-5000}"
  echo "Qdrant API:     http://127.0.0.1:${QDRANT_PORT:-6333}"
elif [ "$ACTION" = "down" ]; then
  echo "[start_env] 停止并清理全部服务（忽略分组参数）"
  $COMPOSE_CMD down -v
else
  echo "未知动作: $ACTION (可选: up|down)" >&2
  exit 1
fi
