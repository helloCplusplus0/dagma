from __future__ import annotations

from dagster import asset


@asset(group_name="viz", description="将上游汇总数据包装为可视化可消费的结构。")
def viz_ready_data(sum_numbers: int) -> dict:
    return {"sum": sum_numbers, "title": "Numbers Summary"}


__all__ = ["viz_ready_data"]
