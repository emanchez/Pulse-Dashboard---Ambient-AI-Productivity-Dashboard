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
