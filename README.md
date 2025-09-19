# Dagma - 统一数据科学工作流平台

Dagma 是一个面向个人与小型生产实践的统一数据科学工作流平台蓝图，核心以 Dagster 为编排中心，聚合实验追踪、向量检索、数据分析与可视化等能力，目标是提供从数据到模型到应用的一站式体验。

## 项目状态
- 当前仓库处于“规划与设计”阶段，尚未合入可运行代码与容器脚本；本 README 以“可落地蓝图 + 路线图”的形式给出清晰的实现路径。
- 我们将按 Dagster 最佳实践落地标准项目结构与配置（definitions.py、workspace.yaml、dagster.yaml、资产/资源/分区等），并提供最小可运行骨架与 Docker/Compose 支持。

## 核心能力与默认选型（可扩展）
- 工作流编排：Dagster（资产导向、可配置资源、分区/调度/传感器）
- 实验追踪：MLflow（Backend：PostgreSQL，Artifact：MinIO/本地卷）
- 向量检索：Qdrant（轻量易用）
- 数据存储与分析：PostgreSQL（默认）；ClickHouse（可选增强，适合重分析负载）
- LLM/Agent：LangChain（代码式主路径）+ LangFlow（可视化辅助）
- 可视化：Streamlit（默认，快速应用）/ Plotly Dash（可选，高度定制）/ Superset（可选，BI 仪表板）
- 可观测性（可选）：OpenTelemetry + Prometheus + Grafana（指标）+ Loki（日志）

备注：原描述中的“ploty dash”已更正为“Plotly Dash”。

## 快速开始（当前阶段）
当前仓库尚未包含可运行代码与脚本，建议按以下路线推进：
1) 最小可运行骨架：Dagster + PostgreSQL + MLflow（Postgres + 本地/MinIO）+ Qdrant。
2) 容器化与脚本：提供 docker-compose.yml 与 scripts/start_env.sh，分组启动 minimal/dagster/data/vector/ml/full。
3) 工程化：pyproject.toml、pre-commit（ruff/black/mypy）、GitHub Actions、pytest 基础测试（含 stub 资源）。
4) 可选增强：按需启用 ClickHouse、Superset、Prom+Grafana+Loki、Traefik（网关）。

备注：
- 容器化配置位于 docker/config（dagster.yaml、workspace.yaml），根目录不再保留同名文件，避免混淆。
- 本地开发建议使用脚本 scripts/dev_web.sh 固定以 127.0.0.1 绑定启动 Dagster Web，避免某些预览/代理环境下 0.0.0.0 导致的白屏问题：
  - 直接启动：bash scripts/dev_web.sh [PORT]
  - 启动前质量检查：bash scripts/dev_web.sh --check [PORT]
如需我先提交哪套骨架，请在 Issue 中选择：
- 方案 A（轻量）：不启用 ClickHouse，默认 Streamlit；
- 方案 B（标准小型生产）：加入 ClickHouse、Superset、Prom+Grafana。

## 计划服务与端口（合入容器后生效）
- Dagster UI: 3000
- MLflow UI: 5000
- Qdrant API: 6333
- ClickHouse HTTP: 8123（可选）
- PostgreSQL: 5432
- MinIO: 9000（S3）/ 9001（Console）

## 目标项目结构（Dagster 最佳实践）
```
dagma/
├── .github/
│   └── workflows/
├── docs/
├── src/
│   └── dagma/
│       ├── __init__.py
│       ├── definitions.py
│       └── defs/
│           ├── __init__.py
│           ├── core/
│           ├── data/
│           │   ├── assets.py
│           │   ├── resources.py
│           │   └── partitions.py
│           ├── models/
│           ├── llm/
│           └── viz/
├── tests/
├── docker/
├── scripts/
├── .pre-commit-config.yaml
├── pyproject.toml
└── README.md
```
说明：为“目标结构”，将分阶段合入，以确保 README 与仓库保持一致。

## 环境变量（计划提供 .env.example）
- POSTGRES_*：PostgreSQL 连接配置
- MLFLOW_TRACKING_URI、MLFLOW_EXPERIMENT_NAME：MLflow 配置
- QDRANT_*：Qdrant 连接配置
- CLICKHOUSE_*：ClickHouse（可选）
- MINIO_*：对象存储（可选）
- DAGSTER_HOME：Dagster 实例目录

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
