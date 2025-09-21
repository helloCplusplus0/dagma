# Dagma - 统一数据科学工作流平台

Dagma 是一个面向个人与小型生产实践的统一数据科学工作流平台蓝图，核心以 Dagster 为编排中心，聚合实验追踪、向量检索、数据分析与可视化等能力，目标是提供从数据到模型到应用的一站式体验。

## 项目状态
- 当前仓库已提供可运行代码与容器脚本，支持本地运行与 Docker/Podman 一键启动。
- 项目遵循 Dagster 最佳实践，已包含 definitions.py、docker-compose、容器态配置与基础测试/CI。

## 核心能力与默认选型（可扩展）
- 工作流编排：Dagster（资产导向、可配置资源、分区/调度/传感器）
- 实验追踪：MLflow（Backend：PostgreSQL，Artifact：MinIO/本地卷）
- 向量检索：Qdrant（轻量易用）
- 数据存储与分析：PostgreSQL（默认）；ClickHouse（可选增强，适合重分析负载）
- LLM/Agent：LangChain（代码式主路径）+ LangFlow（可视化辅助）
- 可视化：Streamlit（默认，快速应用）/ Plotly Dash（可选，高度定制）/ Superset（可选，BI 仪表板）
- 可观测性（可选）：OpenTelemetry + Prometheus + Grafana（指标）+ Loki（日志）

备注：原描述中的“ploty dash”已更正为“Plotly Dash”。

## 部署与快速开始
前置要求：
- 安装 Docker（推荐）或 Podman；确保具备 compose 前端（docker compose 或 podman compose）。
- 可选：Python 3.10+ 用于本地运行测试（make test）。

1) 准备环境变量
- cp .env.example .env，根据需要调整端口与开关（如 MLFLOW_USE_TRACKING、LANGFLOW_BASE_URL、QDRANT_HOST 等）。

2) 一键冒烟自检（端到端）
- make smoke
- 该命令将按需拉起 postgres/mlflow/user_code/webserver/daemon，轮询健康状态，并通过 MLflow API、Postgres schema 校验进行验证；成功将输出“冒烟检查通过”。

3) 启动开发环境（最小分组）
- make dev-up            # 启动 postgres + mlflow + dagster(user_code/webserver/daemon)
- 打开 Dagster UI: http://127.0.0.1:${DAGSTER_WEBSERVER_PORT:-3000}
- 打开 MLflow UI:  http://127.0.0.1:${MLFLOW_PORT:-5000}
- 停止并清理：make dev-down
- 需要完整服务（含 Qdrant/LangFlow）时可执行：bash scripts/start_env.sh up full

4) 生产部署建议（最小）
- 直接使用 docker-compose：docker compose up -d  或  bash scripts/start_env.sh up full
- 如在公司/代理环境，按 .env 中 HTTP_PROXY/HTTPS_PROXY/NO_PROXY 设置；脚本会自动重写宿主 127.0.0.1/localhost 到容器网关别名。
- 如需使用私有镜像仓库（如 GHCR），在 .env 中覆盖 DAGSTER_IMAGE/USER_CODE_IMAGE/MLFLOW_IMAGE。

5) CI 状态
- GitHub Actions 已接入单元测试与 smoke 端到端校验；推送分支或 PR 将自动执行。

## 计划服务与端口（合入容器后生效）
- Dagster UI: 3000
- MLflow UI: 5000
- Qdrant API: 6333
- ClickHouse HTTP: 8123（可选）
- PostgreSQL: 5432
- MinIO: 9000（S3）/ 9001（Console）

## 项目目录结构
```
.
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── docker-build.yml
├── docker/
│   └── config/
│       ├── dagster.yaml
│       └── workspace.yaml
├── scripts/
│   ├── start_env.sh
│   └── smoke.sh
├── src/
│   └── dagma/
│       ├── __init__.py
│       ├── definitions.py
│       └── defs/
│           ├── core/
│           │   └── resources.py
│           ├── data/
│           │   └── assets.py
│           ├── models/
│           │   ├── assets.py
│           │   └── resources.py
│           ├── llm/
│           │   ├── assets.py
│           │   └── resources.py
│           └── viz/
│               └── assets.py
├── tests/
├── .env.example
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── README.md
```
说明：以上为当前仓库的真实结构；Dagster 入口为 src/dagma/definitions.py（通过 [tool.dagster] 自动发现），容器配置集中在 docker/config 下，脚本位于 scripts。

