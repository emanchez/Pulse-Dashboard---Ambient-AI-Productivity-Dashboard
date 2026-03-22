from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
import logging
import json
import re
import uuid

from ..db.session import async_session
from ..models.action_log import ActionLog
from ..core.security import decode_access_token
from sqlalchemy import insert

logger = logging.getLogger(__name__)

# Paths whose mutations are action-logged.  Extend here for new resources.
_LOGGED_PREFIXES = ("/tasks", "/reports", "/system-states", "/ai/accept-tasks")
_LOGGED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Semantic action type mapping: (HTTP method, resource prefix) → action type.
# Non-task routes get their own types but don't affect ghost list.
_ACTION_TYPE_MAP: dict[tuple[str, str], str] = {
    ("POST", "/tasks"): "TASK_CREATE",
    ("PUT", "/tasks"): "TASK_UPDATE",
    ("DELETE", "/tasks"): "TASK_DELETE",
    ("POST", "/reports"): "REPORT_CREATE",
    ("PUT", "/reports"): "REPORT_UPDATE",
    ("DELETE", "/reports"): "REPORT_DELETE",
    ("PATCH", "/reports"): "REPORT_ARCHIVE",
    ("POST", "/system-states"): "SYSTEM_STATE_CREATE",
    ("PUT", "/system-states"): "SYSTEM_STATE_UPDATE",
    ("DELETE", "/system-states"): "SYSTEM_STATE_DELETE",
    ("POST", "/ai"): "AI_ACCEPT_TASKS",
}


def _resolve_action_type(method: str, path: str) -> str:
    """Map HTTP method + path prefix to a semantic action type.

    Falls back to the raw "METHOD /path" format for unrecognised routes.
    """
    parts = [p for p in path.split("/") if p]
    resource = f"/{parts[0]}" if parts else path
    return _ACTION_TYPE_MAP.get((method, resource), f"{method} {path}")


def _extract_entity_id(parts: list[str]) -> str | None:
    """Return the second URL segment ONLY if it looks like a UUID entity reference.

    For paths like /tasks/<uuid> this returns the UUID.  For paths like
    /ai/accept-tasks (where the second segment is part of the endpoint name,
    not an entity id) this returns None, preventing spurious FK violations.
    """
    if len(parts) < 2:
        return None
    candidate = parts[1]
    try:
        uuid.UUID(candidate)  # validates UUID format (8-4-4-4-12 hex)
        return candidate
    except ValueError:
        return None


class ActionLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        try:
            path = request.url.path
            method = request.method.upper()
            if any(path.startswith(p) for p in _LOGGED_PREFIXES) and method in _LOGGED_METHODS:
                # attempt to extract entity id from path (/<resource>/{id})
                parts = [p for p in path.split("/") if p]
                task_id = _extract_entity_id(parts)  # stored in task_id column as generic entity ref

                # as a best-effort, parse response body for created resource id on POST
                if method == "POST" and not task_id:
                    try:
                        if hasattr(response, "body") and response.body:
                            body = response.body
                            if isinstance(body, (bytes, bytearray)):
                                body = body.decode()
                            data = json.loads(body)
                            task_id = data.get("id")
                    except Exception:
                        task_id = None

                # Extract user_id from Authorization header JWT (best-effort)
                user_id: str | None = None
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    try:
                        payload = decode_access_token(auth_header.removeprefix("Bearer ").strip())
                        user_id = payload.get("sub")
                    except Exception:
                        pass

                async with async_session() as session:
                    resolved_type = _resolve_action_type(method, path)
                    stmt = insert(ActionLog.__table__).values(
                        task_id=task_id,
                        action_type=resolved_type,
                        change_summary=f"{resolved_type} on {path} returned {response.status_code}",
                        user_id=user_id,
                    )
                    await session.execute(stmt)
                    await session.commit()
        except Exception:
            # Intentionally non-fatal: logging failure must not break the user request.
            logger.exception("ActionLog middleware failed to write log")

        return response
