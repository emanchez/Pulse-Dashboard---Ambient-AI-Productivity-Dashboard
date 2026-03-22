"""Per-user rate limiter for all AI endpoints to prevent runaway credit usage.

Limits (configurable in Settings):
  - Synthesis: 3 per rolling 7-day window (ISO week)
  - Task suggestions: 5 per calendar day
  - Co-planning: 3 per calendar day

These are soft caps — enforced in the service layer, NOT by SlowAPI.
Mock-mode calls are NOT counted against the limit.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..models.ai_usage import AIUsageLog

logger = logging.getLogger(__name__)

# Endpoint type constants
SYNTHESIS = "synthesis"
SUGGEST = "suggest"
COPLAN = "coplan"


class AIRateLimiter:
    """Checks and records AI endpoint usage against per-user caps."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def check_limit(self, user_id: str, endpoint: str, db: AsyncSession) -> None:
        """Check if the user is within limits. Raise HTTPException(429) if exceeded.

        This MUST be the FIRST call in any AI service method that invokes OZ.
        """
        limit, window_label, used = await self._get_usage(user_id, endpoint, db)
        if used >= limit:
            reset_info = self._get_reset_info(endpoint)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": f"{endpoint.capitalize()} limit reached ({used}/{limit} per {window_label}).",
                    "resetsIn": reset_info,
                    "endpoint": endpoint,
                    "used": used,
                    "limit": limit,
                },
            )
        logger.debug("Rate limit check passed: user=%s endpoint=%s used=%d/%d", user_id, endpoint, used, limit)

    async def record_usage(
        self,
        user_id: str,
        endpoint: str,
        llm_run_id: str | None,
        prompt_chars: int,
        was_mocked: bool,
        db: AsyncSession,
    ) -> None:
        """Persist a usage log entry.

        Called ONLY after a real, successful LLM parse completes.
        NEVER called for errors. NEVER called for mock-mode.
        """
        if was_mocked:
            logger.debug("Skipping usage record — mock mode (user=%s endpoint=%s)", user_id, endpoint)
            return

        now = datetime.now(timezone.utc)
        entry = AIUsageLog(
            user_id=user_id,
            endpoint=endpoint,
            llm_run_id=llm_run_id,
            prompt_chars=prompt_chars,
            was_mocked=was_mocked,
            week_number=now.strftime("%G-W%V"),
            day=now.strftime("%Y-%m-%d"),
            timestamp=now.replace(tzinfo=None),
        )
        db.add(entry)
        await db.commit()
        logger.info("AI usage recorded: user=%s endpoint=%s llm_run_id=%s chars=%d", user_id, endpoint, llm_run_id, prompt_chars)

    async def get_usage_summary(self, user_id: str, db: AsyncSession) -> dict:
        """Return current usage counts vs. caps for all three endpoint types.

        Used by GET /ai/usage to surface limits to the frontend.
        """
        result = {}
        for ep in (SYNTHESIS, SUGGEST, COPLAN):
            limit, window_label, used = await self._get_usage(user_id, ep, db)
            reset_info = self._get_reset_info(ep)
            result[ep] = {
                "used": used,
                "limit": limit,
                "window": window_label,
                "resetsIn": reset_info,
            }
        return result

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _get_usage(self, user_id: str, endpoint: str, db: AsyncSession) -> tuple[int, str, int]:
        """Return (limit, window_label, current_used) for the given endpoint."""
        now = datetime.now(timezone.utc)

        if endpoint == SYNTHESIS:
            limit = self._settings.llm_max_synthesis_per_week
            window_label = "week"
            week_str = now.strftime("%G-W%V")
            stmt = select(func.count()).select_from(AIUsageLog).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.endpoint == endpoint,
                AIUsageLog.was_mocked == False,  # noqa: E712
                AIUsageLog.week_number == week_str,
            )
        elif endpoint in (SUGGEST, COPLAN):
            limit = (
                self._settings.llm_max_suggestions_per_day
                if endpoint == SUGGEST
                else self._settings.llm_max_coplan_per_day
            )
            window_label = "day"
            day_str = now.strftime("%Y-%m-%d")
            stmt = select(func.count()).select_from(AIUsageLog).where(
                AIUsageLog.user_id == user_id,
                AIUsageLog.endpoint == endpoint,
                AIUsageLog.was_mocked == False,  # noqa: E712
                AIUsageLog.day == day_str,
            )
        else:
            raise ValueError(f"Unknown AI endpoint: {endpoint}")

        result = await db.execute(stmt)
        used = result.scalar() or 0
        return limit, window_label, used

    def _get_reset_info(self, endpoint: str) -> str:
        """Return a human-readable reset time for the given endpoint's window."""
        now = datetime.now(timezone.utc)
        if endpoint == SYNTHESIS:
            # Reset at start of next ISO week (Monday 00:00 UTC)
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            reset = (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            delta = reset - now
            days = delta.days
            return f"{days} day{'s' if days != 1 else ''}"
        else:
            # Reset at midnight UTC
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            delta = tomorrow - now
            hours = int(delta.total_seconds() // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''}"
