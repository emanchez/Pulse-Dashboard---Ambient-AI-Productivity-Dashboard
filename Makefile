# Repository-level Makefile — orchestrates backend and frontend targets
# Usage: `make <target>` or `make -C code/backend <target>` / `make -C code/frontend <target>`

.PHONY: dev stop start build deps test generate-api fmt lint

TMP_DIR := .tmp
BACKEND_DIR := code/backend
FRONTEND_DIR := code/frontend
BACKEND_PID := $(TMP_DIR)/dev-backend.pid
FRONTEND_PID := $(TMP_DIR)/dev-frontend.pid

dev:
	@mkdir -p $(TMP_DIR)
	@echo "Starting backend (background)..."
	@$(MAKE) -C $(BACKEND_DIR) start PORT=8000
	@cp -f $(BACKEND_DIR)/.dev.pid $(BACKEND_PID) 2>/dev/null || true
	@echo "Starting frontend (background)..."
	@# Ensure frontend runs in dev mode on port 3000 (background)
	@$(MAKE) -C $(FRONTEND_DIR) start-dev PORT=3000
	@cp -f $(FRONTEND_DIR)/.dev.pid $(FRONTEND_PID) 2>/dev/null || true
	@echo "Started backend (PID: $$(cat $(BACKEND_PID) 2>/dev/null || echo 'unknown')) and frontend (PID: $$(cat $(FRONTEND_PID) 2>/dev/null || echo 'unknown'))."

stop:
	@if [ -f $(BACKEND_PID) ]; then echo "Stopping backend (PID: $$(cat $(BACKEND_PID)))"; kill $$(cat $(BACKEND_PID)) 2>/dev/null || true; rm -f $(BACKEND_PID); fi
	@if [ -f $(FRONTEND_PID) ]; then echo "Stopping frontend (PID: $$(cat $(FRONTEND_PID)))"; kill $$(cat $(FRONTEND_PID)) 2>/dev/null || true; rm -f $(FRONTEND_PID); fi
	@rm -f $(BACKEND_DIR)/.dev.pid $(FRONTEND_DIR)/.dev.pid || true

start:
	@$(MAKE) -C $(BACKEND_DIR) start & $(MAKE) -C $(FRONTEND_DIR) start

deps:
	@$(MAKE) -C $(BACKEND_DIR) deps
	@$(MAKE) -C $(FRONTEND_DIR) deps

test:
	@$(MAKE) -C $(BACKEND_DIR) test
	@echo "Frontend: no test runner configured; see Makefile in code/frontend for placeholder."

generate-api:
	@$(MAKE) -C $(FRONTEND_DIR) generate-api

build:
	@$(MAKE) -C $(FRONTEND_DIR) build
	@$(MAKE) -C $(BACKEND_DIR) build || true

fmt:
	@$(MAKE) -C $(BACKEND_DIR) fmt || true
	@$(MAKE) -C $(FRONTEND_DIR) fmt || true

lint:
	@$(MAKE) -C $(BACKEND_DIR) lint || true
	@$(MAKE) -C $(FRONTEND_DIR) lint || true
