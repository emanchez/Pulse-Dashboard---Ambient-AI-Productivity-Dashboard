from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer

from ..db.session import get_async_session
from ..models.task import Task, TaskSchema
from ..core.security import decode_access_token

router = APIRouter(prefix="/tasks")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    return payload.get("sub")


@router.get("/", response_model=List[TaskSchema])
async def list_tasks(session: AsyncSession = Depends(get_async_session), user: str = Depends(get_current_user)):
    result = await session.execute(select(Task))
    tasks = result.scalars().all()
    return [TaskSchema.model_validate(task.__dict__) for task in tasks]


@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskSchema, session: AsyncSession = Depends(get_async_session), user: str = Depends(get_current_user)):
    task = Task(
        id=payload.id or None,
        name=payload.name,
        priority=payload.priority,
        tags=payload.tags,
        is_completed=payload.is_completed,
        deadline=payload.deadline,
        notes=payload.notes,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return TaskSchema.model_validate(task.__dict__)


@router.put("/{task_id}", response_model=TaskSchema)
async def update_task(task_id: str, payload: TaskSchema, session: AsyncSession = Depends(get_async_session), user: str = Depends(get_current_user)):
    result = await session.get(Task, task_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for k, v in payload.model_dump().items():
        if hasattr(result, k) and v is not None:
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
    await session.delete(result)
    await session.commit()
    return None
