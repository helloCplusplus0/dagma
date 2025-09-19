from __future__ import annotations

from dagster import asset


@asset(group_name="data", description="生成一个最小示例数据集：一组整数。")
def raw_numbers() -> list[int]:
    return [1, 2, 3]


@asset(group_name="data", description="计算整数列表的和，演示资产依赖。")
def sum_numbers(raw_numbers: list[int]) -> int:  # noqa: D401
    return sum(raw_numbers)


__all__ = ["raw_numbers", "sum_numbers"]
