from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.manual_report import ManualReport, ManualReportCreate, ManualReportUpdate
from ..models.task import Task

logger = logging.getLogger(__name__)


async def _validate_task_ids(db: AsyncSession, task_ids: list[str]) -> None:
    """Raise 400 if any task ID does not exist, or 500 on DB error.

    Uses a single batch query instead of N individual lookups.
    """
    if not task_ids:
        return
    unique_ids = set(task_ids)
    try:
        result = await db.execute(
            select(Task.id).where(Task.id.in_(unique_ids))
        )
        found_ids = set(result.scalars().all())
    except SQLAlchemyError as exc:
        logger.exception("Database error while validating task IDs")
        raise HTTPException(
            status_code=500,
            detail="Database error while validating linked tasks",
        ) from exc
    missing = unique_ids - found_ids
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Task(s) not found: {', '.join(sorted(missing))}",
        )


async def create_report(
    db: AsyncSession,
    user_id: str,
    data: ManualReportCreate,
) -> ManualReport:
    # Validate associated task IDs exist
    if data.associated_task_ids:
        await _validate_task_ids(db, data.associated_task_ids)

    word_count = len(data.body.split())

    report = ManualReport(
        user_id=user_id,
        title=data.title,
        body=data.body,
        word_count=word_count,
        associated_task_ids=data.associated_task_ids,
        tags=data.tags,
        status=data.status,
    )
    try:
        db.add(report)
        await db.commit()
        await db.refresh(report)
    except SQLAlchemyError as exc:
        logger.exception("Database error while creating report")
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail="Database error while creating report",
        ) from exc
    return report


async def list_reports(
    db: AsyncSession,
    user_id: str,
    offset: int = 0,
    limit: int = 20,
    status_filter: str | None = None,
) -> tuple[list[ManualReport], int]:
    base_where = [ManualReport.user_id == user_id]
    if status_filter is not None:
        base_where.append(ManualReport.status == status_filter)

    count_stmt = select(func.count()).select_from(ManualReport).where(*base_where)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    items_stmt = (
        select(ManualReport)
        .where(*base_where)
        .order_by(ManualReport.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    items_result = await db.execute(items_stmt)
    items = list(items_result.scalars().all())

    return items, total


async def get_report(
    db: AsyncSession,
    user_id: str,
    report_id: str,
) -> ManualReport | None:
    result = await db.execute(
        select(ManualReport)
        .where(ManualReport.id == report_id)
        .where(ManualReport.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_report(
    db: AsyncSession,
    user_id: str,
    report_id: str,
    data: ManualReportUpdate,
) -> ManualReport | None:
    report = await get_report(db, user_id, report_id)
    if report is None:
        return None

    updates = data.model_dump(exclude_unset=True)

    # Validate any new task IDs
    new_task_ids = updates.get("associated_task_ids")
    if new_task_ids:
        await _validate_task_ids(db, new_task_ids)

    for field, value in updates.items():
        setattr(report, field, value)

    # Recompute word_count if body changed
    if "body" in updates:
        report.word_count = len(updates["body"].split())

    try:
        await db.commit()
        await db.refresh(report)
    except SQLAlchemyError as exc:
        logger.exception("Database error while updating report %s", report_id)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail="Database error while updating report",
        ) from exc
    return report


async def delete_report(
    db: AsyncSession,
    user_id: str,
    report_id: str,
) -> bool:
    report = await get_report(db, user_id, report_id)
    if report is None:
        return False
    try:
        await db.delete(report)
        await db.commit()
    except SQLAlchemyError as exc:
        logger.exception("Database error while deleting report %s", report_id)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail="Database error while deleting report",
        ) from exc
    return True


async def archive_report(
    db: AsyncSession,
    user_id: str,
    report_id: str,
) -> ManualReport | None:
    report = await get_report(db, user_id, report_id)
    if report is None:
        return None
    report.status = "archived"
    try:
        await db.commit()
        await db.refresh(report)
    except SQLAlchemyError as exc:
        logger.exception("Database error while archiving report %s", report_id)
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail="Database error while archiving report",
        ) from exc
    return report
