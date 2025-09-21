"""Dagster definitions entrypoint (M1).

通过 [tool.dagster] 的 module_name="dagma.definitions"，dagster 可自动发现此入口。
"""

from __future__ import annotations

import os

from dagster import Definitions, ScheduleDefinition, define_asset_job, load_assets_from_modules

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

# LangFlow 资源：从环境变量读取连接参数，保持安全与可迁移性
_langflow_resource = llm_resources.LangflowRestResource(
    base_url=os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860"),
    api_key=os.getenv("LANGFLOW_API_KEY"),
    default_flow_id=os.getenv("LANGFLOW_DEFAULT_FLOW_ID"),
)

# Qdrant 资源：从环境变量读取，容器内请设置 QDRANT_HOST=qdrant
_qdrant_resource = llm_resources.QdrantHttpResource(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", "6333")),
    use_https=os.getenv("QDRANT_USE_HTTPS", "false").lower() in {"1", "true", "yes"},
    api_key=os.getenv("QDRANT_API_KEY"),
    collection=os.getenv("QDRANT_COLLECTION", "embeddings"),
    timeout=float(os.getenv("QDRANT_TIMEOUT", "30")),
)

# 为 LangFlow 资产创建最小作业与调度（每日 02:00 触发）
run_langflow_job = define_asset_job("run_langflow_job", selection=["langflow_run_flow"])
run_langflow_daily = ScheduleDefinition(
    name="run_langflow_daily", job=run_langflow_job, cron_schedule="0 2 * * *"
)

# 示例作业：最小 RAG 链与模型训练（便于 UI/CLI 快速触发验证）
run_llm_rag_job = define_asset_job(
    "run_llm_rag_job", selection=["embed_texts_stub", "qdrant_upsert", "qdrant_search"]
)
run_models_train_job = define_asset_job("run_models_train_job", selection=["train_model_stub"])


defs = Definitions(
    assets=all_assets,
    resources={
        "base_path": BasePathResource(),
        "mlflow": _mlflow_resource,
        # 将 llm 资源键统一指向 Qdrant REST 客户端
        "llm": _qdrant_resource,
        # LangFlow 独立资源键，供 langflow_run_flow 使用
        "langflow": _langflow_resource,
        "dashboard": viz_resources.DashboardStubResource(),
    },
    schedules=[run_langflow_daily],
    jobs=[run_langflow_job, run_llm_rag_job, run_models_train_job],
)
