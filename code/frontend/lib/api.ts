const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// Re-export the typed PulseStats from the generated client
export type { PulseStats } from "./generated/pulseClient";
export { getPulse } from "./generated/pulseClient";

export type Task = {
  id?: string | null;
  name: string;
  priority?: string | null;
  tags?: string | null;
  isCompleted?: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
  deadline?: string | null;
  notes?: string | null;
};

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

export async function listTasks(token: string) {
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

export default { login, me, listTasks, createTask, updateTask, deleteTask };
