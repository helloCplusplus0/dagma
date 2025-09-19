"""Dagster definitions entrypoint (M1).

通过 [tool.dagster] 的 module_name=\"dagma.definitions\"，dagster 可自动发现此入口。
"""

from __future__ import annotations

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

defs = Definitions(
    assets=all_assets,
    resources={
        "base_path": BasePathResource(),
        "mlflow": model_resources.MlflowStubResource(),
        "llm": llm_resources.LangflowStubResource(),
        "dashboard": viz_resources.DashboardStubResource(),
    },
)
