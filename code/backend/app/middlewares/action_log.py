from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable

from ..db.session import get_async_session
from ..models.action_log import ActionLog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert


class ActionLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        try:
            path = request.url.path
            method = request.method.upper()
            if path.startswith("/tasks") and method in {"POST", "PUT", "DELETE"}:
                # log an action — minimal: store path and method
                async for session in get_async_session():
                    stmt = insert(ActionLog.__table__).values(
                        task_id=None,
                        action_type=f"{method} {path}",
                        change_summary=f"{method} on {path} returned {response.status_code}",
                    )
                    await session.execute(stmt)
                    await session.commit()
        except Exception:
            # never crash middleware on logging failure
            pass

        return response
