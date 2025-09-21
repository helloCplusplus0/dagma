.PHONY: help test smoke dev-up dev-down

help:
	@echo "Available targets:"
	@echo "  make test     - 运行 pytest (使用本地虚拟环境 .venv)"
	@echo "  make smoke    - 运行端到端冒烟脚本 scripts/smoke.sh"
	@echo "  make dev-up   - 分组启动开发服务 (scripts/start_env.sh up minimal)"
	@echo "  make dev-down - 停止并清理服务 (scripts/start_env.sh down)"

# 优先使用本地 .venv，否则自动创建
VENV=.venv
PIP=$(VENV)/bin/pip
PY=$(VENV)/bin/python
PYTEST=$(VENV)/bin/pytest

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e .
	$(PIP) install -U pytest pytest-cov

# 运行测试
 test: $(VENV)/bin/activate
	$(PYTEST) -q

# 端到端冒烟
 smoke:
	bash scripts/smoke.sh

# 开发环境编排（可选便捷）
 dev-up:
	bash scripts/start_env.sh up minimal

 dev-down:
	bash scripts/start_env.sh down
