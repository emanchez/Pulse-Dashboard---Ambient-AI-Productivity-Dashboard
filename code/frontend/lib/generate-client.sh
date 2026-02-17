#!/usr/bin/env bash
set -euo pipefail
# Usage: ./generate-client.sh [OPENAPI_URL] [OUT_DIR]
# Defaults: OPENAPI_URL=${OPENAPI_URL:-http://localhost:8000/openapi.json}, OUT_DIR=./api-client
OPENAPI_URL="${1:-${OPENAPI_URL:-http://localhost:8000/openapi.json}}"
OUT_DIR="${2:-./api-client}"

echo "Fetching OpenAPI spec from $OPENAPI_URL"
echo "Generating TypeScript client into $OUT_DIR"

mkdir -p "$OUT_DIR"
# Use the CLI flags supported by @hey-api/openapi-ts: input (-i) and output folder (-o).
# Use the 'fetch' client adapter by default.
npx @hey-api/openapi-ts -i "$OPENAPI_URL" -o "$OUT_DIR" --client fetch

echo "Generated client in $OUT_DIR"
