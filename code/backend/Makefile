.PHONY: deps dev start stop test e2e build lint fmt

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

stop:
	@# Kill by PID file if available
	@if [ -f ./.dev.pid ]; then \
		echo "Stopping backend (PID: $$(cat ./.dev.pid))"; \
		kill $$(cat ./.dev.pid) 2>/dev/null || true; \
		rm -f ./.dev.pid; \
	fi
	@# Fallback: kill any uvicorn still bound to the configured port
	@PIDS=$$(lsof -ti :$(PORT) 2>/dev/null); if [ -n "$$PIDS" ]; then echo "Killing lingering uvicorn on :$(PORT) (PIDs: $$PIDS)"; kill $$PIDS 2>/dev/null || true; fi
	@echo "Backend stopped."

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
