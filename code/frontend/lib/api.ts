const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// Re-export all generated API-contract types.
// PulseStats + getPulse live in the hand-written generated/pulseClient (preserved alongside generated files).
// Task, SessionLog, FlowState types come from the @hey-api/openapi-ts generated barrel.
export type { PulseStats } from "./generated/pulseClient";
export { getPulse } from "./generated/pulseClient";
import type {
  TaskSchema as Task,
  SessionLogSchema,
  SessionStartRequest,
  FlowStateSchema,
} from "./generated";
export type { Task, SessionLogSchema, SessionStartRequest, FlowStateSchema };

async function request(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "omit",
    ...opts,
    // headers must come AFTER ...opts so Content-Type is never overwritten
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined;
  return res.json();
}

export async function login(username: string, password: string) {
  return request(`/login`, { method: "POST", body: JSON.stringify({ username, password }) });
}

export async function me(token: string) {
  return request(`/me`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function listTasks(token: string): Promise<Task[]> {
  return request(`/tasks/`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function createTask(token: string, task: Task) {
  return request(`/tasks/`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(task) });
}

export async function updateTask(token: string, id: string, task: Task) {
  return request(`/tasks/${id}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(task) });
}

export async function deleteTask(token: string, id: string) {
  return request(`/tasks/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
}

// ── Session management ────────────────────────────────────────────────────────

export async function getActiveSession(token: string): Promise<SessionLogSchema | null> {
  const res = await fetch(`${BASE}/sessions/active`, {
    credentials: "omit",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed ${res.status}: ${text}`);
  }
  const text = await res.text();
  if (!text || text.trim() === "null") return null;
  return JSON.parse(text) as SessionLogSchema;
}

export async function startSession(token: string, body: SessionStartRequest): Promise<SessionLogSchema> {
  return request(`/sessions/start`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
}

export async function stopSession(token: string): Promise<SessionLogSchema> {
  return request(`/sessions/stop`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
}

// ── Flow state ────────────────────────────────────────────────────────────────

export async function getFlowState(token: string): Promise<FlowStateSchema> {
  return request(`/stats/flow-state`, { headers: { Authorization: `Bearer ${token}` } });
}

export default { login, me, listTasks, createTask, updateTask, deleteTask, getActiveSession, startSession, stopSession, getFlowState };
