from __future__ import annotations

import os
from typing import Any

from dagster import ConfigurableResource
from pydantic import Field


class MlflowStubResource(ConfigurableResource):
    """轻量级 MLflow 追踪占位资源（不引入外部依赖）。

    - start_run(): 返回一个伪 run_id，并将 run 置为活跃。
    - log_param(name, value): 记录参数到当前活跃 run。
    - log_metric(name, value): 记录指标到当前活跃 run。
    - close_run(run_id): 关闭对应 run。

    仅用于 M1 演示资源注入与测试。不要在生产中使用。
    """

    tracking_uri: str | None = None
    runs: list[dict] = Field(default_factory=list)

    def start_run(self) -> str:
        run_id = f"run-{len(self.runs) + 1}"
        self.runs.append({"run_id": run_id, "params": {}, "metrics": {}, "active": True})
        return run_id

    def _get_active_run(self) -> dict:
        for r in reversed(self.runs):
            if r.get("active"):
                return r
        raise RuntimeError("No active run. Call start_run() first.")

    def log_param(self, name: str, value: Any) -> None:
        r = self._get_active_run()
        r["params"][name] = value

    def log_metric(self, name: str, value: float) -> None:
        r = self._get_active_run()
        r["metrics"][name] = float(value)

    def close_run(self, run_id: str) -> None:
        for r in self.runs:
            if r.get("run_id") == run_id:
                r["active"] = False
                return
        raise KeyError(f"Run not found: {run_id}")


class MlflowTrackingResource(ConfigurableResource):
    """基于官方 mlflow 客户端的 Tracking 资源。

    设计原则：
    - 与仓库现有占位资源保持相同的最小 API（start_run/log_param/log_metric/close_run），
      以便资产代码可无缝切换。
    - 仅覆盖最小能力，避免过度封装；更复杂用法请直接在资产内引用 mlflow.* API。
    - 追踪端点与实验名称从配置/环境读取，默认适配 compose 网络（http://mlflow:5000）。
    """

    tracking_uri: str | None = Field(
        default_factory=lambda: os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"),
        description="MLflow Tracking URI，例如 http://mlflow:5000 或 file:///path/to/mlruns",
    )
    experiment_name: str = Field(default_factory=lambda: os.getenv("MLFLOW_EXPERIMENT", "Default"))

    # 运行态缓存最近一次 run_id（便于提供与 Stub 相同的调用体验）
    _active_run_id: str | None = None

    # 懒加载 mlflow，避免 import 带来的冷启动成本、同时兼容未安装时的清晰报错
    @staticmethod
    def _mlflow():
        try:
            import mlflow
        except Exception as e:  # pragma: no cover - 依赖问题属于环境配置错误
            raise RuntimeError(
                "mlflow 未安装，请先在环境中安装（pyproject.toml 或 Dockerfile_user_code）。"
            ) from e
        return mlflow

    def _ensure_experiment(self) -> None:
        mlflow = self._mlflow()
        assert self.tracking_uri is not None
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)

    def start_run(self) -> str:
        mlflow = self._mlflow()
        self._ensure_experiment()
        run = mlflow.start_run()
        self._active_run_id = run.info.run_id
        return run.info.run_id

    def _require_active(self) -> str:
        if not self._active_run_id:
            raise RuntimeError("No active run. Call start_run() first.")
        return self._active_run_id

    def log_param(self, name: str, value: Any) -> None:
        mlflow = self._mlflow()
        self._require_active()
        mlflow.log_param(name, value)

    def log_metric(self, name: str, value: float) -> None:
        mlflow = self._mlflow()
        self._require_active()
        mlflow.log_metric(name, float(value))

    def log_artifact(self, local_path: str, artifact_path: str | None = None) -> None:
        """可选：记录本地文件为 artifact。"""
        mlflow = self._mlflow()
        self._require_active()
        mlflow.log_artifact(local_path, artifact_path=artifact_path)

    def close_run(self, run_id: str | None = None) -> None:
        mlflow = self._mlflow()
        rid = run_id or self._require_active()
        # mlflow API 通过 end_run() 结束当前活动的 run；如 rid 与当前缓存不一致，则先切换
        if self._active_run_id and rid != self._active_run_id:
            # 通过设置 active run 的方式结束指定 run（简化处理：忽略切换失败情况）
            mlflow.start_run(run_id=rid)
        mlflow.end_run()
        if rid == self._active_run_id:
            self._active_run_id = None


__all__ = ["MlflowStubResource", "MlflowTrackingResource"]
