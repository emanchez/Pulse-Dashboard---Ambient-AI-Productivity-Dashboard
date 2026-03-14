from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
import logging
import json

from ..db.session import async_session
from ..models.action_log import ActionLog
from ..core.security import decode_access_token
from sqlalchemy import insert

logger = logging.getLogger(__name__)

# Paths whose mutations are action-logged.  Extend here for new resources.
_LOGGED_PREFIXES = ("/tasks", "/reports", "/system-states", "/ai/accept-tasks")
_LOGGED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _extract_entity_id(parts: list[str]) -> str | None:
    """Return the second URL segment as a generic entity reference, if present."""
    return parts[1] if len(parts) >= 2 else None


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
                    stmt = insert(ActionLog.__table__).values(
                        task_id=task_id,
                        action_type=f"{method} {path}",
                        change_summary=f"{method} on {path} returned {response.status_code}",
                        user_id=user_id,
                    )
                    await session.execute(stmt)
                    await session.commit()
        except Exception:
            # Intentionally non-fatal: logging failure must not break the user request.
            logger.exception("ActionLog middleware failed to write log")

        return response
