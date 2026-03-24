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
  // Strip the "cookie" sentinel — never forward it as a real Bearer token.
  // credentials: "include" is required for cross-origin cookie auth (production).
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token && token !== "cookie") {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}/stats/pulse`, {
    headers,
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed ${res.status}: ${text}`);
  }
  return res.json();
}
