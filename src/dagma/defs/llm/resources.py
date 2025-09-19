from __future__ import annotations

from dagster import ConfigurableResource
from pydantic import Field


class LangflowStubResource(ConfigurableResource):
    endpoint: str | None = Field(default=None, description="LangFlow/LangChain 服务端点（占位）")

    def invoke(self, prompt: str) -> str:
        # 仅返回占位响应，后续 M4 再接入真实 LLM
        return f"LLM-ECHO: {prompt}"


__all__ = ["LangflowStubResource"]
