.PHONY: deps dev start start-dev stop clean-cache build test generate-api lint fmt

deps:
	npm ci

dev:
	npm run dev

start-dev:
	@echo "Starting frontend (background dev)"
	@# honor PORT env; record PID to ./.dev.pid
	@PORT=$${PORT:-3000} nohup npm run dev >/dev/null 2>&1 & echo $$! > ./.dev.pid && echo "PID saved to ./.dev.pid"

stop:
	@# Kill by PID file if available
	@if [ -f ./.dev.pid ]; then \
		echo "Stopping frontend (PID: $$(cat ./.dev.pid))"; \
		kill $$(cat ./.dev.pid) 2>/dev/null || true; \
		rm -f ./.dev.pid; \
	fi
	@# Fallback: kill any next-server still bound to port 3000
	@PIDS=$$(lsof -ti :3000 2>/dev/null); if [ -n "$$PIDS" ]; then echo "Killing lingering next-server on :3000 (PIDs: $$PIDS)"; kill $$PIDS 2>/dev/null || true; fi
	@# Always clear the Next.js build cache for a clean restart
	@if [ -d ./.next ]; then echo "Clearing .next cache..."; rm -rf ./.next; fi
	@echo "Frontend stopped."

clean-cache:
	@if [ -d ./.next ]; then rm -rf ./.next && echo ".next cache cleared."; else echo ".next cache already clean."; fi

start:
	@echo "Starting frontend (background)"
	nohup npm run start >/dev/null 2>&1 & echo $$! > ./.dev.pid && echo "PID saved to ./.dev.pid"

build:
	npm run build

generate-api:
	npm run generate:api

test:
	@echo "No frontend test runner configured; add vitest/jest to enable `make test`"

lint:
	@echo "No linter configured — add eslint/prettier to enable `make lint`"

fmt:
	@echo "No formatter configured — add prettier to enable `make fmt`"
