from __future__ import annotations

from dagster import asset, get_dagster_logger

from .resources import MlflowStubResource


@asset(group_name="models", description="最小训练占位：记录参数与指标至 MLflow stub。")
def train_model_stub(mlflow: MlflowStubResource) -> dict:
    log = get_dagster_logger()
    run_id = mlflow.start_run()
    mlflow.log_param("n_estimators", 10)
    mlflow.log_metric("rmse", 0.123)
    mlflow.close_run(run_id)
    log.info("Completed train_model_stub run_id=%s", run_id)
    return {"run_id": run_id, "status": "ok"}


__all__ = ["train_model_stub"]
