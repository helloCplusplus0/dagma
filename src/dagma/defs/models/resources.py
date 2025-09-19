from __future__ import annotations

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


__all__ = ["MlflowStubResource"]
