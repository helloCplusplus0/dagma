from __future__ import annotations

from dagster import MaterializeResult, MetadataValue, asset


@asset(group_name="data", description="生成一个最小示例数据集：一组整数。")
def raw_numbers() -> MaterializeResult[list[int]]:
    data = [1, 2, 3]
    # 附加观测性元数据：记录数量与样本
    return MaterializeResult(
        value=data,
        metadata={
            "count": len(data),
            "preview": MetadataValue.json(data),
        },
    )


@asset(group_name="data", description="计算整数列表的和，演示资产依赖。")
def sum_numbers(raw_numbers: list[int]) -> MaterializeResult[int]:  # noqa: D401
    total = sum(raw_numbers)
    # 附加观测性元数据：输入规模与结果摘要
    return MaterializeResult(
        value=total,
        metadata={
            "input_count": len(raw_numbers),
            "result": total,
        },
    )


__all__ = ["raw_numbers", "sum_numbers"]
