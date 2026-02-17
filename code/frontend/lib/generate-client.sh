#!/usr/bin/env bash
set -euo pipefail
OPENAPI_URL="${OPENAPI_URL:-http://localhost:8000/openapi.json}"
echo "Fetching OpenAPI spec from $OPENAPI_URL"
npx @hey-api/openapi-ts "$OPENAPI_URL" -o ./lib/api.ts --language typescript
echo "Generated ./lib/api.ts"
