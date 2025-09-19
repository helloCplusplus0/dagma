from __future__ import annotations

from dagster import asset, get_dagster_logger

from .resources import QdrantHttpResource


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
) -> dict:
    vectors, payloads = embed_texts_stub
    dim = len(vectors[0]) if vectors else 0
    # 幂等创建集合
    llm.ensure_collection(size=dim, distance="Cosine")

    points = []
    for i, (vec, pl) in enumerate(zip(vectors, payloads, strict=False), start=1):
        points.append({"id": i, "vector": vec, "payload": pl})
    resp = llm.upsert(points)
    return {"count": len(points), "result": resp}


@asset(group_name="llm", description="使用第一条向量进行近邻检索，返回 top-3。")
def qdrant_search(
    qdrant_upsert: dict,
    embed_texts_stub: tuple[list[list[float]], list[dict]],
    llm: QdrantHttpResource,
) -> list[dict]:
    vectors, _payloads = embed_texts_stub
    if not vectors:
        return []
    log = get_dagster_logger()
    results = llm.search(vectors[0], limit=3, with_payload=True)
    log.info("qdrant_search top3=%s", results)
    return results


__all__ = ["llm_placeholder", "embed_texts_stub", "qdrant_upsert", "qdrant_search"]
