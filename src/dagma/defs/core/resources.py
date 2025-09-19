from __future__ import annotations

from pathlib import Path

from dagster import ConfigurableResource
from pydantic import Field


class BasePathResource(ConfigurableResource):
    """基础路径资源，用于统一管理本地输出/缓存目录。

    - base_path: 根目录。默认放到项目工作区下的 .dagma_data。
    - ensure_dir(*parts): 创建并返回子目录 Path。
    - resolve(*parts): 拼接并返回 Path（不创建）。
    """

    base_path: str = Field(default=".dagma_data", description="本地工作根目录")

    def resolve(self, *parts: str | Path) -> Path:
        return Path(self.base_path).joinpath(*map(str, parts))

    def ensure_dir(self, *parts: str | Path) -> Path:
        p = self.resolve(*parts)
        p.mkdir(parents=True, exist_ok=True)
        return p


__all__ = ["BasePathResource"]
