# M2 容器化与一键环境（docker/compose）设计与落地方案

本方案在不改变现有 Python 代码逻辑的前提下，交付一套符合 Dagster 最佳实践、可按需扩展的本地容器编排与一键启动方式。目标是将 M1 的最小可运行骨架放入标准的“Webserver + Daemon + User Code + Postgres”的部署拓扑，同时并行提供 MLflow、Qdrant，便于后续 M3/M4 扩展。

—

## 1. 架构与服务拓扑

核心服务（最小集）：
- Postgres（5432）：Dagster 实例存储（runs、event logs、schedules 等）与 MLflow backend store
- Dagster User Code（gRPC，4000）：承载代码位置（code location），对外暴露 gRPC 服务，供 Webserver 加载
- Dagster Webserver（3000）：加载 workspace.yaml 指向的 user-code gRPC，负责 UI 与提交运行
- Dagster Daemon：出队执行（QueuedRunCoordinator）、调度/传感器

配套服务：
- MLflow（5000）：实验追踪（Tracking UI）；backend 指向 Postgres，artifact 先落本地卷，后续可切 MinIO
- Qdrant（6333）：向量数据库，供 M4 示例使用（可先占位）

可选服务：
- MinIO（9000/9001）：MLflow 的 artifact store（可选）
- ClickHouse（8123）：可选分析引擎（Backlog 中已列）

—

## 2. 关键文件与目录（规划）

- docker/
  - base/Dockerfile：Python 基础镜像与通用系统依赖
  - dev/Dockerfile：开发镜像（可选，便于本地调试/热重载）
  - prod/Dockerfile：生产镜像（多阶段构建、最小化）
  - Dockerfile_user_code：User Code 容器镜像（暴露 4000 gRPC）
  - Dockerfile_dagster：Webserver/Daemon 共用基础镜像（安装 dagster-webserver、dagster-postgres）
- docker-compose.yml：编排 Postgres、MLflow、Qdrant、Dagster 三件套（user-code/webserver/daemon）
- .env.example：集中环境变量（POSTGRES_*、MLFLOW_*、QDRANT_*、DAGSTER_HOME、DAGSTER_CURRENT_IMAGE 等）
- scripts/start_env.sh：一键分组启动 minimal/data/vector/ml/full（仅在 M2 中提供实现草案）
- workspace.yaml（容器内使用版本）：webserver 侧指向 user-code gRPC
- dagster.yaml（容器内使用版本）：启用 dagster-postgres（实例存储），读取 env 定义的连接项

说明：仓库根部已有的 <mcfile name="workspace.yaml" path="/home/dell/Projects/Dagma/workspace.yaml"></mcfile> 与 <mcfile name="dagster.yaml" path="/home/dell/Projects/Dagma/dagster.yaml"></mcfile> 面向本地开发；容器镜像中会内置“容器态”的 workspace.yaml/dagster.yaml，以免与本地冲突。

—

## 3. docker-compose.yml（最小工作示例草案）

以下为最小可用编排草案，后续按需细化 healthcheck、资源限制与日志策略（不在本次强行铺满，避免过度设计）。

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-dagster}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 8s
      retries: 5

  user_code:
    build:
      context: .
      dockerfile: ./docker/Dockerfile_user_code
    image: ${USER_CODE_IMAGE:-dagma/user-code:dev}
    environment:
      DAGSTER_HOME: /opt/dagster/dagster_home
      DAGSTER_CURRENT_IMAGE: ${USER_CODE_IMAGE:-dagma/user-code:dev}
      DAGSTER_POSTGRES_USER: ${POSTGRES_USER:-postgres}
      DAGSTER_POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      DAGSTER_POSTGRES_DB: ${POSTGRES_DB:-dagster}
      DAGSTER_POSTGRES_HOST: postgres
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - dagma

  webserver:
    build:
      context: .
      dockerfile: ./docker/Dockerfile_dagster
    command: ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "/opt/dagster/workspace.yaml"]
    ports:
      - "${DAGSTER_WEBSERVER_PORT:-3000}:3000"
    environment:
      DAGSTER_HOME: /opt/dagster/dagster_home
      DAGSTER_POSTGRES_USER: ${POSTGRES_USER:-postgres}
      DAGSTER_POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      DAGSTER_POSTGRES_DB: ${POSTGRES_DB:-dagster}
      DAGSTER_POSTGRES_HOST: postgres
    volumes:
      - dagster_home:/opt/dagster/dagster_home
    depends_on:
      postgres:
        condition: service_healthy
      user_code:
        condition: service_started
    networks:
      - dagma

  daemon:
    build:
      context: .
      dockerfile: ./docker/Dockerfile_dagster
    command: ["dagster-daemon", "run"]
    restart: on-failure
    environment:
      DAGSTER_HOME: /opt/dagster/dagster_home
      DAGSTER_POSTGRES_USER: ${POSTGRES_USER:-postgres}
      DAGSTER_POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      DAGSTER_POSTGRES_DB: ${POSTGRES_DB:-dagster}
      DAGSTER_POSTGRES_HOST: postgres
    volumes:
      - dagster_home:/opt/dagster/dagster_home
    depends_on:
      postgres:
        condition: service_healthy
      user_code:
        condition: service_started
    networks:
      - dagma

  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.16.0
    command: ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "postgresql+psycopg2://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-dagster}", "--default-artifact-root", "/mlruns"]
    environment:
      MLFLOW_TRACKING_URI: http://mlflow:5000
    ports:
      - "${MLFLOW_PORT:-5000}:5000"
    volumes:
      - mlruns:/mlruns
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - dagma

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "${QDRANT_PORT:-6333}:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - dagma

