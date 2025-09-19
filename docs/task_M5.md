# M5. MLflow 集成（Tracking 最小可用）

一、目标与范围
- 目标：在不引入过度封装的前提下，为模型模块提供可切换的 MLflow Tracking 资源，使 Dagster 资产能记录参数、指标与工件，并在 MLflow UI 可见。
- 范围：
  - 资源：提供最小 API 的 MlflowTrackingResource，复用官方 mlflow 客户端；保留 MlflowStubResource 作为默认占位与本地无服务演示。
  - 资产：示例资产记录 param/metric/artifact，验证端到端写入。
  - 依赖：将 mlflow 加入运行时依赖。

二、设计与实现
1) 资源封装（最小 API，对齐 Stub）
- 资源文件：<mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/models/resources.py"></mcfile>
- 设计要点：
  - 与占位资源一致的最小接口：start_run、log_param、log_metric、close_run（另提供可选 log_artifact）。
  - 通过环境/配置读取 tracking_uri 与 experiment_name，默认适配 compose 下的 http://mlflow:5000。
  - 懒加载 mlflow，安装缺失时给出清晰报错；仅做薄封装，复杂用法可在资产中直接使用 mlflow.*。

2) 资源切换（环境变量控制）
- 入口文件：<mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile>
- 约定：
  - MLFLOW_USE_TRACKING∈{1,true,yes} 时启用真实 MlflowTrackingResource；否则使用 MlflowStubResource。
  - 支持 MLFLOW_TRACKING_URI、MLFLOW_EXPERIMENT 环境变量覆盖默认值。

3) 示例资产（记录参数/指标/工件）
- 资产文件：<mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/models/assets.py"></mcfile>
- 行为：
  - start_run → log_param("n_estimators", 10) → log_metric("rmse", 0.123)。
  - 生成本地 train_summary.txt 并在可用时调用 mlflow.log_artifact 上传（对 Stub 自动跳过）。
  - close_run 并返回 {run_id, status, artifact}。

4) 依赖与配置
- 依赖文件：<mcfile name="pyproject.toml" path="/home/dell/Projects/Dagma/pyproject.toml"></mcfile>
- 运行时依赖新增：mlflow（最小必要集）。
- 说明：
  - 本地开发通过 uv/pip 安装即可；容器模式下请确保 user_code 镜像同时安装 mlflow（参考 M2 的 Dockerfile_user_code，自行追加安装指令）。

三、运行指南（Ubuntu 24）
1) 安装依赖
- uv sync（或 pip install -e .）确保安装 mlflow。

2) 启动 MLflow（二选一）
- 选项A：使用项目 docker compose 的 mlflow 服务（见 <mcfile name="task_M2.md" path="/home/dell/Projects/Dagma/docs/task_M2.md"></mcfile> 中的 compose 片段）。
  - 默认 UI: http://localhost:5000
- 选项B：本地文件存储模式
  - 导出环境：MLFLOW_TRACKING_URI=file:///ABS_PATH/mlruns
  - MLflow UI 可通过 `mlflow ui --backend-store-uri $MLFLOW_TRACKING_URI` 启动（可选）。

3) 启用 Tracking 资源
- 导出环境变量（示例）：
  - export MLFLOW_USE_TRACKING=1
  - export MLFLOW_TRACKING_URI=http://localhost:5000  # 或 compose 下 http://mlflow:5000
  - export MLFLOW_EXPERIMENT=Default

4) 启动 Dagster 与物化资产
- uv run dagster dev（或使用项目脚本/Compose）
- 在 Web UI 中物化 models 组的 train_model_stub 资产；或使用 CLI：
  - uv run dagster asset materialize -m dagma.definitions train_model_stub

5) 验收
- 在 MLflow UI（/experiments/）能看到一次最新运行：
  - Params: n_estimators=10
  - Metrics: rmse=0.123
  - Artifacts: train_summary.txt

四、设计取舍与对齐
- 薄封装、最小接口：避免重复设计，直接复用官方 mlflow API；仅提供与 Stub 对齐的最小方法集合。
- 默认 Stub：避免强依赖外部服务影响开发体验；通过环境变量显式切换到 Tracking。
- 配置即代码：追踪端点/实验名称全部来自环境变量，避免硬编码与泄露。
- 单文件 <500 行：资源与资产实现均为少量函数，符合约束。

五、常见问题（FAQ）
- Q: 资产里还能直接用 mlflow.* API 吗？
  - A: 可以。资源仅提供最小公共面，复杂用法（如 autolog、模型注册）可在资产中直接 import mlflow。
- Q: 容器里报 mlflow 未安装？
  - A: 请在 user_code 镜像构建时安装 mlflow（参考 M2 的 Dockerfile_user_code），确保运行时镜像内有同版本依赖。
- Q: UI 看不到运行记录？
  - A: 检查 MLFLOW_USE_TRACKING 是否为真、MLFLOW_TRACKING_URI 是否可达；本地/容器的端口映射与网络名称需一致（compose 下通常为 http://mlflow:5000）。

六、文件索引
- 资源：<mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/models/resources.py"></mcfile>
- 资产：<mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/models/assets.py"></mcfile>
- 定义入口：<mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile>
- 依赖：<mcfile name="pyproject.toml" path="/home/dell/Projects/Dagma/pyproject.toml"></mcfile>
