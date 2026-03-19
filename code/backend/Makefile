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
	@mkdir -p logs
	@echo "Starting backend (background, no --reload) using $(PYTHON)"
	@PYTHONPATH=$(PWD) nohup $(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port $(PORT) >logs/backend.log 2>&1 & echo $$! > ./.dev.pid
	@echo "PID $$(cat ./.dev.pid) saved to ./.dev.pid — logs at logs/backend.log"
	@echo "Waiting for backend to become ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		sleep 1; \
		if curl -sf http://127.0.0.1:$(PORT)/health >/dev/null 2>&1; then \
			echo "Backend is up on :$(PORT)"; \
			exit 0; \
		fi; \
	done; \
	echo "ERROR: Backend did not start within 10s — check logs/backend.log:"; \
	cat logs/backend.log 2>/dev/null || true; \
	exit 1

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
