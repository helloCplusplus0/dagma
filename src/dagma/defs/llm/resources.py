from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

from dagster import ConfigurableResource
from pydantic import Field


class LangflowStubResource(ConfigurableResource):
    endpoint: str | None = Field(default=None, description="LangFlow/LangChain 服务端点（占位）")

    def invoke(self, prompt: str) -> str:
        # 仅返回占位响应，后续 M4 再接入真实 LLM
        return f"LLM-ECHO: {prompt}"


# 新增：LangFlow REST 资源（最小可用）。
class LangflowRestResource(ConfigurableResource):
    """极简 LangFlow REST 客户端资源（不依赖第三方库）。

    仅覆盖本项目最小需求：
    - run_flow(flow_id, input_value, output_type, input_type, tweaks, session_id, stream)

    注意：生产中建议启用鉴权（API Key/网关）、重试/超时、TLS/证书校验与审计日志。
    """

    base_url: str = Field(
        default="http://localhost:7860",
        description="LangFlow 服务基础地址，如 http://localhost:7860",
    )
    api_key: str | None = Field(
        default=None, description="LangFlow API Key（可选，若启用鉴权则必填）"
    )
    timeout: float = Field(default=10.0, description="HTTP 超时时间（秒）")

    # 便于 Dagster 调度使用的默认 Flow 配置（可选）
    default_flow_id: str | None = Field(default=None, description="默认调用的 Flow ID（可选）")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        url = urllib.parse.urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url=url, data=data, headers=self._headers(), method=method.upper()
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                if not raw:
                    return None
                # LangFlow 返回 JSON
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise RuntimeError(f"LangFlow HTTP {e.code} {e.reason}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"LangFlow connection error: {e}") from e

    def run_flow(
        self,
        *,
        flow_id: str | None = None,
        input_value: str = "hello",
        output_type: str = "chat",
        input_type: str = "chat",
        tweaks: dict[str, Any] | None = None,
        session_id: str | None = None,
        stream: bool = False,
    ) -> Any:
        """调用 LangFlow 的 /api/v1/run/{flow_id} 接口。

        返回值为 LangFlow 的原始 JSON 响应，便于上层资产记录/解析。
        """
        fid = flow_id or self.default_flow_id
        if not fid:
            # 无 Flow ID 时直接返回跳过原因，避免资产失败
            return {"status": "skipped", "reason": "no flow_id provided"}

        query = f"?stream={'true' if stream else 'false'}"
        path = f"/api/v1/run/{fid}{query}"
        body: dict[str, Any] = {
            "input_value": input_value,
            "output_type": output_type,
            "input_type": input_type,
        }
        if tweaks:
            body["tweaks"] = tweaks
        if session_id:
            body["session_id"] = session_id
        return self._request("POST", path, body)


class QdrantHttpResource(ConfigurableResource):
    """极简 Qdrant REST 客户端资源（不依赖第三方库）。

    仅覆盖本项目最小需求：
    - ensure_collection(size, distance): 创建或幂等确保 collection 存在
    - upsert(points): 写入/更新向量
    - search(vector, limit, with_payload): 近邻检索

    注意：生产中请使用官方 SDK 并启用鉴权/SSL/重试等能力。
    """

    host: str = Field(default="localhost", description="Qdrant 主机名或域名")
    port: int = Field(default=6333, description="Qdrant 端口，默认 6333")
    use_https: bool = Field(default=False, description="是否使用 https")
    api_key: str | None = Field(
        default=None, description="Qdrant API Key（可选，Qdrant Cloud 需配置）"
    )
    collection: str = Field(default="dagma_demo", description="默认使用的 collection 名称")
    timeout: float = Field(default=5.0, description="HTTP 超时时间（秒）")

    # ===== 内部基础能力 =====
    def _base_url(self) -> str:
        scheme = "https" if self.use_https else "http"
        return f"{scheme}://{self.host}:{self.port}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            # Qdrant Cloud 约定 Header 名为 api-key
            headers["api-key"] = self.api_key
        return headers

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        url = urllib.parse.urljoin(self._base_url() + "/", path.lstrip("/"))
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url=url, data=data, headers=self._headers(), method=method.upper()
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
            raise RuntimeError(f"Qdrant HTTP {e.code} {e.reason}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Qdrant connection error: {e}") from e

    # ===== 公开 API =====
    def ensure_collection(self, size: int, distance: str = "Cosine") -> Any:
        """确保 collection 存在（幂等）。"""
        path = f"/collections/{self.collection}"
        body = {"vectors": {"size": size, "distance": distance}}
        try:
            return self._request("PUT", path, body)
        except RuntimeError as e:
            msg = str(e)
            # 已存在时返回 409，应视为幂等成功
            if "409 Conflict" in msg or "already exists" in msg:
                return {"status": {"message": "collection exists"}}
            raise

    def upsert(self, points: Iterable[dict[str, Any]]) -> Any:
        """向集合写入 points（包含 id, vector, payload）。

        为兼容不同 Qdrant 版本，依次尝试以下格式：
        1) POST: {"points": [PointStruct,...]}
        2) POST: {"batch": {ids, vectors, payloads}}
        3) PUT:  {"points": [PointStruct,...]}
        4) PUT:  顶层 {ids, vectors, payloads}
        """
        base_path = f"/collections/{self.collection}/points?wait=true"
        pts = list(points)
        # 统一 batch 结构
        batch = {
            "ids": [p["id"] for p in pts],
            "vectors": [p["vector"] for p in pts],
        }
        payloads = [p.get("payload") for p in pts]
        if any(pl is not None for pl in payloads):
            batch["payloads"] = payloads

        # 1) POST points
        try:
            return self._request("POST", base_path, {"points": pts})
        except RuntimeError:
            pass

        # 2) POST batch
        try:
            return self._request("POST", base_path, {"batch": batch})
        except RuntimeError:
            pass

        # 3) PUT points
        try:
            return self._request("PUT", base_path, {"points": pts})
        except RuntimeError:
            pass

        # 4) PUT top-level batch
        return self._request("PUT", base_path, batch)

    def search(
        self, vector: list[float], limit: int = 3, with_payload: bool = True
    ) -> list[dict[str, Any]]:
        """向集合执行相似度搜索，返回结果列表。"""
        path = f"/collections/{self.collection}/points/search"
        body = {"vector": vector, "limit": int(limit), "with_payload": with_payload}
        resp = self._request("POST", path, body)
        return resp.get("result", []) if isinstance(resp, dict) else []


__all__ = ["LangflowStubResource", "LangflowRestResource", "QdrantHttpResource"]
