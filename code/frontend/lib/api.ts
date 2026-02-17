// Minimal TypeScript client stub for the backend API.
// This provides typed helper functions for the frontend to use.

export type LoginRequest = { username: string; password: string }
export type TokenResponse = { accessToken: string }

export type Task = {
  id: string
  title: string
  description?: string
  completed: boolean
}

const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(baseUrl + path, { ...opts, credentials: 'same-origin' })
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`)
  return (await res.json()) as T
}

export async function login(body: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export async function getMe(token: string): Promise<{ username: string; sub: string }> {
  return request('/me', { headers: { Authorization: `Bearer ${token}` } })
}

export async function listTasks(token: string): Promise<Task[]> {
  return request('/tasks', { headers: { Authorization: `Bearer ${token}` } })
}

export async function createTask(token: string, task: Partial<Task>): Promise<Task> {
  return request('/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(task),
  })
}

export default {
  login,
  getMe,
  listTasks,
  createTask,
}
