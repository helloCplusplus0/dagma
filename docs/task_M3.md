# M3. 工程化与 CI/CD 方案（落地版）

本方案聚焦“质量基线 + 持续集成 + 提交与分支规范”的最小可行集合，严格贴合当前仓库现状，避免过度设计，可立即运行与演进。

---

## 1) 质量基线（Lint/Typing/Tests）

- 语言与运行时
  - Python: 3.11（与 `pyproject.toml`、`mypy` 配置一致）
- 依赖与工具
  - 依赖声明：`pyproject.toml`
  - 工具：`ruff`（格式化与静态检查）、`mypy`（类型检查）、`pytest`（单测）、`pre-commit`（本地钩子）
- 统一规则（已在仓库配置中定义，无需重复配置）
  - `ruff`: 行宽 100，规则集 E/F/I/UP/B
  - `mypy`: Python 3.11、忽略第三方缺失类型、`src` 为源路径
  - `pytest`: `tests/` 目录，`-q -ra` 轻量输出

本地一键检查（不修改文件）：

- 使用 uv（推荐）
  - 安装依赖：`uv run ruff --version` 将触发首次解析；或执行 `uv sync --group dev`
  - 质量检查：
    - 格式检查：`uv run ruff format --check`
    - 规则检查：`uv run ruff check .`
    - 类型检查：`uv run mypy src`
    - 单元测试：`uv run pytest -q`

- 使用已有脚本（会直接格式化文件）：
  - `bash scripts/dev_check.sh`

Pre-commit（本地开发者建议启用）：

- 一次性安装：`uv run pre-commit install`
- 手动全量执行：`uv run pre-commit run --all-files`

---

## 2) CI 工作流（GitHub Actions）

目标：在 PR 与主干推送时自动执行格式校验、静态检查、类型检查与单测。尽可能利用现成 Action 与 uv 缓存，减少实现与维护负担。

- 触发条件
  - `pull_request`：所有分支到 `main` 的 PR
  - `push`：`main` 与 `feature/*`
- 核心步骤
  1) `actions/checkout` 拉取源码
  2) `astral-sh/setup-uv` 安装 uv，指定 `python-version: 3.11` 与缓存
  3) 运行 `ruff format --check`、`ruff check`、`mypy`、`pytest`
- 并发与稳定性
  - 使用 `concurrency` 取消过期的同分支运行，节约资源

工作流文件：`.github/workflows/ci.yml`（已由本任务创建）

---

## 3) 容器构建健检（非发布，仅构建验证）

目标：在 Dockerfile 或 compose 变更时，验证两类镜像能成功构建（`docker/Dockerfile_dagster` 与 `docker/Dockerfile_user_code`）。不推送、不发布，仅做健检与缓存以加速复跑。

- 触发条件
  - `pull_request`：`docker/**`、`docker-compose.yml`
  - `workflow_dispatch`：手动触发
- 核心步骤
  1) `actions/checkout`
  2) `docker/setup-buildx-action` + `docker/build-push-action`
  3) `cache-from/to: type=gha` 使用 GitHub Actions 缓存
- 平台：`linux/amd64`（与默认 runner 一致）

工作流文件：`.github/workflows/docker-build.yml`（已由本任务创建）

---

## 4) 提交规范与分支策略

- 提交规范（Conventional Commits 最小子集）
  - 类型：`feat`、`fix`、`docs`、`ci`、`refactor`、`test`、`chore`
  - 示例：`feat(core): add asset for dataset partition`
  - 重大变更：可在类型后添加 `!` 或在正文 `BREAKING CHANGE:` 说明
- 分支策略（轻量 Trunk-based）
  - 主干：`main`（受保护，必须通过 CI）
  - 功能分支：`feature/<topic>`（从 `main` 切出）
  - 合并方式：PR + `squash and merge`（鼓励小步提交，合并时整洁历史）

---

## 5) 运行与排错指南（CI）

- 失败常见原因
  - `ruff format --check` 未通过：请在本地执行 `uv run ruff format` 修复
  - `mypy` 类型问题：根据报错在 `src/` 补充类型或忽略注解
  - `pytest` 失败：在本地复现并补充测试/修复逻辑
- 重新运行与复现
  - CI 界面点击 `Re-run jobs`
  - 本地使用同版本 Python（3.11）与 `uv run` 执行同名命令

---

## 6) 后续增量（不在本次落地范围，但兼容演进）

- 引入覆盖率阈值与报告归档（`pytest-cov` + `actions/upload-artifact`）
- 变更影响面检测（按改动路径切分 job，进一步节省CI时间）
- 容器安全扫描（Trivy/Snyk），依赖漏洞检测（`pip-audit`/`uv` 安全告警）
- 生产镜像签名与供应链（cosign）与发布流水线（后续 M* 阶段再设计）

---

## 7) 成果清单（本次已落地）

- `.github/workflows/ci.yml`：质量基线自动化
- `.github/workflows/docker-build.yml`：容器构建健检
- 文档：`docs/M3.md`（本文件）
