const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// Re-export all generated API-contract types.
// PulseStats + getPulse live in the hand-written generated/pulseClient (preserved alongside generated files).
// Task, SessionLog, FlowState types come from the @hey-api/openapi-ts generated barrel.
export type { PulseStats } from "./generated/pulseClient";
export { getPulse } from "./generated/pulseClient";
import type {
  TaskSchema as Task,
  TaskCreate,
  TaskUpdate,
  SessionLogSchema,
  SessionStartRequest,
  FlowStateSchema,
  ManualReportSchema,
  ManualReportCreate,
  ManualReportUpdate,
  PaginatedReportsResponse,
  SystemStateSchema,
  SystemStateCreate,
  SystemStateUpdate,
} from "./generated";
export type {
  Task,
  TaskCreate,
  TaskUpdate,
  SessionLogSchema,
  SessionStartRequest,
  FlowStateSchema,
  ManualReportSchema,
  ManualReportCreate,
  ManualReportUpdate,
  PaginatedReportsResponse,
  SystemStateSchema,
  SystemStateCreate,
  SystemStateUpdate,
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

export async function listTasks(token: string): Promise<Task[]> {
  return request(`/tasks/`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function createTask(token: string, task: TaskCreate): Promise<Task> {
  return request(`/tasks/`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(task) });
}

export async function updateTask(token: string, id: string, task: TaskUpdate): Promise<Task> {
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

// ── Reports ───────────────────────────────────────────────────────────────────

export async function createReport(token: string, data: ManualReportCreate): Promise<ManualReportSchema> {
  return request(`/reports`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
}

export async function listReports(token: string, offset = 0, limit = 20, status?: string): Promise<PaginatedReportsResponse> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (status) params.set("status", status);
  return request(`/reports?${params}`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function getReport(token: string, id: string): Promise<ManualReportSchema> {
  return request(`/reports/${id}`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function updateReport(token: string, id: string, data: ManualReportUpdate): Promise<ManualReportSchema> {
  return request(`/reports/${id}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
}

export async function deleteReport(token: string, id: string): Promise<void> {
  return request(`/reports/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
}

export async function archiveReport(token: string, id: string): Promise<ManualReportSchema> {
  return request(`/reports/${id}/archive`, { method: "PATCH", headers: { Authorization: `Bearer ${token}` } });
}

// ── System States ─────────────────────────────────────────────────────────────

export async function createSystemState(token: string, data: SystemStateCreate): Promise<SystemStateSchema> {
  return request(`/system-states`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
}

export async function listSystemStates(token: string): Promise<SystemStateSchema[]> {
  return request(`/system-states`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function getActiveSystemState(token: string): Promise<SystemStateSchema | null> {
  const res = await fetch(`${BASE}/system-states/active`, {
    credentials: "omit",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed ${res.status}: ${text}`);
  }
  const text = await res.text();
  if (!text || text.trim() === "null") return null;
  return JSON.parse(text) as SystemStateSchema;
}

export async function updateSystemState(token: string, id: string, data: SystemStateUpdate): Promise<SystemStateSchema> {
  return request(`/system-states/${id}`, { method: "PUT", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(data) });
}

export async function deleteSystemState(token: string, id: string): Promise<void> {
  return request(`/system-states/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
}

// ── AI / Synthesis ────────────────────────────────────────────────────────

export interface SuggestedTask {
  name: string;
  priority: string;
  rationale: string;
  isLowFriction: boolean;
}

export interface SynthesisResponse {
  id: string;
  summary: string;
  theme: string;
  commitmentScore: number;
  suggestedTasks: SuggestedTask[];
  status: string;
  periodStart: string;
  periodEnd: string;
  createdAt: string;
}

export interface TaskSuggestionResponse {
  suggestions: SuggestedTask[];
  isReEntryMode: boolean;
  rationale: string;
}

export interface CoPlanResponse {
  hasConflict: boolean;
  conflictDescription: string | null;
  resolutionQuestion: string | null;
  suggestedPriority: string | null;
}

export interface AIUsageBucket {
  used: number;
  limit: number;
  resetsIn: string;
}

export interface AIUsageSummary {
  synthesis: AIUsageBucket;
  suggest: AIUsageBucket;
  coplan: AIUsageBucket;
}

export interface GhostTask {
  id: string;
  name: string;
  priority: string;
  daysOpen: number;
  actionCount: number;
  lastActionAt: string | null;
  ghostReason: string;
}

export interface GhostListResponse {
  ghosts: GhostTask[];
  total: number;
}

export interface WeeklySummaryResponse {
  totalActions: number;
  tasksCompleted: number;
  tasksCreated: number;
  reportsWritten: number;
  sessionsCompleted: number;
  longestSilenceHours: number;
  activeDays: number;
  periodStart: string;
  periodEnd: string;
}

export async function triggerSynthesis(token: string): Promise<{ id: string; status: string }> {
  return request(`/ai/synthesis`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({}) });
}

export async function getLatestSynthesis(token: string): Promise<SynthesisResponse> {
  return request(`/ai/synthesis/latest`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function getSynthesis(token: string, id: string): Promise<SynthesisResponse> {
  return request(`/ai/synthesis/${id}`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function suggestTasks(token: string, focusArea?: string): Promise<TaskSuggestionResponse> {
  return request(`/ai/suggest-tasks`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ focusArea: focusArea || null }),
  });
}

export async function acceptTasks(token: string, tasks: { name: string; priority: string; notes?: string }[]): Promise<{ createdTaskIds: string[] }> {
  return request(`/ai/accept-tasks`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ tasks }),
  });
}

export async function coPlan(token: string, reportId: string): Promise<CoPlanResponse> {
  return request(`/ai/co-plan`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ reportId }),
  });
}

export async function getAIUsage(token: string): Promise<AIUsageSummary> {
  return request(`/ai/usage`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function getGhostList(token: string): Promise<GhostListResponse> {
  return request(`/stats/ghost-list`, { headers: { Authorization: `Bearer ${token}` } });
}

export async function getWeeklySummary(token: string): Promise<WeeklySummaryResponse> {
  return request(`/stats/weekly-summary`, { headers: { Authorization: `Bearer ${token}` } });
}

export default {
  login, me,
  listTasks, createTask, updateTask, deleteTask,
  getActiveSession, startSession, stopSession,
  getFlowState,
  createReport, listReports, getReport, updateReport, deleteReport, archiveReport,
  createSystemState, listSystemStates, getActiveSystemState, updateSystemState, deleteSystemState,
  triggerSynthesis, getLatestSynthesis, getSynthesis, suggestTasks, acceptTasks, coPlan,
  getAIUsage, getGhostList, getWeeklySummary,
};
