"""AI endpoints — usage tracking & rate limit status.

All /ai/* endpoints require JWT authentication and are gated by the AI_ENABLED flag.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.auth import get_current_user
from ..core.config import get_settings
from ..db.session import get_async_session
from ..services.ai_rate_limiter import AIRateLimiter

router = APIRouter(prefix="/ai", tags=["ai"])

_settings = get_settings()
_rate_limiter = AIRateLimiter()


def _check_ai_enabled() -> None:
    """Guard: return 503 when AI features are disabled."""
    if not _settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI features are disabled (AI_ENABLED=false)")


@router.get("/usage")
async def ai_usage(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Return current AI usage counts vs. caps for the authenticated user.

    Response shape:
    {
      "synthesis": {"used": 1, "limit": 3, "window": "week", "resetsIn": "5 days"},
      "suggest":   {"used": 0, "limit": 5, "window": "day",  "resetsIn": "14 hours"},
      "coplan":    {"used": 2, "limit": 3, "window": "day",  "resetsIn": "14 hours"}
    }
    """
    _check_ai_enabled()
    return await _rate_limiter.get_usage_summary(user_id, db)
