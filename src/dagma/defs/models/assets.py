from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from dagster import ResourceParam, asset, get_dagster_logger


@asset(
    group_name="models",
    description="最小训练占位：记录参数、指标与 artifact 至 MLflow 资源（stub 或 tracking）。",
)
def train_model_stub(mlflow: ResourceParam[Any]) -> dict:
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
    log.info("Completed train_model_stub run_id=%s artifact=%s", run_id, artifact_path)
    return {"run_id": run_id, "status": "ok", "artifact": artifact_path}


__all__ = ["train_model_stub"]
