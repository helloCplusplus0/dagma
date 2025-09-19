from __future__ import annotations

from dagster import ConfigurableResource
from pydantic import Field


class DashboardStubResource(ConfigurableResource):
    output_dir: str = Field(default=".dagma_dash", description="仪表盘发布输出目录（占位）")

    def publish(self, payload: dict) -> str:
        # 仅返回一个伪路径，后续阶段引入真实可视化/应用
        return f"{self.output_dir}/index.html"


__all__ = ["DashboardStubResource"]
