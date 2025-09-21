#!/usr/bin/env bash
set -euo pipefail

# scripts/smoke.sh
# 轻量端到端冒烟检查：
# 1) 启动 compose（核心服务）
# 2) 轮询所有容器健康状态直至 healthy 或超时
# 3) 通过 MLflow API 创建实验并搜索
# 4) 在 Postgres 中校验 mlflow schema 的关键表是否存在
# 5) 输出报告；任一步失败则以非零码退出

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

INFO() { echo -e "[INFO] $*"; }
WARN() { echo -e "[WARN] $*"; }
ERR()  { echo -e "[ERR]  $*"; }

COMPOSE="docker compose"
# podman-docker 兼容层同样支持该命令

# 仅针对冒烟所需的核心服务（不包含 qdrant/langflow）
SERVICES=(postgres mlflow user_code webserver daemon)

INFO "启动核心服务（分两步以忽略 user_code 的依赖）：postgres mlflow"
$COMPOSE up -d postgres mlflow

INFO "启动 user_code / webserver / daemon（--no-deps，避免拉起 qdrant/langflow）"
for s in user_code webserver daemon; do
  $COMPOSE up -d --no-deps "$s"
done

# 健康检查轮询
TIMEOUT=120
INTERVAL=3
ELAPSED=0
HEALTHY=0

check_all_healthy() {
  local ok=1
  for s in "${SERVICES[@]}"; do
    local id status
    id=$($COMPOSE ps -q "$s")
    status=$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null || echo unknown)
    if [[ "$status" != "healthy" ]]; then ok=0; fi
  done
  echo $ok
}

INFO "轮询容器健康状态（最长 ${TIMEOUT}s，每 ${INTERVAL}s 一次）"
while [[ $ELAPSED -lt $TIMEOUT ]]; do
  if [[ $(check_all_healthy) -eq 1 ]]; then HEALTHY=1; break; fi
  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED+INTERVAL))
  echo -n "."
done
[[ $HEALTHY -eq 1 ]] || { echo; ERR "容器未全部变为 healthy，超时 ${TIMEOUT}s"; $COMPOSE ps; exit 10; }
echo
INFO "全部容器 healthy"

# MLflow API 验证
MLFLOW_URL=${MLFLOW_URL:-http://localhost:${MLFLOW_PORT:-5000}}
INFO "调用 MLflow API: $MLFLOW_URL"
set +e
create=$(curl -sS -X POST "$MLFLOW_URL/api/2.0/mlflow/experiments/create" \
  -H 'Content-Type: application/json' \
  --data '{"name":"smoke-'"$(date +%s)"'"}' -w '\n%{http_code}')
set -e
create_code=${create##*$'\n'}
create_body=${create%$'\n'*}
if [[ "$create_code" != "200" ]]; then
  ERR "创建实验失败 HTTP $create_code: $create_body"
  exit 20
fi
exp_id=$(echo "$create_body" | python -c 'import sys,json;print(json.load(sys.stdin).get("experiment_id",""))')
[[ -n "$exp_id" ]] || { ERR "未解析到 experiment_id"; exit 21; }
INFO "创建实验成功 id=$exp_id"

# search 验证
set +e
search=$(curl -sS -X POST "$MLFLOW_URL/api/2.0/mlflow/experiments/search" -H 'Content-Type: application/json' --data '{"max_results":5}' -w '\n%{http_code}')
set -e
search_code=${search##*$'\n'}
search_body=${search%$'\n'*}
if [[ "$search_code" != "200" ]]; then
  ERR "搜索实验失败 HTTP $search_code: $search_body"
  exit 22
fi
INFO "搜索实验成功，返回长度 $(echo -n "$search_body" | wc -c) 字节"

# Postgres 校验 mlflow schema 表
PG_HOST=localhost
PG_PORT=${POSTGRES_PORT:-5432}
PG_DB=${POSTGRES_DB:-dagster}
PG_USER=${POSTGRES_USER:-postgres}
PG_PASS=${POSTGRES_PASSWORD:-postgres}
export PGPASSWORD="$PG_PASS"
INFO "校验 Postgres(${PG_HOST}:${PG_PORT}/${PG_DB}) 的 mlflow schema 表是否存在"

run_psql() {
  if command -v psql >/dev/null 2>&1; then
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 "$@"
  else
    local cid
    cid=$($COMPOSE ps -q postgres)
    docker exec -e PGPASSWORD="$PG_PASS" "$cid" psql -h 127.0.0.1 -p 5432 -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 "$@"
  fi
}

run_psql <<'SQL'
\pset format unaligned
\t on
SELECT 'mlflow.experiments' AS tbl WHERE EXISTS (
  SELECT 1 FROM information_schema.tables WHERE table_schema='mlflow' AND table_name='experiments'
);
SELECT 'mlflow.runs' AS tbl WHERE EXISTS (
  SELECT 1 FROM information_schema.tables WHERE table_schema='mlflow' AND table_name='runs'
);
SQL

INFO "冒烟检查通过"
exit 0
