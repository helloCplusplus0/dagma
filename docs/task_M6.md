# M6. LLM/Agent 与编排增强（LangFlow 无头集成）

目标：以最小、可运行、可扩展为原则，采用 LangFlow 的 REST（无头）方式与 Dagster 松耦合集成，不引入重量依赖，面向后续可替换/扩展（LangChain/自研）保持接口清晰。

—

## 1. 架构与设计

- 角色划分：
  - Dagster：负责调度、编排、可观测与资源注入；资产 langflow_run_flow 仅作为触发器与结果收集者。
  - LangFlow：负责 LLM/Agent 流程的可视化构建与运行，提供稳定的 REST API。
- 松耦合接口：
  - 通过极简资源 LangflowRestResource 封装 `/api/v1/run/{flow_id}`，仅覆盖本项目需要的参数：`input_value, output_type, input_type, tweaks, session_id, stream`。
  - 资源从环境变量读取连接信息，避免硬编码，便于 dev/prod 切换。
- 失败与降级：
  - 未配置 `LANGFLOW_DEFAULT_FLOW_ID` 时，资产返回 `{status: "skipped"}`，不使管道失败，保障可用性。

## 2. 环境变量

- LANGFLOW_BASE_URL：LangFlow 服务基础地址（例如 `http://localhost:7860`）。
- LANGFLOW_API_KEY：LangFlow 的 API Key（如启用鉴权时需要）。
- LANGFLOW_DEFAULT_FLOW_ID：默认调用的 Flow ID，用于 `langflow_run_flow` 资产。

注意：请勿提交真实密钥到仓库。参考 `.env.example` 增补相应变量项（仅示例）。

## 3. 代码实现（关键点）

- 资源：<mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/resources.py"></mcfile>
  - <mcsymbol name="LangflowRestResource" filename="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/resources.py" startline="18" type="class"></mcsymbol>：
    - 字段：`base_url, api_key, timeout, default_flow_id`
    - 方法：`run_flow(...)` → POST `/api/v1/run/{flow_id}`，返回原始 JSON
- 资产：<mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py"></mcfile>
  - <mcsymbol name="langflow_run_flow" filename="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py" startline="74" type="function"></mcsymbol>：
    - 注入资源 `langflow: LangflowRestResource`
    - 调用 `run_flow(input_value="ping from dagma", output_type="chat", input_type="chat")`
    - 记录响应摘要 keys，避免打印大对象
- 注册与调度：<mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile>
  - 环境变量装配 `langflow` 资源：`LANGFLOW_BASE_URL / API_KEY / DEFAULT_FLOW_ID`
  - 为 `langflow_run_flow` 定义作业与每日 `02:00` 调度（变量名：`run_langflow_daily`）。

## 4. 使用步骤（本地）

1) 启动或连接 LangFlow：
   - 本地运行 LangFlow（端口默认为 7860），或通过 compose/远程环境提供服务。
2) 在 LangFlow UI 创建/导入一个 Flow，获取 Flow ID，并在环境导出：
   - `export LANGFLOW_BASE_URL=http://localhost:7860`
   - `export LANGFLOW_DEFAULT_FLOW_ID=<your-flow-id>`
   - 如启用鉴权：`export LANGFLOW_API_KEY=...`
3) 启动 Dagster：`dagster dev`
4) 在 Dagster Web UI：
   - 搜索资产 `langflow_run_flow` 并物化；
   - 校验运行日志中出现 `langflow_run_flow summary=...`；
   - 如未设置 Flow ID，资产应返回 `{"status":"skipped"}`。
5) 查看调度：
   - 在 Schedules 页看到 `run_langflow_daily`（cron: `0 2 * * *`），可手动触发对应 Job 验证。

## 5. FAQ

- Q: 为什么不直接在 Dagster 中实现复杂 LLM 链路？
  - A: 保持编排与推理链分离，便于替换与独立演进；LangFlow 负责可视化、团队协作与快速迭代。
- Q: 如何切换到其他推理后端（如 LangChain/自研）？
  - A: 保持资源接口稳定（如 `run_flow` 风格），新增资源实现并替换 Definitions 中的资源装配；资产逻辑保持最小改动。
- Q: 生产环境需要注意什么？
  - A: 启用 API 鉴权（Key/JWT/OIDC/网关）、TLS/证书校验、超时/重试、审计日志与配额，避免在日志中打印敏感数据。

## 6. 验收清单

- Dagster UI 可物化 `langflow_run_flow` 且线上 LangFlow 返回有效响应；或在未配置 Flow ID 时返回 `skipped`。
- `run_langflow_daily` 调度已注册并可见，可手动触发验证。
- 代码遵循项目风格与规范，新增单文件 < 500 行，未引入冲突设计；文档步骤可复现。
