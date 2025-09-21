from __future__ import annotations

import pathlib
import sys

# 确保 src 在测试导入路径中（避免依赖可编辑安装）
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from dagma.defs.core.resources import BasePathResource  # noqa: E402
from dagma.defs.models.resources import (  # noqa: E402
    MlflowStubResource,
    MlflowTrackingResource,
)


def test_base_path_resource(tmp_path):
    res = BasePathResource(base_path=str(tmp_path))
    p = res.ensure_dir("sub")
    assert p.exists() and p.is_dir()


def test_mlflow_stub_resource_logs():
    r = MlflowStubResource()
    run_id = r.start_run()
    r.log_param("alpha", 0.1)
    r.log_metric("loss", 0.01)
    r.close_run(run_id)
    # 断言写入到最近一次 run
    assert r.runs[-1]["params"]["alpha"] == 0.1
    assert r.runs[-1]["metrics"]["loss"] == 0.01
    assert r.runs[-1]["active"] is False


def test_mlflow_tracking_resource_min_api(monkeypatch):
    """使用 monkeypatch 模拟 mlflow 客户端，验证 Tracking 资源的最小 API 行为。

    仅聚焦交互：set_tracking_uri/set_experiment/start_run/log_param/log_metric/end_run。
    """

    class _Run:
        def __init__(self, run_id: str):
            self.info = type("Info", (), {"run_id": run_id})

    class _MLF:
        def __init__(self):
            self.calls = []
            self.active_run = None

        def set_tracking_uri(self, uri):
            self.calls.append(("set_tracking_uri", uri))

        def set_experiment(self, name):
            self.calls.append(("set_experiment", name))

        def start_run(self, run_id=None):
            rid = run_id or "rid-1"
            self.active_run = rid
            self.calls.append(("start_run", rid))
            return _Run(rid)

        def log_param(self, k, v):
            assert self.active_run is not None
            self.calls.append(("log_param", k, v))

        def log_metric(self, k, v):
            assert self.active_run is not None
            self.calls.append(("log_metric", k, float(v)))

        def end_run(self):
            assert self.active_run is not None
            self.calls.append(("end_run", self.active_run))
            self.active_run = None

    fake = _MLF()

    # 将 MlflowTrackingResource._mlflow 指向我们的 fake 实例
    monkeypatch.setattr(MlflowTrackingResource, "_mlflow", staticmethod(lambda: fake))

    r = MlflowTrackingResource(tracking_uri="http://mlflow:5000", experiment_name="Default")
    rid = r.start_run()
    assert rid == "rid-1"

    r.log_param("alpha", 0.1)
    r.log_metric("loss", 0.01)
    r.close_run(rid)

    # 基本交互断言顺序（前两步确保实验与 URI 设置）
    assert ("set_tracking_uri", "http://mlflow:5000") in fake.calls
    assert ("set_experiment", "Default") in fake.calls
    # 至少包含一次 start_run/log_param/log_metric/end_run
    assert any(c[0] == "start_run" for c in fake.calls)
    assert any(c[0] == "log_param" for c in fake.calls)
    assert any(c[0] == "log_metric" for c in fake.calls)
    assert any(c[0] == "end_run" for c in fake.calls)
