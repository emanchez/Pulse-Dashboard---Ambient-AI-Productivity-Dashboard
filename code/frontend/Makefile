.PHONY: deps dev start build test generate-api lint fmt

deps:
	npm ci

dev:
	npm run dev

start-dev:
	@echo "Starting frontend (background dev)"
	@# honor PORT env; record PID to ./.dev.pid
	@PORT=$${PORT:-3000} nohup npm run dev >/dev/null 2>&1 & echo $$! > ./.dev.pid && echo "PID saved to ./.dev.pid"

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
