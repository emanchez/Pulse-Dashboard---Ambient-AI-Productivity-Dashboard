.PHONY: deps dev start start-dev stop clean-cache build test generate-api lint fmt

deps:
	npm ci

dev:
	npm run dev

start-dev:
	@if [ ! -d node_modules ]; then echo "node_modules not found — run 'make deps' (npm ci) first"; exit 1; fi
	@mkdir -p logs
	@echo "Starting frontend dev server (background) on port $${PORT:-3000}"
	@PORT=$${PORT:-3000} nohup npm run dev >logs/frontend.log 2>&1 & echo $$! > ./.dev.pid
	@echo "PID $$(cat ./.dev.pid) saved to ./.dev.pid — logs at logs/frontend.log"
	@echo "Waiting for frontend to become ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
		sleep 1; \
		if curl -sf http://127.0.0.1:$${PORT:-3000} >/dev/null 2>&1; then \
			echo "Frontend is up on :$${PORT:-3000}"; \
			exit 0; \
		fi; \
	done; \
	echo "ERROR: Frontend did not start within 15s — check logs/frontend.log:"; \
	cat logs/frontend.log 2>/dev/null || true; \
	exit 1

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
