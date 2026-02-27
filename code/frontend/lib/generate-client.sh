#!/usr/bin/env bash
set -euo pipefail
# Usage: ./generate-client.sh [OPENAPI_URL] [OUT_DIR]
# Defaults: OPENAPI_URL=${OPENAPI_URL:-http://localhost:8000/openapi.json}, OUT_DIR=./api-client
OPENAPI_URL="${1:-${OPENAPI_URL:-http://localhost:8000/openapi.json}}"
OUT_DIR="${2:-./api-client}"

echo "Fetching OpenAPI spec from $OPENAPI_URL"
echo "Generating TypeScript client into $OUT_DIR"

mkdir -p "$OUT_DIR"
# @hey-api/openapi-ts >=0.46 requires the -p/--plugins flag to emit files.
# The TypeScript-only plugin emits types.gen.ts + index.ts (no service functions).
npx @hey-api/openapi-ts -i "$OPENAPI_URL" -o "$OUT_DIR" -p @hey-api/typescript

echo "Generated client in $OUT_DIR"

# ── Restore hand-written companion files ────────────────────────────────────
# The generator clears $OUT_DIR on each run. pulseClient.ts is a hand-written
# file that lives alongside the generated output; it provides getPulse() and
# the PulseStats type alias used by PulseCard.tsx and lib/api.ts.
# Restore it unconditionally after each generation pass.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat > "$OUT_DIR/pulseClient.ts" << 'PULSE_EOF'
// Hand-written alongside @hey-api/openapi-ts generated files.
// Preserved because the TypeScript-only plugin does not emit service functions.
// getPulse and PulseStats are imported directly by PulseCard.tsx and lib/api.ts.

export type PulseStats = {
  silenceState: "paused" | "stagnant" | "engaged";
  lastActionAt: string | null;
  gapMinutes: number;
  pausedUntil: string | null;
};

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function getPulse(token: string): Promise<PulseStats> {
  const res = await fetch(`${BASE}/stats/pulse`, {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    credentials: "omit",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed ${res.status}: ${text}`);
  }
  return res.json();
}
PULSE_EOF

echo "Restored pulseClient.ts in $OUT_DIR"
