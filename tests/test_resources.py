from __future__ import annotations

import pathlib
import sys

# 确保 src 在测试导入路径中（避免依赖可编辑安装）
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from dagma.defs.core.resources import BasePathResource  # noqa: E402
from dagma.defs.models.resources import MlflowStubResource  # noqa: E402


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
