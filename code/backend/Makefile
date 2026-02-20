.PHONY: deps dev start test e2e build lint fmt

# Prefer a project virtualenv if present, else fallback to system python
PYTHON := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || command -v python || command -v python3)
PORT ?= 8000

# Create a local virtualenv if missing and bootstrap pip
venv:
	@if [ ! -d .venv ]; then python3 -m venv .venv && echo "Created .venv"; fi
	@.venv/bin/python -m pip install --upgrade pip setuptools wheel || true

deps: venv
	@$(PYTHON) -m pip install --upgrade pip
	@$(PYTHON) -m pip install -r requirements.txt

dev:
	@echo "Starting backend in foreground (use ctrl-c to stop)"
	PYTHONPATH=$(PWD) $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(PORT)

start:
	@if [ ! -x .venv/bin/python ]; then echo "No .venv found — run 'make deps' to create virtualenv and install dependencies"; exit 1; fi
	@echo "Starting backend (background) using $(PYTHON)"
	PYTHONPATH=$(PWD) nohup $(PYTHON) -m uvicorn app.main:app --reload --host 127.0.0.1 --port $(PORT) >/dev/null 2>&1 & echo $$! > ./.dev.pid && echo "PID saved to ./.dev.pid"

test:
	$(PYTHON) -m pytest -q

e2e:
	$(PYTHON) -m pytest -q tests/e2e

build:
	@echo "No build step for backend (Python service)"

lint:
	@echo "No linter configured — add ruff/black for lint/format targets"

fmt:
	@echo "No formatter configured — add black/ruff for fmt target"
