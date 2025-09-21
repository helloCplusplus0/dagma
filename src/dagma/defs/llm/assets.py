from __future__ import annotations

from dagster import MaterializeResult, MetadataValue, asset, get_dagster_logger

from .resources import LangflowRestResource, QdrantHttpResource


@asset(group_name="llm", description="LLM 占位资产，不做任何调用。")
def llm_placeholder() -> str:
    return "placeholder"


# ===== 最小 RAG 资产链：向量化 -> 写入 -> 检索 =====
@asset(
    group_name="llm",
    description="简易文本嵌入（占位实现）：将每个字符映射为 ord 值并归一化，维度为 8。",
)
def embed_texts_stub() -> tuple[list[list[float]], list[dict]]:
    """返回 (vectors, payloads)。

    - vectors: list[8-dim float]
    - payloads: 与向量对应的元数据（含 text）
    """
    texts = ["hello world", "dagma project", "qdrant vector db", "langflow ui"]
    dim = 8
    vectors: list[list[float]] = []
    payloads: list[dict] = []
    for t in texts:
        vals = [ord(c) % 97 for c in t[:dim]]  # 取前 dim 个字符的数值特征
        if len(vals) < dim:
            vals += [0] * (dim - len(vals))
        # 简单归一化到 [0,1]
        m = max(1, max(vals))
        vec = [v / m for v in vals]
        vectors.append(vec)
        payloads.append({"text": t})
    return vectors, payloads


@asset(group_name="llm", description="将向量写入 Qdrant（REST）。")
def qdrant_upsert(
    embed_texts_stub: tuple[list[list[float]], list[dict]], llm: QdrantHttpResource
) -> MaterializeResult[dict]:
    vectors, payloads = embed_texts_stub
    dim = len(vectors[0]) if vectors else 0
    # 幂等创建集合
    llm.ensure_collection(size=dim, distance="Cosine")

    points = []
    for i, (vec, pl) in enumerate(zip(vectors, payloads, strict=False), start=1):
        points.append({"id": i, "vector": vec, "payload": pl})
    resp = llm.upsert(points)

    # 组装 Qdrant REST 链接（便于健康性验证与排障）
    scheme = "https" if llm.use_https else "http"
    base = f"{scheme}://{llm.host}:{llm.port}"
    coll_url = f"{base}/collections/{llm.collection}"

    return MaterializeResult(
        value={"count": len(points), "result": resp},
        metadata={
            "points_count": len(points),
            "collection": llm.collection,
            "qdrant_collection_url": MetadataValue.url(coll_url),
        },
    )


@asset(group_name="llm", description="使用第一条向量进行近邻检索，返回 top-3。")
def qdrant_search(
    qdrant_upsert: dict,
    embed_texts_stub: tuple[list[list[float]], list[dict]],
    llm: QdrantHttpResource,
) -> MaterializeResult[list[dict]]:
    vectors, _payloads = embed_texts_stub
    if not vectors:
        return MaterializeResult(value=[])
    log = get_dagster_logger()
    results = llm.search(vectors[0], limit=3, with_payload=True)
    log.info("qdrant_search top3=%s", results)

    scheme = "https" if llm.use_https else "http"
    base = f"{scheme}://{llm.host}:{llm.port}"
    search_ep = f"{base}/collections/{llm.collection}/points/search"

    return MaterializeResult(
        value=results,
        metadata={
            "returned": len(results),
            "collection": llm.collection,
            "qdrant_search_endpoint": MetadataValue.url(search_ep),
        },
    )


@asset(group_name="llm", description="通过 LangFlow REST 调用指定 Flow（最小示例）。")
def langflow_run_flow(langflow: LangflowRestResource) -> MaterializeResult[dict]:
    """最小可用：如果未配置 default_flow_id，则标记跳过；否则直接调用并记录关键信息。"""
    log = get_dagster_logger()
    resp = langflow.run_flow(input_value="ping from dagma", output_type="chat", input_type="chat")
    # 记录关键信息，避免打印过大响应
    summary = {
        "status": resp.get("status") if isinstance(resp, dict) else None,
        "id": resp.get("id") if isinstance(resp, dict) else None,
        "keys": list(resp.keys())[:8] if isinstance(resp, dict) else None,
    }
    log.info("langflow_run_flow summary=%s", summary)

    # 使用资源的 base_url 作为 UI 根地址，避免访问不存在的 host/port/use_https 属性
    ui_base = getattr(langflow, "base_url", "http://localhost:7860")
    if isinstance(ui_base, str):
        ui_base = ui_base.rstrip("/")

    return MaterializeResult(
        value=resp if isinstance(resp, dict) else {},
        metadata={
            "langflow_ui_url": MetadataValue.url(
                ui_base if isinstance(ui_base, str) else "http://localhost:7860"
            ),
            "default_flow_id": getattr(langflow, "default_flow_id", None),
        },
    )


__all__ = [
    "llm_placeholder",
    "embed_texts_stub",
    "qdrant_upsert",
    "qdrant_search",
    "langflow_run_flow",
]
