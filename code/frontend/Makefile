.PHONY: deps dev start build test generate-api lint fmt

deps:
	npm ci

dev:
	npm run dev

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
