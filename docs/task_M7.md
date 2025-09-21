# M7. 观测闭环与生产化指引（不新增 UI 服务）

目标（当前阶段）
- 不引入新的可视化/门户服务，优先用 Dagster UI + 外部系统自身 UI（MLflow、LangFlow、Qdrant）完成观测闭环。
- 通过“运行时元数据”和“深链接 URL”，在 Dagster UI 的资产页面直接观察关键指标、样本与一跳跳转。
- 提供可直接触发的示例 Job，便于一键验证链路健康。

本次变更概览（代码索引）
- 数据资产：添加运行时 Metadata（计数、样本）
  - <mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/data/assets.py"></mcfile>
- 模型资产：添加 MLflow 深链接与运行时 Metadata（参数/指标计数、artifact 标记）
  - <mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/models/assets.py"></mcfile>
- LLM/RAG 资产：为 Qdrant 与 LangFlow 增加可点击的 REST/UI 链接与返回条数等 Metadata
  - <mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py"></mcfile>
- 定义入口：新增示例作业，便于 UI/CLI 快速触发
  - <mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile>
- 现有测试：保持兼容（资产 MaterializeResult.value 为原有返回值）
  - <mcfile name="test_assets.py" path="/home/dell/Projects/Dagma/tests/test_assets.py"></mcfile>
  - <mcfile name="test_resources.py" path="/home/dell/Projects/Dagma/tests/test_resources.py"></mcfile>

一、设计要点与最佳实践
- 运行时元数据：使用 Dagster MaterializeResult.metadata 附加关键信息（计数、预览、URL）。
- 深链接策略：
  - MLflow 运行页：优先读取环境变量 MLFLOW_UI_BASE_URL（示例：http://localhost:5000），可选 MLFLOW_EXPERIMENT_ID；回退为资源的 tracking_uri（若可解析为 http/https）。
  - Qdrant：根据资源配置拼装集合与查询 endpoint URL，便于健康验证与排障。
  - LangFlow：根据资源 base_url 拼装 UI 根地址（支持 http/https，自带端口），透出 default_flow_id 供人工确认。
- 示例 Job：定义 run_llm_rag_job 与 run_models_train_job，减少多次点击，把链路串起来验证。
- 安全合规：不在代码中硬编码密钥；所有敏感配置均从环境变量读取；不打印请求/响应中的敏感字段；只记录必要摘要。

二、实现细节（关键修改说明）
- 数据资产元数据
  - raw_numbers：count、preview(json)。
  - sum_numbers：input_count、result。
- 模型资产元数据与深链接
  - train_model_stub：在关闭/提交 run 后，构造 MLflow UI 与 run URL（若可用）；metadata 含 params_count、metrics_count、artifact_uploaded、mlflow_tracking_uri、mlflow_run_url。
- LLM/RAG 元数据与深链接
  - qdrant_upsert：points_count、collection、qdrant_collection_url。
  - qdrant_search：returned、collection、qdrant_search_endpoint。
  - langflow_run_flow：langflow_ui_url、default_flow_id（仅摘要，不输出大响应）。
- 示例 Job（Dagster UI/CLI 可见）
  - run_llm_rag_job：embed_texts_stub -> qdrant_upsert -> qdrant_search。
  - run_models_train_job：train_model_stub。

三、如何运行与验收
A) 本地启动与基础验证
- 启动 Dagster：
  - 命令：dagster dev（或使用容器编排中的 webserver + user_code 方案）。
- 打开 UI：http://localhost:3000/
- 在“Assets”页：
  - 点击 data 组资产，能看到 count、preview、input_count、result 等元数据字段。
  - 点击 llm 组资产：
    - qdrant_upsert 元数据中包含 qdrant_collection_url（可点击）。
    - qdrant_search 元数据中包含 qdrant_search_endpoint（可点击）。
  - 点击 models 组资产：
    - train_model_stub 元数据中包含 mlflow_tracking_uri 与（若可推导）mlflow_run_url（可点击）。

B) 触发示例 Job
- 在“Jobs”页：
  - 运行 run_llm_rag_job，预期：各步骤 SUCCESS，qdrant_* 资产 Metadata 显示链接。
  - 运行 run_models_train_job，预期：SUCCESS，Metadata 中包含 MLflow URL（如已配置）。
- 在“Schedules”页：
  - 可见 run_langflow_daily（默认 02:00），用于最小演示；实际生产请调优。

C) CLI 快速验证（可选）
- 列出资产：dagster asset list -m dagma.definitions
- 物化数据资产：dagster asset materialize --select raw_numbers,sum_numbers -m dagma.definitions
- 运行 Job：
  - dagster job launch -j run_llm_rag_job -m dagma.definitions
  - dagster job launch -j run_models_train_job -m dagma.definitions

四、测试与质量门槛
- 现有测试用例保持通过：
  - data 与 models 资产在返回 MaterializeResult 后，value 保持原值，断言不变。
  - MLflow Stub 资源测试不受影响。
- 建议新增/扩展（如需要）：
  - 验证 metadata 字段存在且类型正确（可在单测中读取 result.get_asset_materialization_events）。
- 运行：pytest -q（可结合 pytest-cov 观察覆盖率）。

五、安全与合规注意事项
- 不提交明文密钥：API keys、token、云端凭据等一律通过环境变量/密钥管理注入。
- 最小权限原则：
  - MLflow：使用最低限度写入权限的 token；若仅观察可切到只读角色。
  - Qdrant/LangFlow：调试阶段采用本地/隔离网络；生产开启鉴权与 TLS。
- 日志与元数据去敏：
  - 不记录原始文本/向量完整数据；只记录计数与链接。
  - 出错时打印摘要与状态码，避免泄露请求体。

六、环境变量与配置建议
- MLflow：
  - MLFLOW_USE_TRACKING=true|false（默认 false 使用 Stub）
  - MLFLOW_UI_BASE_URL=http://localhost:5000（生产为真实域名）
  - MLFLOW_EXPERIMENT_ID=0（可选，用于拼装 run URL）
- LangFlow：
  - LANGFLOW_BASE_URL=http://localhost:7860
  - LANGFLOW_API_KEY=...（如开启鉴权）
  - LANGFLOW_DEFAULT_FLOW_ID=...（可选）
- Qdrant：在资源中以参数化方式设定 host/port/collection/use_https/api_key（见资源定义）。

七、故障排查（快速指引）
- MLflow URL 未显示：检查 MLFLOW_USE_TRACKING 与 MLFLOW_UI_BASE_URL 是否设置为 http/https 前缀；容器网络/端口映射是否正确。
- Qdrant 相关链接 404：确认集合已创建、collection 名称一致；检查 host/port/use_https 与 api-key。
- LangFlow 调用失败：检查 BASE_URL/API_KEY/Flow ID；可通过 langflow_ui_url 点击进入页面手动验证。

八、后续可选增强（纳入 Backlog）
- 将元数据扩展为统一的“观测字段规范”（如 event_type、latency_ms、size_bytes）。
- 收敛到 Prometheus/OpenTelemetry 的指标/追踪，统一观测性栈。
- 当出现统一门户需求时，再评估最小接入 Streamlit/Plotly Dash。
