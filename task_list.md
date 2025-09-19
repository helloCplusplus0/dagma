# Dagma 开发规划表（对齐 README 与 Dagster 最佳实践）

> 目的：将 README 的蓝图拆解为可执行子任务，以最小可运行骨架 → 容器化 → 工程化 → 功能扩展的顺序推进，确保每一步都有交付物与验收标准。

—

## 概览
- 核心组件：Dagster（编排）、MLflow（实验追踪）、Qdrant（向量库）、PostgreSQL（数据库）、LangChain/LangFlow（LLM/Agent）、Streamlit（可视化应用）
- 目标结构：遵循 Dagster 标准项目结构（definitions.py、workspace.yaml、dagster.yaml、assets/resources/partitions、tests），分阶段合入。
- 交付节奏：M1 最小可运行骨架 → M2 docker/compose 与脚本 → M3 工程化与 CI → M4 扩展能力与端到端示例。

—

## 里程碑与子任务

### Y M0. 准备与基础设置（Project bootstrap）
- [ ] 规划依赖与约束
  - [ ] Python 版本范围（建议 3.10+）、本地虚拟环境规范（uv/venv/poetry 二选一，先以 uv/pip 为主）
  - [ ] 基础依赖清单（dagster、dagster-webserver、mlflow、qdrant-client、psycopg、pydantic、pandas、pyyaml、python-dotenv 等）
  - [ ] 开发依赖清单（pytest、pytest-cov、ruff、black、isort、mypy、pre-commit、types-* 补充）
- [ ] 初始化工程元文件
  - [ ] pyproject.toml（应用/库元信息、依赖、工具链配置：ruff/black/mypy/isort/pytest）
  - [ ] .pre-commit-config.yaml（ruff、black、isort、mypy、end-of-file-fixer）
  - [ ] .gitignore（Python、Docker、IDE、Dagster 实例缓存等）
  - [ ] LICENSE（MIT）
- [ ] 基础文档
  - [ ] docs/ 占位与贡献指南草稿
  - [ ] README 增补“如何本地跑 M1 骨架”段落（安装、环境变量、启动命令）

验收标准：本地可安装依赖（pip/uv），pre-commit 可运行，lint 与类型检查通过，无运行代码但工程结构清晰。

—

### Y M1. 最小可运行骨架（Dagster-first）
- [ ] 目录结构与入口
  - [ ] src/dagma/__init__.py
  - [ ] src/dagma/definitions.py（全局 Definitions 入口；汇集 assets、resources、schedules/partitions）
  - [ ] src/dagma/defs/ 包结构：core/、data/、models/、llm/、viz/
  - [ ] dagster.yaml（实例配置，DAGSTER_HOME 指向、logs、storage 策略）
  - [ ] workspace.yaml（代码位置：python_file 指向 src/dagma/definitions.py 或包入口）
- [ ] 资产与资源（最小示例）
  - [ ] data.assets: 一个简单资产（如生成 DataFrame 或写入本地文件）
  - [ ] data.partitions: 简单的 DailyPartitionedConfig 或 StaticPartitionsDefinition（可选）
  - [ ] core.resources: 一个 ConfigurableResource 示例（如简单 KV 或本地路径配置）
  - [ ] models.assets: 演示与 MLflow 的最小交互占位（先用 stub 资源，不真实连接）
  - [ ] llm.assets: 预留占位（不引入重量依赖）
  - [ ] viz.assets: 预留占位（不引入重量依赖）
- [ ] 测试基础（pytest）
  - [ ] tests/test_assets.py：使用 Dagster 的资源覆盖/入参注入，对 data.assets 做最小行为验证
  - [ ] tests/test_resources.py：对 core.resources 的配置/校验逻辑做单测
- [ ] 脚本
  - [ ] scripts/dev_check.sh：一键运行 lint、type-check、pytest

验收标准：
- [ ] `dagster dev` 能够启动 Web（需安装 dagster-webserver）并加载最小资产图
- [ ] pytest 全绿（覆盖最小资产与资源）
- [ ] README 新增“本地运行 Dagster 骨架”说明

—

### Y M2. 容器化与一键环境（docker/compose）
- [ ] docker 目录与镜像分层
  - [ ] docker/base/Dockerfile：基础运行镜像（Python + 系统依赖 + 构建缓存策略）
  - [ ] docker/dev/Dockerfile：开发镜像（热重载/调试工具）
  - [ ] docker/prod/Dockerfile：生产镜像（多阶段构建、最小镜像）
- [ ] docker-compose.yml 与分组启动
  - [ ] 服务：postgres（5432）、mlflow（5000，backend=postgres，artifact=local/MinIO 可切）、qdrant（6333）、dagster-user-code（4000 gRPC）、dagster-webserver（3000）、dagster-daemon
  - [ ] 可选：minio（9000/9001）、clickhouse（8123）
  - [ ] volumes/networks/healthcheck；环境变量来自 .env/.env.example；workspace.yaml 指向 user-code gRPC；为 user-code 注入 DAGSTER_CURRENT_IMAGE
- [ ] scripts/start_env.sh：支持分组启动（minimal / data / vector / ml / full）与日志聚合
- [ ] 环境变量与安全
  - [ ] .env.example（POSTGRES_*、MLFLOW_*、QDRANT_*、MINIO_*、DAGSTER_HOME、DAGSTER_CURRENT_IMAGE 等）
  - [ ] secrets 挂载/引用建议，避免明文提交

验收标准：
- [ ] `docker compose up -d` 后，Dagster Webserver + Daemon + User Code、MLflow、Qdrant、Postgres 可用，端口与数据卷正常
- [ ] MLflow 成功连接 Postgres 作为 backend store，artifact 可落盘（本地或 MinIO）
- [ ] Dagster Webserver 能通过 workspace.yaml 连接到 user-code gRPC，并由 Daemon 负责出队与执行（QueuedRunCoordinator 生效）

