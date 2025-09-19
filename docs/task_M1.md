# M1 最小可运行骨架（Dagster-first）设计与落地

本阶段目标：在不引入重量依赖与复杂业务的前提下，交付一套可被 `dagster dev` 正确加载、具备最小资产图与资源注入示例的项目骨架，并配套最小单测与本地开发脚本。

## 关键设计
- 入口：通过 `pyproject.toml` 的 `[tool.dagster]` 指定 `module_name = "dagma.definitions"`，无需显式 `workspace.yaml` 亦可被 `dagster dev` 自动发现。
- 结构：按功能域拆分 `src/dagma/defs/{core,data,models,llm,viz}`，在 <mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile> 汇聚注册。
- 资产：
  - data：`raw_numbers` → `sum_numbers`，演示资产依赖与返回值传递。
  - models：`train_model_stub` 使用 `MlflowStubResource` 记录参数/指标，体现资源注入。
  - llm/viz：占位资产，避免过度设计。
- 资源：
  - core：`BasePathResource` 管理本地路径（创建/解析）。
  - models：`MlflowStubResource` 仅内存记录日志，便于单测与后续替换为真实 MLflow 客户端。
  - llm/viz：轻量占位资源，后续阶段再替换为真实实现。
- 单测：
  - `tests/test_assets.py` 覆盖资产物化与资源覆盖注入。
  - `tests/test_resources.py` 覆盖资源的配置与最小行为。
- 脚本：`scripts/dev_check.sh` 一键执行格式化、静态检查、类型检查与测试。

## 目录结构（新增与关键文件）
- <mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile>
- <mcfolder name="core" path="/home/dell/Projects/Dagma/src/dagma/defs/core/"></mcfolder>
  - <mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/core/resources.py"></mcfile>
- <mcfolder name="data" path="/home/dell/Projects/Dagma/src/dagma/defs/data/"></mcfolder>
  - <mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/data/assets.py"></mcfile>
  - <mcfile name="partitions.py" path="/home/dell/Projects/Dagma/src/dagma/defs/data/partitions.py"></mcfile>
- <mcfolder name="models" path="/home/dell/Projects/Dagma/src/dagma/defs/models/"></mcfolder>
  - <mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/models/resources.py"></mcfile>
  - <mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/models/assets.py"></mcfile>
- <mcfolder name="llm" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/"></mcfolder>
  - <mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/resources.py"></mcfile>
  - <mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py"></mcfile>
- <mcfolder name="viz" path="/home/dell/Projects/Dagma/src/dagma/defs/viz/"></mcfolder>
  - <mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/viz/resources.py"></mcfile>
  - <mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/viz/assets.py"></mcfile>
- <mcfile name="test_assets.py" path="/home/dell/Projects/Dagma/tests/test_assets.py"></mcfile>
- <mcfile name="test_resources.py" path="/home/dell/Projects/Dagma/tests/test_resources.py"></mcfile>
- <mcfile name="dev_check.sh" path="/home/dell/Projects/Dagma/scripts/dev_check.sh"></mcfile>

## 本地运行与验收
- 依赖安装（已在 M0 完成，可复用）：
  - `uv sync --all-extras --dev`
- 启动 Dagster Web：
  - `uv run dagster dev`（自动加载 <mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile>）
  - 浏览器访问本地 Web UI，能看到 `data`、`models`、`llm`、`viz` 中的最小资产图
  - 注意：若在预览/代理环境下遇到 `0.0.0.0` 白屏，请改用 `http://localhost:3333/` 或 `http://127.0.0.1:3333/` 访问；或使用命令 `uv run dagster dev -m dagma.definitions --host 127.0.0.1` 明确绑定本地回环地址
  - 也可执行脚本 <mcfile name="dev_web.sh" path="/home/dell/Projects/Dagma/scripts/dev_web.sh"></mcfile> 以固定 `127.0.0.1` 启动：`bash scripts/dev_web.sh [PORT]`
  - 需要在启动前串行运行质量检查时，可使用：`bash scripts/dev_web.sh --check [PORT]`
- 运行质量检查：
  - `bash scripts/dev_check.sh`
- 运行单测：
  - `uv run pytest -q`

## 取舍与边界
- 严格避免引入重量依赖（MLflow、pandas 等），以 stub/原生类型完成演示。
- 分区 `partitions.py` 先提供占位定义，不强制加入资产，降低测试复杂度。
- 资源命名与资产入参一一对应，符合 Dagster 资源注入约定。

## 后续阶段衔接建议
- M2：容器化并接入 Postgres/MLflow/Qdrant 服务组，替换 stub 为真实客户端。
- M3：CI 工作流（lint → type-check → tests），提升覆盖率与质量门槛。
- M4：补充端到端示例与文档（数据→模型→向量→可视化）。
