from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.auth import get_current_user
from ..db.session import get_async_session
from ..models.session_log import SessionLogSchema, SessionStartRequest
from ..services.session_service import get_active_session, start_session, stop_session

router = APIRouter()


@router.post("/start", response_model=SessionLogSchema, status_code=status.HTTP_201_CREATED)
async def sessions_start(
    req: SessionStartRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> SessionLogSchema:
    if not req.task_name or not req.task_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="taskName must not be blank")
    session_log = await start_session(db, user_id, req)
    return SessionLogSchema.model_validate(session_log)


@router.post("/stop", response_model=SessionLogSchema, status_code=status.HTTP_200_OK)
async def sessions_stop(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> SessionLogSchema:
    session_log = await stop_session(db, user_id)
    if session_log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")
    return SessionLogSchema.model_validate(session_log)


@router.get("/active", response_model=SessionLogSchema | None, status_code=status.HTTP_200_OK)
async def sessions_active(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> SessionLogSchema | None:
    session_log = await get_active_session(db, user_id)
    if session_log is None:
        return None
    return SessionLogSchema.model_validate(session_log)
