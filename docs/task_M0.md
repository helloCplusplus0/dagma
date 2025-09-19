# Dagma M0（Project Bootstrap）方案A实施说明

版本：v1.0
作者：Dagma 项目
日期：2025-09-18

目标
- 建立可复制、可持续迭代的最小工程基线（质量与一致性优先）。
- 为后续 M1 Dagster 骨架与 M2/M3 业务资产迭代提供稳定的依赖、工具链与目录结构。
- 全面对齐 Dagster 官方最佳实践的项目布局与本仓库既定结构（见 README 与规划）。

范围（In scope）
- 依赖与环境管理选型与落地（方案A：轻量）。
- 基础工程规范与工具（代码风格、静态检查、类型检查、单元测试、提交钩子）。
- 基础项目结构与必要占位（docs/、配置模板、忽略规则、许可证模板）。

不包含（Out of scope）
- Dagster definitions/assets/resources 的具体实现（放到 M1）。
- 容器化/CI/CD 生产化流水线（后续里程碑逐步完善）。

一、关键决策（方案A：轻量）
1) 依赖管理与环境
- 选型：uv（优先）
  - 理由：解析与安装速度快、生成可重现的锁文件、与 pyproject.toml 原生集成、易于在本地与CI复用。
  - 备选：pip + venv（若团队对 uv 不熟悉，可用 pip-tools/requirements.txt 流程作为兜底）。
- Python 版本：3.11（上限 <3.13），兼顾 Ubuntu 24 默认环境的可用性与主流库兼容性。

2) 项目结构（与 Dagster 标准保持一致）
- 采用既定结构（节选）：
  - src/dagma/definitions.py 为 Dagster 入口；src/dagma/defs/ 下按模块拆分 assets/resources/partitions。
  - 根目录包含 pyproject.toml、workspace.yaml、dagster.yaml（M1 添加内容）、tests/、docs/ 等。

3) 基础工程规范
- 格式化与静态检查：ruff（同时承担格式化和lint，降低依赖复杂度）。
- 类型检查：mypy（逐步收紧，先从宽松配置开始）。
- 单元测试：pytest + pytest-cov。
- 提交钩子：pre-commit（统一本地与CI质量门槛）。
- 许可证：MIT（可在后续变更为企业策略要求的许可证）。

二、文件与配置（将于实施阶段创建/更新）
A) pyproject.toml（核心片段，示例草案）
- 基本信息
  - [project] name = "dagma" version = "0.1.0"
  - requires-python = ">=3.11,<3.13"
- 运行时依赖（初期最小集）：
  - dagster、dagster-webserver
- 开发依赖（可作为可选/extra 或 [tool.uv] dev-dependencies）：
  - ruff、mypy、pytest、pytest-cov、pre-commit、types-requests（可选）
- Dagster 加载配置（便于 `dagster dev` 直接识别）：
  - [tool.dagster] module_name = "dagma.definitions"  code_location_name = "dagma"

B) pre-commit 配置（.pre-commit-config.yaml，最小但实用）
- ruff（lint + format）
- mypy（类型检查，可设置为仅对 src/ 生效）
- end-of-file-fixer、trailing-whitespace（通用质量钩子）
- optional：check-merge-conflict、detect-private-key、check-yaml

C) .gitignore（重点条目）
- Python/构建：__pycache__/、*.pyc、*.pyo、build/、dist/、*.egg-info
- 虚拟环境与锁：.venv/、.env、uv.lock
- 工具缓存：.pytest_cache/、.mypy_cache/、.ruff_cache/
- IDE：.idea/、.vscode/
- 系统：.DS_Store
- Dagster 运行工件（如有）：.dagster/ 或本地实例存储目录（若定义）

D) LICENSE
- MIT 模板，版权年份与主体按仓库实际信息填写。

E) docs/
- 当前文档：docs/task_M0.md（本文件）。
- 后续将补充 docs/architecture、docs/guides、docs/api 的占位与导航。

三、命令与执行指南（Ubuntu 24，方案A）
1) 安装 uv（一次性）
- 参考官方安装脚本或通过包管理器安装；安装后确认 `uv --version`。

2) 同步依赖
- 初始化/更新 pyproject.toml 后执行：
  - uv sync  （创建/更新虚拟环境并安装依赖）
  - uv run python -V  （验证 Python 版本）

3) 添加依赖（示例）
- 运行时：uv add dagster dagster-webserver
- 开发时：uv add --dev ruff mypy pytest pytest-cov pre-commit

4) 安装与启用提交钩子
- uv run pre-commit install
- uv run pre-commit run --all-files

5) 基线验证
- 格式化/静态检查：uv run ruff check . && uv run ruff format --check
- 类型检查（可宽松）：uv run mypy src  （首次可允许部分忽略）
- 单元测试：uv run pytest -q

四、与 Dagster 的对齐要点（为 M1 做准备）
- definitions.py 作为统一入口；资产与资源在 src/dagma/defs/* 按模块拆分，避免巨石文件。
- 在 pyproject.toml 配置 [tool.dagster]，使 `dagster dev` 自动发现代码位置（M1 生效）。
- workspace.yaml 与 dagster.yaml 在 M1 提交最小可运行版本（本阶段仅占位/规划）。
- 测试策略：对 assets/resources 的纯函数逻辑优先做单测；对 IO/外部系统引入 fixture 与 mock。

五、质量门槛（M0 完成判定）
- 工程化基线就绪：
  - 存在并通过 uv sync 的 pyproject.toml 与 uv.lock。
  - pre-commit 安装成功，`pre-commit run --all-files` 无阻塞错误。
  - ruff/mypy/pytest 在空或最小样例下跑通（测试可暂为空集合）。
  - .gitignore、LICENSE 与 docs/ 结构到位。
- 未引入与业务强绑定的实现代码；M1 可在此基线上无缝扩展。

六、后续步骤（进入 M1 前的具体改动清单）
- 在仓库根创建/更新以下文件：
  - pyproject.toml（按本文档示例落地）
  - .pre-commit-config.yaml（最小配置）
  - .gitignore（按上述条目）
  - LICENSE（MIT 模板）
- 初始化依赖与钩子：uv sync；uv add 运行时与开发依赖；pre-commit install
- 预留空目录与文件：
  - src/dagma/__init__.py、src/dagma/definitions.py（空实现或占位注释）
  - src/dagma/defs/__init__.py 及子模块目录结构
  - tests/__init__.py
- 验收基线：执行“基线验证”命令全部通过。

七、风险与应对
- Python 版本兼容：优先 3.11；若团队统一到 3.12，需确保 Dagster 与相关库完全兼容后再升级。
- 工具链学习曲线：为 uv 与 ruff 提供团队速查与统一命令别名（Makefile/脚本在后续添加）。
- 依赖收敛：保持最小依赖，避免在 M0 阶段引入数据栈重型依赖（如 dbt/ML 等）以降低波动。

结论
- 本方案以“最小可行 + 可持续演进”为核心，优先交付稳定工程基线。
- 通过 uv + ruff + mypy + pytest + pre-commit 的组合，确保质量门槛与开发效率；为 M1 Dagster 最小骨架搭建与运行奠定基础。
