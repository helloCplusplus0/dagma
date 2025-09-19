from __future__ import annotations

import pathlib
import sys

# 确保 src 在测试导入路径中（避免依赖可编辑安装）
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from dagster import materialize  # noqa: E402

from dagma.defs.data import assets as data_assets  # noqa: E402
from dagma.defs.llm import assets as llm_assets  # noqa: E402
from dagma.defs.models import assets as model_assets  # noqa: E402
from dagma.defs.models import resources as model_resources  # noqa: E402


def test_data_assets_materialize():
    result = materialize([data_assets.raw_numbers, data_assets.sum_numbers])
    assert result.success
    assert result.output_for_node("sum_numbers") == 6


def test_models_asset_with_resource_override():
    # 通过 resources 参数注入/覆盖资源
    result = materialize(
        [model_assets.train_model_stub],
        resources={"mlflow": model_resources.MlflowStubResource(tracking_uri="file://stub")},
    )
    assert result.success
    payload = result.output_for_node("train_model_stub")
    assert payload["status"] == "ok"
    assert "run_id" in payload


def test_llm_assets_defined():
    # 轻量验证：资产函数可被 materialize 调用到定义阶段（不执行到外部请求）
    assert callable(llm_assets.embed_texts_stub)
    assert callable(llm_assets.qdrant_upsert)
    assert callable(llm_assets.qdrant_search)
