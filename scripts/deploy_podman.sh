#!/usr/bin/env bash
# 一键使用 Podman 在云服务器部署 Dagma
# 说明：
#  - 依赖 Podman 4.x 及 podman compose（或 podman-compose 插件）
#  - 会使用 GHCR 镜像 ghcr.io/<org>/<repo>/{dagster,user-code}:<tag>
#  - 需要事先完成 `podman login ghcr.io`（使用具有 read:packages 的 GH PAT）
#  - 默认从当前仓库的 remote.origin 解析 <org>/<repo>，也可通过参数覆盖
#
# 用法：
#   scripts/deploy_podman.sh --tag v0.1.1 [--ns ghcr.io/ORG/REPO] [--env .env.podman]
#
# 示例：
#   scripts/deploy_podman.sh --tag v0.1.1
#   scripts/deploy_podman.sh --tag ci-<shortsha> --ns ghcr.io/acme/dagma
#
set -euo pipefail

TAG=""
NS=""
ENV_FILE=".env.podman"

log() { printf "[deploy] %s\n" "$*"; }
err() { printf "[deploy][ERROR] %s\n" "$*" 1>&2; }

usage() {
  cat <<EOF
用法: $0 --tag <TAG> [--ns ghcr.io/ORG/REPO] [--env <ENV_FILE>]
参数:
  --tag <TAG>     必填。镜像标签，例如 v0.1.1 或 ci-abcdefg
  --ns  <NS>      可选。GHCR 命名空间，形如 ghcr.io/ORG/REPO；默认从 git remote 解析
  --env <FILE>    可选。生成/使用的 env 文件（用于 compose 覆盖镜像），默认 .env.podman
EOF
}

# 解析参数
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      TAG="${2:-}"; shift 2;;
    --ns)
      NS="${2:-}"; shift 2;;
    --env)
      ENV_FILE="${2:-}"; shift 2;;
    -h|--help)
      usage; exit 0;;
    *) err "未知参数: $1"; usage; exit 2;;
  esac
done

if [[ -z "$TAG" ]]; then err "必须指定 --tag"; usage; exit 2; fi

# 检查 podman / compose
if ! command -v podman >/dev/null 2>&1; then err "未检测到 podman，请先安装 (Ubuntu: apt-get install -y podman)"; exit 2; fi
if podman compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(podman compose)
elif command -v podman-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(podman-compose)
else
  err "未检测到 podman compose，请安装 podman-compose 或升级 podman 以内置 compose"
  exit 2
fi

log "容器运行时: $(podman --version | head -n1)"

# 解析 GHCR 命名空间
if [[ -z "$NS" ]]; then
  # 尝试从 git remote 解析 github org/repo
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    REMOTE_URL=$(git config --get remote.origin.url || true)
    # 支持 git@github.com:org/repo.git 或 https://github.com/org/repo.git
    if [[ "$REMOTE_URL" =~ github.com[:/]+([^/]+)/([^/.]+) ]]; then
      ORG="${BASH_REMATCH[1]}"; REPO="${BASH_REMATCH[2]}"
      NS="ghcr.io/${ORG}/${REPO}"
    fi
  fi
fi

if [[ -z "$NS" ]]; then
  err "无法自动解析 GHCR 命名空间，请使用 --ns ghcr.io/ORG/REPO 指定"
  exit 2
fi

log "GHCR 命名空间: $NS"
log "镜像标签: $TAG"

# 预拉取镜像（便于尽早暴露认证或权限问题）
for IMG in "${NS}/dagster:${TAG}" "${NS}/user-code:${TAG}"; do
  log "拉取镜像: ghcr.io/${IMG#ghcr.io/}"
  if ! podman pull "$IMG"; then
    err "拉取失败: $IMG\n请确认已执行: podman login ghcr.io (并具备 read:packages 权限)"
    exit 3
  fi
done

# 生成 env 文件，覆盖 compose 中的镜像变量
cat >"${ENV_FILE}" <<EOF
# 由 deploy_podman.sh 生成/更新，用于覆盖 compose 镜像
USER_CODE_IMAGE=${NS}/user-code:${TAG}
DAGSTER_IMAGE=${NS}/dagster:${TAG}
# 可按需调整以下端口与可选变量
POSTGRES_PORT=5432
DAGSTER_WEBSERVER_PORT=3000
MLFLOW_PORT=5000
QDRANT_PORT=6333
LANGFLOW_PORT=7860
# 可选：如启用鉴权，提供 LangFlow API Key
# LANGFLOW_API_KEY=
EOF

log "已生成 env 文件: ${ENV_FILE}"

# 启动编排
log "启动服务 (compose up -d)"
"${COMPOSE_CMD[@]}" --env-file "$ENV_FILE" -f docker-compose.yml up -d

log "容器列表:"
podman ps --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}'

log "部署完成。访问 Dagster Web UI: http://<服务器IP>:\n  端口: $(grep -E '^DAGSTER_WEBSERVER_PORT=' "$ENV_FILE" | cut -d= -f2) (默认 3000)\n也可进入容器触发 Job 示例:"
cat <<'EOCMD'
# 获取 user_code 容器 ID
UCID=$(podman ps --filter name=user_code --format '{{.ID}}' | head -n1)
# 列出作业
podman exec -it "$UCID" bash -lc 'dagster job list -m dagma.definitions'
# 触发示例作业
podman exec -it "$UCID" bash -lc 'dagster job launch -j run_llm_rag_job -m dagma.definitions'
podman exec -it "$UCID" bash -lc 'dagster job launch -j run_models_train_job -m dagma.definitions'
# 查看最近运行
podman exec -it "$UCID" bash -lc 'dagster run list -n 10'
EOCMD
