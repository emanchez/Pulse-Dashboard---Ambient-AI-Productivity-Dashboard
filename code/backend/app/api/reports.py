from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_async_session
from ..models.manual_report import (
    ManualReport,
    ManualReportCreate,
    ManualReportSchema,
    ManualReportUpdate,
    PaginatedReportsResponse,
)
from ..services import report_service
from .auth import get_current_user

router = APIRouter(prefix="/reports")


@router.post("", response_model=ManualReportSchema, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ManualReportCreate,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> ManualReportSchema:
    report = await report_service.create_report(session, user_id, payload)
    return ManualReportSchema.model_validate(report)


@router.get("", response_model=PaginatedReportsResponse)
async def list_reports(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> PaginatedReportsResponse:
    items, total = await report_service.list_reports(
        session, user_id, offset=offset, limit=limit, status_filter=status
    )
    return PaginatedReportsResponse(
        items=[ManualReportSchema.model_validate(r) for r in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{report_id}", response_model=ManualReportSchema)
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> ManualReportSchema:
    report = await report_service.get_report(session, user_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ManualReportSchema.model_validate(report)


@router.put("/{report_id}", response_model=ManualReportSchema)
async def update_report(
    report_id: str,
    payload: ManualReportUpdate,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> ManualReportSchema:
    report = await report_service.update_report(session, user_id, report_id, payload)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ManualReportSchema.model_validate(report)


@router.patch("/{report_id}/archive", response_model=ManualReportSchema)
async def archive_report(
    report_id: str,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> ManualReportSchema:
    report = await report_service.archive_report(session, user_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ManualReportSchema.model_validate(report)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    session: AsyncSession = Depends(get_async_session),
    user_id: str = Depends(get_current_user),
) -> None:
    deleted = await report_service.delete_report(session, user_id, report_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return None
