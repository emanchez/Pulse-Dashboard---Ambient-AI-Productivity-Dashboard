from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_async_session
from ..models.system_state import SystemStateCreate, SystemStateSchema, SystemStateUpdate
from ..services import system_state_service
from .auth import get_current_user

router = APIRouter(prefix="/system-states")


@router.post("", response_model=SystemStateSchema, status_code=status.HTTP_201_CREATED)
async def create_system_state(
    payload: SystemStateCreate,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> SystemStateSchema:
    state = await system_state_service.create_state(session, user_id, payload)
    return SystemStateSchema.model_validate(state)


@router.get("", response_model=list[SystemStateSchema])
async def list_system_states(
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> list[SystemStateSchema]:
    states = await system_state_service.list_states(session, user_id)
    return [SystemStateSchema.model_validate(s) for s in states]


# /active must be declared BEFORE /{state_id} to avoid route shadowing
@router.get("/active", response_model=Optional[SystemStateSchema])
async def get_active_system_state(
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> SystemStateSchema | None:
    state = await system_state_service.get_active_state(session, user_id)
    if state is None:
        return None
    return SystemStateSchema.model_validate(state)


@router.put("/{state_id}", response_model=SystemStateSchema)
async def update_system_state(
    state_id: str,
    payload: SystemStateUpdate,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> SystemStateSchema:
    state = await system_state_service.update_state(session, user_id, state_id, payload)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
    return SystemStateSchema.model_validate(state)


@router.delete("/{state_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system_state(
    state_id: str,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> None:
    deleted = await system_state_service.delete_state(session, user_id, state_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System state not found")
    return None
