from __future__ import annotations

from dagster import asset


@asset(group_name="llm", description="LLM 占位资产，不做任何调用。")
def llm_placeholder() -> str:
    return "placeholder"


__all__ = ["llm_placeholder"]
