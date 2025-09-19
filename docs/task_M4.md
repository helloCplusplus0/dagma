# M4. 扩展能力与端到端示例（设计与落地）

本阶段目标：在不引入重量级依赖的前提下，给出一套可运行的“向量化→写入→检索”最小链路，并评估 LangChain 与 LangFlow 的集成策略；同时保持与既有 Dagster 项目结构与测试约束完全一致。

## 1. 选型与集成策略

- 优先级：先以 LangFlow 降低使用门槛，LangChain 暂缓引入。
  - 理由：LangFlow 提供可视化编排与现成组件，门槛更低；而 LangChain 在工程上可作后续增强（如复杂链/Agent），当前最小链路无需其核心抽象即可落地。
- 数据向量存储：Qdrant（REST）。
  - 理由：提供标准化向量检索 API；采用 HTTP 接口避免增加 Python 额外依赖，便于容器化与 CI 运行。
- 前端演示：Streamlit 可作为后续增强（M5+），当前以 Dagster 资产链和日志输出为主，不引入 UI 依赖。
- 训练与追踪：MLflow 仍保持占位资源（M1 已有），在本阶段不扩展。

结论：M4 先聚焦“最小可运行检索链”，UI 与复杂编排在后续里程碑推进。

## 2. 落地方案与代码结构

- 资源
  - 新增 Qdrant 轻量 HTTP 资源，实现最小 REST 客户端：
    - ensure_collection(size, distance)
    - upsert(points)
    - search(vector, limit, with_payload)
  - 代码位置：<mcfile name="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/resources.py"></mcfile>
    - 资源定义：<mcsymbol name="QdrantHttpResource" filename="resources.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/resources.py" startline="23" type="class"></mcsymbol>
- 资产
  - 在 LLM 模块追加最小资产链：
    - <mcsymbol name="embed_texts_stub" filename="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py" startline="15" type="function"></mcsymbol>：构造 8 维占位向量与 payload
    - <mcsymbol name="qdrant_upsert" filename="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py" startline="38" type="function"></mcsymbol>：幂等确保集合并写入 points
    - <mcsymbol name="qdrant_search" filename="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py" startline="52" type="function"></mcsymbol>：以第一条向量检索 top-3
  - 资产文件：<mcfile name="assets.py" path="/home/dell/Projects/Dagma/src/dagma/defs/llm/assets.py"></mcfile>
- 注册
  - 将 llm 资源键指向 QdrantHttpResource（后续可切换或组合）：
    - 定义入口：<mcfile name="definitions.py" path="/home/dell/Projects/Dagma/src/dagma/definitions.py"></mcfile>

## 3. 使用与运行

前置：需要一个可访问的 Qdrant 实例（本地或远程）。
- 本地快速启动（示例）：
  - docker 方式：`docker run -p 6333:6333 qdrant/qdrant:latest`
- 运行验证：
  - 通过 Python 调用 materialize：
    - materialize([embed_texts_stub, qdrant_upsert, qdrant_search])
  - 预期：
    - 能创建集合（如 dagma_demo）
    - upsert 成功返回结果
    - search 返回 top-3，日志打印结果

## 4. 设计取舍与最佳实践

- 无外部 SDK 依赖：采用标准库 urllib 实现极简 REST 调用，避免在 M4 引入新依赖。
- 幂等设计：资产在写入前确保集合存在，支持重复运行；ensure_collection 遇到 409 Conflict/“already exists” 视为幂等成功，保证重复物化不报错。
- Upsert 兼容性：为兼容不同 Qdrant 版本/部署，对 /collections/{collection}/points?wait=true 内置多格式回退，顺序依次为 1) POST {"points":[...]}; 2) POST {"batch": {ids, vectors, payloads}}; 3) PUT {"points":[...]}; 4) PUT {ids, vectors, payloads}；常见报错“missing field ids”将由回退路径自动规避。
- 单文件 <500 行：新增代码严格控制体量，注释清晰。
- 与现有结构一致：保持 ConfigurableResource、资产风格与命名一致，注册在 Definitions 中的统一键 `llm` 下。
- 可演进性：后续可将 `llm` 切换为 LangFlow 后端或组合资源，或以环境变量驱动选择。

## 5. LangChain 与 LangFlow 的必要性评估（面向 M4）

- LangFlow：更低门槛的可视化编排，便于非工程角色使用。适合在 M5+ 提供 UI Demo 与可视化链路管理。
- LangChain：提供丰富抽象与生态，适合：
  - 需要复杂链路编排/检索增强（分块、rerank、hybrid search）
  - 需要多模态、代理、工具调用等能力
- 本阶段选择：不同时引入二者。先用 LangFlow 作为未来 UI 入口的方向，M4 只做最小 REST 能力打底。

## 6. FAQ

- Q: 本地没有 Qdrant 会怎样？
  - A: upsert/search 会抛出连接错误。建议用 Docker 一键启动本地实例。
- Q: 如何切换集合名或端口？
  - A: 在 Definitions 中覆盖 llm 资源，或在 materialize 调用时传入资源实例参数。
- Q: 嵌入向量为什么这么“假”？
  - A: 这是最小可运行占位。后续可以接入真实 embedding 模型（如 OpenAI、BGE），但仍保持同样资产接口。

## 7. 后续演进（M5+）

- 接入真实向量化（embedding）与更强检索策略（过滤、rerank）。
- 引入 LangFlow UI 以低门槛编排与可视化调试。
- 如需工程化复杂度，择机引入 LangChain 生态组件（文本分块、Retriever、Tool/Agent）。
- 为 Qdrant 资源加入重试、超时、鉴权、SSL 校验与错误分类，并补充集成测试。
