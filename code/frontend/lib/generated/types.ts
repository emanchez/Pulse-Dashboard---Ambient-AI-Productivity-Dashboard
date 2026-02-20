/**
 * Task — canonical shape returned by GET /tasks/ and accepted by POST/PUT /tasks/:id.
 * This is the authoritative type definition for the Task contract; api.ts re-exports it
 * from here so there is a single source of truth inside lib/generated.
 *
 * All fields mirror the backend TaskSchema camelCase aliases.
 */
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