## 环境变量（.env.example）
建议先复制并按需修改：cp .env.example .env
- Postgres：POSTGRES_USER、POSTGRES_PASSWORD、POSTGRES_DB、POSTGRES_PORT
- Dagster：DAGSTER_WEBSERVER_PORT（DAGSTER_HOME 在容器内固定为 /opt/dagster/dagster_home）
- MLflow：MLFLOW_PORT、MLFLOW_USE_TRACKING、MLFLOW_TRACKING_URI、MLFLOW_EXPERIMENT、MLFLOW_USERNAME_READONLY、MLFLOW_PASSWORD_READONLY
- Qdrant：QDRANT_HOST、QDRANT_PORT、QDRANT_USE_HTTPS、QDRANT_API_KEY、QDRANT_COLLECTION、QDRANT_TIMEOUT
- LangFlow：LANGFLOW_PORT、LANGFLOW_BASE_URL、LANGFLOW_API_KEY、LANGFLOW_DEFAULT_FLOW_ID
- 镜像覆盖（可选）：USER_CODE_IMAGE、DAGSTER_IMAGE、MLFLOW_IMAGE
- 代理（可选）：HTTP_PROXY、HTTPS_PROXY、NO_PROXY（需包含 user_code,postgres,mlflow,qdrant,langflow,localhost,127.0.0.1,::1）

## 技术选型与替代项（基于 dev_tools_fix.md）
- 数据库/分析：默认 PostgreSQL；可选 ClickHouse（高并发分析）、DuckDB/Polars（本地轻量）
- 可视化：默认 Streamlit；可选 Plotly Dash（高度定制）、Superset（BI）
- 消息/流（按需）：Redis Streams（轻量）、Redpanda/Kafka（更强吞吐）
- 服务化（按需）：FastAPI（统一 API）、Traefik（网关/路由）
- 可观测性（按需）：OpenTelemetry + Prometheus/Grafana + Loki

## 路线图与里程碑
- M1：提交最小可运行骨架（definitions.py、workspace.yaml、dagster.yaml、基础资产/资源与测试）
- M2：提交 docker-compose 与 scripts/start_env.sh（分组启动）
- M3：提交工程化配置（pyproject、pre-commit、CI、pytest）
- M4：扩展组件（ClickHouse、Superset、可观测性栈）与端到端示例流程

## 贡献指南
1. Fork 仓库
2. 基于 Issue/里程碑创建分支（`feature/xxx`）
3. 提交更改（遵循 Conventional Commits）
4. 发起 Pull Request（关联 Issue）

## 许可证
MIT

## 使用 Cookbook（可复制运行）
1) 列出可用资产与作业
- dagster asset list
- dagster job list

2) 运行数据资产链
- dagster asset materialize -m dagma.definitions raw_numbers sum_numbers

3) 运行最小 RAG 链（Qdrant REST）
- 确保 qdrant 服务已就绪（make dev-up 或 docker compose up -d）
- dagster asset materialize -m dagma.definitions embed_texts_stub qdrant_upsert qdrant_search

4) 运行最小训练作业（MLflow）
- 本地默认使用 MlflowStubResource；如需真实追踪，将 .env 中 MLFLOW_USE_TRACKING=true 并重启服务
- 然后执行：dagster job launch -m dagma.definitions -j run_models_train_job
- 也可直接 materialize 资产：dagster asset materialize -m dagma.definitions train_model_stub

5) 运行 LangFlow Flow（可选）
- 在 .env 设置 LANGFLOW_BASE_URL 与 LANGFLOW_DEFAULT_FLOW_ID（可选）
- 启动 langflow 服务后，执行：dagster job launch -m dagma.definitions -j run_langflow_job

6) 以 UI 操作
- make dev-up 后，打开 http://127.0.0.1:${DAGSTER_WEBSERVER_PORT:-3000}
- 在“Assets/Jobs/Schedules”中即可可视化触发与查看元数据链接（如 MLflow 与 Qdrant URL）

7) 常见问题排查
- 代理环境下容器间调用失败：确认 .env 中 NO_PROXY 包含 postgres,user_code,webserver,daemon,mlflow,qdrant,langflow,localhost,127.0.0.1,::1
- MLflow UI 无法访问 artifact：确保 MLFLOW_SERVER 使用 --serve-artifacts 且 artifacts-destination 映射到卷（compose 已配置）
- Qdrant 401/SSL 错误：若使用 Qdrant Cloud，请在 .env 设置 QDRANT_API_KEY 与 QDRANT_USE_HTTPS=true