—

### M3. 工程化与 CI/CD
- [ ] 质量基线
  - [ ] ruff/black/isort/mypy 配置与通过
  - [ ] pytest + 覆盖率门限（如 80% 起），对关键资源/资产增加单测
- [ ] CI（GitHub Actions）
  - [ ] workflow: lint → type-check → tests → 构建镜像（可选）
  - [ ] 缓存策略：pip/uv、pytest、docker layer
- [ ] 提交规范与分支策略
  - [ ] Conventional Commits、保护主分支、PR 检查与模板

验收标准：PR 自动检查全绿，主分支保持可运行；release 分支可构建镜像。

—

### M4. 扩展能力与端到端示例
- [ ] MLflow 集成
  - [ ] models.resources: MLflow Tracking 客户端资源（从 env 读取 TRACKING_URI/EXPERIMENT）
  - [ ] models.assets: 训练/评估示例资产（记录参数、指标、模型；可先用 sklearn/轻量例子）
  - [ ] 示例：从 Dagster 资产触发一次 MLflow run 并在 UI 可见
- [ ] Qdrant 集成
  - [ ] data/resources 或 models/resources: Qdrant 客户端资源（集合创建、向量写入）
  - [ ] data.assets: 简单向量化与写入（可先用随机向量/占位 encoder），查询演示
- [ ] LLM/Agent
  - [ ] llm.assets: 基于 LangChain 的最小链路（离线 stub/或本地小模型/云端占位），加入流式/结构化输出示例
  - [ ] 可选：LangFlow 无头模式/导入导出示例，与 LangChain 互操作说明
- [ ] 可视化
  - [ ] Streamlit 应用骨架：读取 Postgres/Qdrant 或展示 MLflow 指标，演示 multipage 与缓存
  - [ ] 可选：Plotly Dash/Superset 接入指引
- [ ] 调度/分区/传感器
  - [ ] partitions：日/小时分区示例；schedules：定时；sensors：基于外部事件（可选）
- [ ] 生产化指引（文档）
  - [ ] PostgreSQL（角色/权限、连接池 PgBouncer、备份/恢复）
  - [ ] Qdrant（快照/备份、HNSW/量化配置、payload 索引与副本/分片基础）
  - [ ] Dagster（代码位置与多部署、实例隔离、配置分层 dev/prod）
  - [ ] 安全与合规（最小权限、Secrets 管理、日志与监控）

验收标准：
- [ ] 本地一键启动后可跑通“数据→模型→向量→应用”的端到端最小闭环 Demo
- [ ] 提供操作手册与问题诊断清单（FAQ/Runbook）

—

## 任务分解（按文件/模块）
- [ ] src/dagma/definitions.py：集中注册 assets/resources/partitions/schedules
- [ ] src/dagma/defs/core/resources.py：通用配置型资源（BasePath、Clock、简单 KV）
- [ ] src/dagma/defs/data/assets.py：数据生成/清洗/加载最小资产
- [ ] src/dagma/defs/data/partitions.py：示例分区定义
- [ ] src/dagma/defs/models/resources.py：MLflow Tracking 客户端封装
- [ ] src/dagma/defs/models/assets.py：最小训练/评估并记录到 MLflow
- [ ] src/dagma/defs/llm/resources.py：LangChain/LangFlow 集成入口（占位）
- [ ] src/dagma/defs/llm/assets.py：最小链路/结构化输出示例（占位）
- [ ] src/dagma/defs/viz/resources.py：可视化相关（Streamlit/Plotly Dash）占位
- [ ] src/dagma/defs/viz/assets.py：产出可视化可消费的数据/图表
- [ ] tests/test_assets.py：资产行为测试（含资源覆盖）
- [ ] tests/test_resources.py：资源配置与校验测试
- [ ] dagster.yaml / workspace.yaml：实例与代码位置配置
- [ ] docker/* 与 scripts/*：容器与启动脚本

—

## 环境变量与配置分层
- [ ] .env.example：POSTGRES_*/MLFLOW_*/QDRANT_*/MINIO_*/DAGSTER_HOME 等
- [ ] 本地 dev 与 prod 的差异化配置（端口、日志级别、缓存策略、持久化路径）
- [ ] 机密管理：docker secrets/.env 文件权限、CI 中的 GitHub Secrets

—

## 验收与质量门槛（每阶段通用）
- [ ] 代码风格：ruff/black/isort 一致
- [ ] 类型检查：mypy 通过
- [ ] 测试：pytest 全绿，关键模块有覆盖
- [ ] 文档：README/ docs 指引可复现
- [ ] 安全：不提交明文密钥，敏感配置读取自环境变量

—

## 后续增强（Backlog）
- [ ] ClickHouse 与 Superset 的可选集成
- [ ] 观测性栈（OpenTelemetry + Prometheus + Grafana + Loki）
- [ ] API 层（FastAPI）与统一鉴权（JWT/OIDC）
- [ ] 网关/路由（Traefik）
- [ ] 示例数据集与 Benchmark 脚本
- [ ] 发布流程与版本标记（SemVer/Release Drafter）

—

## 执行建议（短期行动）
1) 完成 M0（依赖与工具链落地），提交初始工程结构与质量基线。
2) 合入 M1 最小 Dagster 骨架与单测，确保 `dagster dev` 正常。
3) 推进 M2 容器化与一键启动，打通最小服务编排。
4) 完成 M3 工程化与 CI，使每个 PR 都可验证质量。
5) 进入 M4 集成与 Demo 闭环，开始撰写用户指南与运维手册。
