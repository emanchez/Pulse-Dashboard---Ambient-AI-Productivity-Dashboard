from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_async_session
from ..models.task import Task, TaskCreate, TaskSchema, TaskUpdate
from .auth import get_current_user

router = APIRouter(prefix="/tasks")


@router.get("/", response_model=List[TaskSchema])
async def list_tasks(session: AsyncSession = Depends(get_async_session), user: str = Depends(get_current_user)):
    result = await session.execute(select(Task).where(Task.user_id == user))
    tasks = result.scalars().all()
    return [TaskSchema.model_validate(task.__dict__) for task in tasks]


@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, session: AsyncSession = Depends(get_async_session), user: str = Depends(get_current_user)):
    task = Task(
        name=payload.name,
        priority=payload.priority,
        tags=payload.tags,
        is_completed=payload.is_completed,
        deadline=payload.deadline,
        notes=payload.notes,
        user_id=user,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return TaskSchema.model_validate(task.__dict__)


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(task_id: str, payload: TaskUpdate, session: AsyncSession = Depends(get_async_session), user: str = Depends(get_current_user)):
    result = await session.get(Task, task_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if result.user_id != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    # Fields that must never be overwritten with None (system / primary-key fields)
    _protect_from_none = {"id", "created_at", "updated_at", "user_id"}
    for k, v in payload.model_dump().items():
        if not hasattr(result, k):
            continue
        if v is None and k in _protect_from_none:
            continue
        if v is None:
            continue
        setattr(result, k, v)
    session.add(result)
    await session.commit()
    await session.refresh(result)
    return TaskSchema.model_validate(result.__dict__)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, session: AsyncSession = Depends(get_async_session), user: str = Depends(get_current_user)):
    result = await session.get(Task, task_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if result.user_id != user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    await session.delete(result)
    await session.commit()
    return None
