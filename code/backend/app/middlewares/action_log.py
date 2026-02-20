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


class ActionLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        try:
            path = request.url.path
            method = request.method.upper()
            if path.startswith("/tasks") and method in {"POST", "PUT", "DELETE"}:
                # attempt to extract task id from path (/tasks/{id})
                parts = [p for p in path.split("/") if p]
                task_id = None
                if len(parts) >= 2 and parts[0] == "tasks":
                    # e.g. /tasks/<id>
                    if len(parts) >= 2:
                        task_id = parts[1]

                # as a best-effort, try to parse response body for created resource id
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
            logger.exception("ActionLog middleware failed to write log")

        return response
