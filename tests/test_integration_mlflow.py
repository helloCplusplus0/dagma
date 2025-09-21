import os
import time

import requests


def wait_for(url: str, timeout: int = 30, interval: float = 2.0) -> None:
    """简易等待直到 GET 返回 200，否则超时抛错。"""
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return
            last = (r.status_code, r.text[:200])
        except Exception as e:  # noqa: BLE001
            last = (type(e).__name__, str(e)[:200])
        time.sleep(interval)
    raise AssertionError(f"timeout waiting for {url}, last={last}")


def test_mlflow_http_ok() -> None:
    base = os.getenv("MLFLOW_URL", f"http://localhost:{os.getenv('MLFLOW_PORT', '5000')}")
    # 根路径由 gunicorn/werkzeug 提供，返回 200
    wait_for(base + "/", timeout=40)

    # create
    name = f"pytest-integ-{int(time.time())}"
    resp = requests.post(
        base + "/api/2.0/mlflow/experiments/create",
        json={"name": name},
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    exp_id = resp.json().get("experiment_id")
    assert exp_id, resp.text

    # search
    resp = requests.post(
        base + "/api/2.0/mlflow/experiments/search",
        json={"max_results": 5},
        timeout=10,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "experiments" in data
