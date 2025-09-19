from __future__ import annotations

from dagster import StaticPartitionsDefinition

# 示例静态分区定义（M1 不强制使用，仅作为后续扩展示例）
small_static_partitions = StaticPartitionsDefinition(["train", "test"])

__all__ = ["small_static_partitions"]
