#!/usr/bin/env bash
set -euo pipefail
OPENAPI_URL="${OPENAPI_URL:-http://localhost:8000/openapi.json}"
echo "Fetching OpenAPI spec from $OPENAPI_URL"
# Use the CLI flags supported by @hey-api/openapi-ts: input (-i) and output folder (-o).
# Generate a TypeScript client into ./lib using the 'fetch' client adapter.
npx @hey-api/openapi-ts -i "$OPENAPI_URL" -o ./lib --client fetch
echo "Generated client in ./lib"
