"""Dagster definitions entrypoint (M1).

通过 [tool.dagster] 的 module_name="dagma.definitions"，dagster 可自动发现此入口。
"""

from __future__ import annotations

import os

from dagster import Definitions, load_assets_from_modules

from .defs.core.resources import BasePathResource
from .defs.data import assets as data_assets
from .defs.llm import assets as llm_assets
from .defs.llm import resources as llm_resources
from .defs.models import assets as model_assets
from .defs.models import resources as model_resources
from .defs.viz import assets as viz_assets
from .defs.viz import resources as viz_resources

all_assets = load_assets_from_modules([data_assets, model_assets, llm_assets, viz_assets])

# 通过环境变量切换 MLflow 资源（最佳实践：默认使用 Stub，生产/联调时显式打开）
_use_tracking = os.getenv("MLFLOW_USE_TRACKING", "").lower() in {"1", "true", "yes"}
_mlflow_resource = (
    model_resources.MlflowTrackingResource()
    if _use_tracking
    else model_resources.MlflowStubResource()
)

defs = Definitions(
    assets=all_assets,
    resources={
        "base_path": BasePathResource(),
        "mlflow": _mlflow_resource,
        # 将 llm 资源键统一指向一个组合资源（目前仅包含 LangflowStub 与 QdrantHttp）
        "llm": llm_resources.QdrantHttpResource(),
        "dashboard": viz_resources.DashboardStubResource(),
    },
)
