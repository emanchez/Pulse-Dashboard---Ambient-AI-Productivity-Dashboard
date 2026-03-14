"""AI endpoints — synthesis, task suggestions, co-planning, usage tracking.

All /ai/* endpoints require JWT authentication and are gated by the AI_ENABLED flag.
Rate limiting is enforced at the service layer (AIRateLimiter), not by SlowAPI.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.auth import get_current_user
from ..core.config import get_settings
from ..db.session import get_async_session
from ..schemas.synthesis import (
    AcceptTasksRequest,
    CoPlanRequest,
    CoPlanResponse,
    SynthesisCreate,
    SynthesisResponse,
    TaskSuggestionRequest,
    TaskSuggestionResponse,
)
from ..services.ai_rate_limiter import AIRateLimiter
from ..services.ai_service import AIService
from ..services.oz_client import CircuitBreakerOpen, ServiceDisabledError
from ..services.synthesis_service import SynthesisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

_settings = get_settings()
_rate_limiter = AIRateLimiter()
_synthesis_service = SynthesisService()
_ai_service = AIService()

# ── Exception → HTTP mapping ──────────────────────────────────────────────
_OZ_EXCEPTION_MAP: dict[type[Exception], tuple[int, str]] = {
    ServiceDisabledError: (503, "AI features are currently disabled."),
    CircuitBreakerOpen: (503, "AI service temporarily unavailable. Please try again later."),
    TimeoutError: (504, "AI service timed out. Please try again later."),
    ValueError: (422, "AI service returned an unparsable response."),
    RuntimeError: (502, "AI service returned an error."),
}


def _handle_ai_exception(exc: Exception) -> HTTPException:
    """Convert OZ/AI exceptions to structured HTTP errors.

    Sanitizes internal error details — only generic messages are exposed.
    """
    for exc_type, (status_code, message) in _OZ_EXCEPTION_MAP.items():
        if isinstance(exc, exc_type):
            logger.error("AI exception mapped to HTTP %d: %s", status_code, exc)
            return HTTPException(status_code=status_code, detail=message)
    logger.error("Unhandled AI exception: %s", exc, exc_info=True)
    return HTTPException(status_code=500, detail="An unexpected error occurred with the AI service.")


def _check_ai_enabled() -> None:
    """Guard: return 503 when AI features are disabled."""
    if not _settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI features are disabled (AI_ENABLED=false)")


# ---------------------------------------------------------------------------
#  Usage
# ---------------------------------------------------------------------------

@router.get("/usage")
async def ai_usage(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return current AI usage counts vs. caps for the authenticated user."""
    _check_ai_enabled()
    return await _rate_limiter.get_usage_summary(user_id, db)


# ---------------------------------------------------------------------------
#  Sunday Synthesis (Step 3)
# ---------------------------------------------------------------------------

@router.post("/synthesis", status_code=202)
async def trigger_synthesis(
    body: SynthesisCreate = SynthesisCreate(),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Trigger a new Sunday Synthesis.

    Returns 202 with synthesis ID. Rate limit: 3/week (429 if exceeded).
    """
    _check_ai_enabled()
    report = await _synthesis_service.trigger_synthesis(user_id, db, body.period_days)
    return {"id": report.id, "status": report.status}


@router.get("/synthesis/latest", response_model=SynthesisResponse)
async def get_latest_synthesis(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get the most recent completed synthesis."""
    report = await _synthesis_service.get_latest(user_id, db)
    if not report:
        raise HTTPException(status_code=404, detail="No synthesis reports found")
    return _synthesis_service._report_to_response(report)


@router.get("/synthesis/{synthesis_id}", response_model=SynthesisResponse)
async def get_synthesis(
    synthesis_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get a specific synthesis report by ID (user-scoped)."""
    report = await _synthesis_service.get_by_id(synthesis_id, user_id, db)
    if not report:
        raise HTTPException(status_code=404, detail="Synthesis report not found")
    return _synthesis_service._report_to_response(report)


# ---------------------------------------------------------------------------
#  Task Suggester (Step 4)
# ---------------------------------------------------------------------------

@router.post("/suggest-tasks", response_model=TaskSuggestionResponse)
async def suggest_tasks(
    body: TaskSuggestionRequest = TaskSuggestionRequest(),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Generate 3-5 AI task suggestions. Rate limit: 5/day (429 if exceeded)."""
    _check_ai_enabled()
    try:
        return await _ai_service.suggest_tasks(user_id, db, body.focus_area)
    except HTTPException:
        raise
    except Exception as exc:
        raise _handle_ai_exception(exc)


# ---------------------------------------------------------------------------
#  Co-Planning / Ambiguity Guard (Step 4)
# ---------------------------------------------------------------------------

@router.post("/co-plan", response_model=CoPlanResponse)
async def co_plan(
    body: CoPlanRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Analyze a manual report for ambiguity. Rate limit: 3/day (429 if exceeded).

    Short reports (< 20 words) return hasConflict=false without consuming a slot.
    """
    _check_ai_enabled()
    try:
        return await _ai_service.co_plan(user_id, body.report_id, db)
    except HTTPException:
        raise
    except Exception as exc:
        raise _handle_ai_exception(exc)


# ---------------------------------------------------------------------------
#  Accept AI-suggested tasks (Step 4) — no OZ call, no rate limit
# ---------------------------------------------------------------------------

@router.post("/accept-tasks", status_code=201)
async def accept_tasks(
    body: AcceptTasksRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Accept AI-suggested tasks and add them to the user's task list.

    No OZ call. No rate limit. Creates real Task rows.
    """
    task_ids = await _ai_service.accept_tasks(user_id, body.tasks, db)
    return {"createdTaskIds": task_ids}
