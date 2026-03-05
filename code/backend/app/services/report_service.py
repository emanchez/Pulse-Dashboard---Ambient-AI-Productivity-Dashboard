from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.manual_report import ManualReport, ManualReportCreate, ManualReportUpdate
from ..models.task import Task


async def create_report(
    db: AsyncSession,
    user_id: str,
    data: ManualReportCreate,
) -> ManualReport:
    # Validate associated task IDs exist
    if data.associated_task_ids:
        for task_id in data.associated_task_ids:
            result = await db.get(Task, task_id)
            if result is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task '{task_id}' does not exist",
                )

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
    db.add(report)
    await db.commit()
    await db.refresh(report)
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
        for task_id in new_task_ids:
            result = await db.get(Task, task_id)
            if result is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task '{task_id}' does not exist",
                )

    for field, value in updates.items():
        setattr(report, field, value)

    # Recompute word_count if body changed
    if "body" in updates:
        report.word_count = len(updates["body"].split())

    await db.commit()
    await db.refresh(report)
    return report


async def delete_report(
    db: AsyncSession,
    user_id: str,
    report_id: str,
) -> bool:
    report = await get_report(db, user_id, report_id)
    if report is None:
        return False
    await db.delete(report)
    await db.commit()
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
    await db.commit()
    await db.refresh(report)
    return report