networks:
  dagma:
    driver: bridge

volumes:
  pgdata:
  mlruns:
  qdrant_storage:
  dagster_home:
```

说明：
- user_code 镜像通过 DAGSTER_CURRENT_IMAGE 提示 run launcher 使用同一镜像执行容器化任务；后续如开启容器执行器/launchers，可直接沿用
- webserver/daemon 共用同一基础镜像（Dockerfile_dagster），分别以不同 command 运行，减少镜像数量
- workspace.yaml/dagster.yaml 会以“容器态”版本写入 /opt/dagster/ 路径，并通过 volumes 映射 DAGSTER_HOME，便于持久化

—

## 4. Dockerfile（草案）

docker/Dockerfile_user_code（最小版）：
```dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DAGSTER_HOME=/opt/dagster/dagster_home

RUN pip install --no-cache-dir \
    dagster \
    dagster-postgres

WORKDIR /opt/dagster/app
# 复制项目代码（尽量只复制必要路径，减少构建上下文）
COPY src/ /opt/dagster/app/src/
COPY pyproject.toml /opt/dagster/app/

# 暴露 gRPC 端口
EXPOSE 4000

# 以模块方式启动 gRPC 代码位置（对应仓库入口 src/dagma/definitions.py）
CMD ["dagster", "api", "grpc", "--module-name", "dagma.definitions", "--host", "0.0.0.0", "--port", "4000"]
```

docker/Dockerfile_dagster（最小版）：
```dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DAGSTER_HOME=/opt/dagster/dagster_home

RUN pip install --no-cache-dir \
    dagster \
    dagster-webserver \
    dagster-postgres

# 提供容器态配置（构建阶段可由 COPY 写入模板文件）
WORKDIR /opt/dagster
# 这些文件将由后续提交补充：
# COPY docker/config/dagster.yaml /opt/dagster/dagster.yaml
# COPY docker/config/workspace.yaml /opt/dagster/workspace.yaml

# webserver 映射端口
EXPOSE 3000
```

—

## 5. 容器态配置文件（模板）

workspace.yaml（容器内 /opt/dagster/workspace.yaml）：
```yaml
load_from:
  - grpc_server:
      host: user_code
      port: 4000
```

dagster.yaml（容器内 /opt/dagster/dagster.yaml，示意）：
```yaml
# 由 dagster-postgres 提供实例存储后端；敏感信息读取自环境变量
telemetry:
  enabled: false
instance_class: dagster._core.instance.DagsterInstance
# run_storage / event_log_storage / schedule_storage 推荐采用 dagster-postgres
# 具体 DSN/参数读取环境变量，避免硬编码；在下一次提交中随镜像一并提供模板
```

—

## 6. 环境变量与 .env.example（建议）

建议在仓库根部提供 .env.example，示意如下（不提交真实密钥）：
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=dagster
POSTGRES_PORT=5432

DAGSTER_WEBSERVER_PORT=3000
MLFLOW_PORT=5000
QDRANT_PORT=6333

# 用于 user_code 容器与作业容器的统一镜像标识
USER_CODE_IMAGE=dagma/user-code:dev
```

—

## 7. 一键脚本 scripts/start_env.sh（接口约定）

先定义接口与行为（实现将随后续提交合入，避免一次性做太多）：
- 入口：scripts/start_env.sh [group]
- 支持分组：
  - minimal：postgres + user_code + webserver + daemon
  - data：minimal + mlflow
  - vector：minimal + qdrant
  - ml：minimal + mlflow + qdrant
  - full：minimal + mlflow + qdrant +（可选 minio/clickhouse）
- 行为：
  - 自动加载 .env（若存在），输出最终端口/URL
  - 检测 docker compose 可用性与版本
  - 按分组对 compose services 进行选择性 up -d
  - 提供 logs 聚合与 stop/down 便捷子命令

—

## 7. M2 验收步骤与命令（可直接复制执行）

说明：以下命令以 Podman + Compose 为例（容器名形如 dagma_...）。若你使用 Docker，可将 `podman compose` 替换为 `docker compose`，`podman exec` 替换为 `docker exec`，其余保持不变。

### 7.1 启动/重启编排（如未启动）
```bash
# 在项目根目录执行
podman compose up -d
# 查看容器状态
podman ps --format '{{.Names}}\t{{.Status}}'
```

