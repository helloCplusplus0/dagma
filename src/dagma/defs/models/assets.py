from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from dagster import MaterializeResult, MetadataValue, ResourceParam, asset, get_dagster_logger


@asset(
    group_name="models",
    description="最小训练占位：记录参数、指标与 artifact 至 MLflow 资源（stub 或 tracking）。",
)
def train_model_stub(mlflow: ResourceParam[Any]) -> MaterializeResult[dict]:
    log = get_dagster_logger()
    run_id = mlflow.start_run()
    # 记录参数与指标
    mlflow.log_param("n_estimators", 10)
    mlflow.log_metric("rmse", 0.123)

    # 生成并上传最小 artifact（例如训练摘要）
    artifact_path = None
    try:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "train_summary.txt"
            p.write_text(f"run_id={run_id}\nrmse=0.123\n", encoding="utf-8")
            # 兼容：MlflowStubResource 没有 log_artifact 方法，使用鸭子类型判断
            if hasattr(mlflow, "log_artifact"):
                mlflow.log_artifact(str(p))
                artifact_path = str(p)
    except Exception as e:  # 容错：artifact 上传失败不阻断最小示例
        log.warning("artifact logging skipped: %s", e)

    mlflow.close_run(run_id)

    # 深链接拼装：优先使用 MLFLOW_UI_BASE_URL，其次尝试资源的 tracking_uri
    ui_base = os.getenv("MLFLOW_UI_BASE_URL") or getattr(mlflow, "tracking_uri", None)
    exp_id = os.getenv("MLFLOW_EXPERIMENT_ID")
    run_url = None
    if isinstance(ui_base, str) and ui_base.startswith(("http://", "https://")):
        base = ui_base.rstrip("/")
        run_url = (
            f"{base}/#/experiments/{exp_id}/runs/{run_id}" if exp_id else f"{base}/#/runs/{run_id}"
        )

    payload: dict = {"run_id": run_id, "status": "ok", "artifact": artifact_path}
    log.info("Completed train_model_stub run_id=%s artifact=%s", run_id, artifact_path)

    return MaterializeResult(
        value=payload,
        metadata={
            "params_count": 1,
            "metrics_count": 1,
            "artifact_uploaded": artifact_path is not None,
            "mlflow_tracking_uri": MetadataValue.url(ui_base) if isinstance(ui_base, str) else None,
            "mlflow_run_url": MetadataValue.url(run_url) if run_url else None,
        },
    )


__all__ = ["train_model_stub"]