### 7.2 在 Webserver 容器内通过 GraphQL 查询最近 runs
```bash
podman exec -t dagma_webserver_1 bash -lc 'python - <<"PY"
import json, urllib.request
q = """
query RecentRuns {
  runsOrError(filter: {}, limit: 5) {
    __typename
    ... on Runs {
      results { runId status }
    }
    ... on PythonError { message stack }
  }
}
"""
data = json.dumps({"query": q}).encode("utf-8")
req = urllib.request.Request("http://localhost:3000/graphql", data=data, headers={"Content-Type":"application/json"})
resp = urllib.request.urlopen(req, timeout=15)
print(resp.read().decode())
PY'
```
预期：返回最近的运行（runId 与 status），如 `SUCCESS`。

### 7.3 在 User Code 容器内通过模块入口列出与物化资产
说明：当前 CLI 不使用 `-w`（workspace 文件）参数，请使用模块入口 `-m dagma.definitions`。

- 列出资产：
```bash
podman exec -t dagma_user_code_1 bash -lc 'dagster asset list -m dagma.definitions'
```
- 物化原子资产（raw_numbers、sum_numbers）：
```bash
podman exec -t dagma_user_code_1 bash -lc 'dagster asset materialize --select raw_numbers,sum_numbers -m dagma.definitions'
```
- 物化下游资产（viz_ready_data，会自动消费 sum_numbers）：
```bash
podman exec -t dagma_user_code_1 bash -lc 'dagster asset materialize --select viz_ready_data -m dagma.definitions'
```
预期：CLI 输出显示步骤成功（STEP_SUCCESS / RUN_SUCCESS），并将 IOManager 的产物写入容器内的 `$DAGSTER_HOME/storage/` 目录。

### 7.4 在 Postgres 容器内直接查询 runs 表确认入库
```bash
podman exec -t dagma_postgres_1 bash -lc "psql -U postgres -d dagster -c 'SELECT run_id, status, create_timestamp, update_timestamp FROM runs ORDER BY create_timestamp DESC LIMIT 5;'"
```
预期：能看到最近的 run 记录，`status` 为 `SUCCESS`。

> 可选：你也可以进一步查看 event_logs 表的结构并按 run_id 计数事件（不同版本字段名可能略有差异，先查看表结构再决定要查的列）：
```bash
podman exec -t dagma_postgres_1 bash -lc "psql -U postgres -d dagster -c '\\d event_logs'"
# 示例：按 run_id 计数
podman exec -t dagma_postgres_1 bash -lc "psql -U postgres -d dagster -c \"SELECT run_id, COUNT(*) AS events FROM event_logs GROUP BY run_id ORDER BY events DESC LIMIT 5;\""
```

### 7.5（可选）检查实例配置是否正确挂载到容器
```bash
# 查看 user_code 容器的实例目录与配置
podman exec -t dagma_user_code_1 bash -lc 'echo $DAGSTER_HOME; ls -la $DAGSTER_HOME; [ -f $DAGSTER_HOME/dagster.yaml ] && sed -n "1,200p" $DAGSTER_HOME/dagster.yaml || true'

# 查看 webserver/daemon 的实例目录
podman exec -t dagma_webserver_1 bash -lc 'echo $DAGSTER_HOME; ls -la $DAGSTER_HOME'
podman exec -t dagma_daemon_1   bash -lc 'echo $DAGSTER_HOME; ls -la $DAGSTER_HOME'
```

—

### 常见问题与提示
- 若 `dagster asset list` 或 `asset materialize` 报 `No such option: -w`，说明该 CLI 版本不支持 workspace 参数，请改用 `-m dagma.definitions`。
- 若 Webserver GraphQL 查询返回错误，请先确认容器均已启动、`workspace.yaml` 指向的 gRPC（user_code:4000）连通。
- 若 runs 未入库，请检查各容器的 `DAGSTER_HOME` 是否存在 `dagster.yaml`，以及 `dagster-postgres` 是否已安装，并确认连接的 Postgres 正常服务。


## 8. 清理与一致性检查（避免跨环境踩坑复现）
- 移除根级重复/占位配置：dagster.yaml、workspace.yaml 已删除，统一使用 docker/config/*.yaml（容器态生效）。
- 锁文件策略：不跟踪 uv.lock，确保各环境按 pyproject.toml 解析依赖，避免锁版本在不同平台/CPU 架构下冲突。
- README 更新：已移除根级 dagster.yaml/workspace.yaml 的目标结构展示，新增 docker/config 说明与 dev_web.sh 使用指引。
- 代理与 NO_PROXY：compose 中 webserver/daemon 显式清空 HTTP(S)_PROXY 并设置 NO_PROXY 指向 user_code/postgres 等内部主机名，避免 gRPC 与数据库走代理失败。
- .gitignore 校验：包含 .venv、工具缓存、Dagster 运行目录等；如需启用 .env 文件，请根据安全策略调整。
- 一致性校验命令：
  - grep -R "workspace.yaml\|dagster.yaml" . 确认无遗留引用
  - bash scripts/dev_check.sh 运行质量基线
  - docker compose config 验证最终合成配置
