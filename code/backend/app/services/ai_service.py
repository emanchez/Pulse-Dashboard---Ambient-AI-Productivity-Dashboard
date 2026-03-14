"""AI Service — Task Suggester (Prompt B) and Co-Planning (Prompt C).

Pipeline order (mandatory — see master.md Rate Limiting section):
  For suggest_tasks:
    1. check_limit()   — FIRST
    2. build_context()
    3. build_prompt()
    4. oz_client.run()
    5. parse_response()
    6. record_usage()  — LAST, only after real successful parse

  For co_plan:
    0. Short-report check (< 20 words) — BEFORE rate limit (no slot consumed)
    1. check_limit()
    2. build_prompt()
    3. oz_client.run()
    4. parse_response()
    5. record_usage()  — LAST, only after real successful parse

  For accept_tasks:
    No OZ call, no rate limit. Creates Task rows directly.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..models.manual_report import ManualReport
from ..models.task import Task
from ..schemas.synthesis import (
    AcceptedTask,
    CoPlanResponse,
    SuggestedTask,
    TaskSuggestionResponse,
)
from ..services.ai_rate_limiter import AIRateLimiter, SUGGEST, COPLAN
from ..services.inference_context import InferenceContextBuilder
from ..services.oz_client import OZClient
from ..services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AIService:
    """Orchestrates Task Suggester and Co-Planning AI features."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._rate_limiter = AIRateLimiter()
        self._context_builder = InferenceContextBuilder()
        self._prompt_builder = PromptBuilder()
        self._oz_client = OZClient()

    # ------------------------------------------------------------------
    # Task Suggester (Prompt B)
    # ------------------------------------------------------------------

    async def suggest_tasks(
        self, user_id: str, db: AsyncSession, focus_area: str | None = None
    ) -> TaskSuggestionResponse:
        """Generate 3-5 task suggestions using Prompt B."""

        # 0. RATE LIMIT CHECK — must be first
        await self._rate_limiter.check_limit(user_id, SUGGEST, db)

        # 1. Build inference context
        context = await self._context_builder.build(user_id, db)
        context_dict = context.model_dump(by_alias=True, mode="json")

        # Add focus area if provided
        if focus_area:
            context_dict["focusArea"] = focus_area

        # 2. Build prompt (re-entry mode is handled via is_returning_from_leave in context)
        prompt = self._prompt_builder.build_task_suggestion_prompt(context_dict)

        # 3. Submit to OZ
        was_mocked = self._oz_client._is_mock_mode()
        try:
            result = await self._oz_client.run_prompt(
                prompt, title="Task Suggestions"
            )

            # 4. Parse response
            parsed = self._parse_suggestion_response(result)
            suggestions = self._build_suggestions(
                parsed, is_re_entry=context.is_returning_from_leave
            )

            # 5. Record usage — only after real successful parse
            await self._rate_limiter.record_usage(
                user_id=user_id,
                endpoint=SUGGEST,
                oz_run_id=result.get("id") or result.get("run_id"),
                prompt_chars=len(prompt),
                was_mocked=was_mocked,
                db=db,
            )

            return TaskSuggestionResponse(
                suggestions=suggestions,
                is_re_entry_mode=context.is_returning_from_leave,
                rationale="Low-friction re-entry tasks suggested."
                if context.is_returning_from_leave
                else "Tasks based on your recent activity patterns.",
            )

        except HTTPException:
            raise  # re-raise rate limit 429s
        except Exception as e:
            logger.error("Task suggestion failed for user %s: %s", user_id, e)
            # Return empty on failure — don't consume a slot
            return TaskSuggestionResponse(
                suggestions=[],
                is_re_entry_mode=context.is_returning_from_leave,
                rationale=f"Unable to generate suggestions: {str(e)}",
            )

    # ------------------------------------------------------------------
    # Co-Planning / Ambiguity Guard (Prompt C)
    # ------------------------------------------------------------------

    async def co_plan(
        self, user_id: str, report_id: str, db: AsyncSession
    ) -> CoPlanResponse:
        """Analyze a manual report for ambiguity using Prompt C."""

        # 0. Fetch and validate report — BEFORE rate limit check
        report = await self._get_user_report(user_id, report_id, db)

        # Short report check — < 20 words → no OZ call, no slot consumed
        word_count = len((report.body or "").split())
        if word_count < 20:
            return CoPlanResponse(
                has_conflict=False,
                conflict_description=None,
                resolution_question=None,
                suggested_priority=None,
            )

        # 1. RATE LIMIT CHECK — after validation, before OZ
        await self._rate_limiter.check_limit(user_id, COPLAN, db)

        # 2. Fetch open tasks for context
        open_tasks = await self._get_open_tasks(user_id, db)
        task_dicts = [{"title": t.name} for t in open_tasks]

        # 3. Build prompt
        report_body = (report.body or "")[:1000]
        prompt = self._prompt_builder.build_co_planning_prompt(report_body, task_dicts)

        # 4. Submit to OZ
        was_mocked = self._oz_client._is_mock_mode()
        try:
            result = await self._oz_client.run_prompt(
                prompt, title="Co-Planning Analysis"
            )

            # 5. Parse response
            parsed = self._parse_coplan_response(result)

            # 6. Record usage — only after real successful parse
            await self._rate_limiter.record_usage(
                user_id=user_id,
                endpoint=COPLAN,
                oz_run_id=result.get("id") or result.get("run_id"),
                prompt_chars=len(prompt),
                was_mocked=was_mocked,
                db=db,
            )

            return CoPlanResponse(
                has_conflict=parsed.get("hasConflict", False),
                conflict_description=parsed.get("conflictDescription"),
                resolution_question=parsed.get("resolutionQuestion"),
                suggested_priority=parsed.get("suggestedPriority"),
            )

        except HTTPException:
            raise  # re-raise rate limit 429s
        except Exception as e:
            logger.error("Co-planning failed for user %s report %s: %s", user_id, report_id, e)
            return CoPlanResponse(
                has_conflict=False,
                conflict_description=f"Analysis failed: {str(e)}",
                resolution_question=None,
                suggested_priority=None,
            )

    # ------------------------------------------------------------------
    # Accept tasks (no OZ call, no rate limit)
    # ------------------------------------------------------------------

    async def accept_tasks(
        self, user_id: str, tasks: list[AcceptedTask], db: AsyncSession
    ) -> list[str]:
        """Create real Task rows from accepted AI suggestions.

        Returns list of created task IDs. No OZ call, no rate limit.
        """
        created_ids: list[str] = []
        for t in tasks:
            task = Task(
                name=t.name,
                priority=t.priority,
                notes=t.notes,
                is_completed=False,
                user_id=user_id,
            )
            db.add(task)
            await db.flush()  # populate task.id
            created_ids.append(task.id)

        await db.commit()
        return created_ids

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_user_report(
        self, user_id: str, report_id: str, db: AsyncSession
    ) -> ManualReport:
        """Fetch a ManualReport by ID, scoped to user. 404 if not found."""
        stmt = (
            select(ManualReport)
            .where(ManualReport.id == report_id)
            .where(ManualReport.user_id == user_id)
        )
        result = await db.execute(stmt)
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found")
        return report

    async def _get_open_tasks(
        self, user_id: str, db: AsyncSession
    ) -> list[Task]:
        """Fetch open (non-completed) tasks for a user."""
        stmt = (
            select(Task)
            .where(Task.user_id == user_id)
            .where(Task.is_completed == False)  # noqa: E712
            .limit(20)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    def _parse_suggestion_response(self, result: dict) -> list[dict]:
        """Extract a JSON array of suggestions from OZ response."""
        raw = result.get("result", "")

        # If already a list, return it
        if isinstance(raw, list):
            return raw

        # Try parsing as JSON
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    # Might be wrapped: {"suggestedTasks": [...]}
                    for key in ("suggestedTasks", "suggestions", "tasks"):
                        if key in parsed and isinstance(parsed[key], list):
                            return parsed[key]
                    return [parsed]
            except (json.JSONDecodeError, ValueError):
                pass

            # Regex fallback: find JSON array
            match = re.search(r"\[[\s\S]*\]", raw)
            if match:
                try:
                    return json.loads(match.group())
                except (json.JSONDecodeError, ValueError):
                    pass

        raise ValueError(f"Could not parse suggestions from OZ response: {str(result)[:200]}")

    def _parse_coplan_response(self, result: dict) -> dict:
        """Extract co-planning JSON from OZ response."""
        raw = result.get("result", "")

        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                try:
                    return json.loads(match.group())
                except (json.JSONDecodeError, ValueError):
                    pass

        raise ValueError(f"Could not parse co-plan response: {str(result)[:200]}")

    def _build_suggestions(
        self, parsed: list[dict], is_re_entry: bool
    ) -> list[SuggestedTask]:
        """Convert raw parsed suggestions to SuggestedTask objects."""
        suggestions: list[SuggestedTask] = []
        for item in parsed[:5]:  # cap at 5
            suggestions.append(
                SuggestedTask(
                    name=item.get("title") or item.get("name", "Untitled"),
                    priority=item.get("priority", "Medium"),
                    rationale=item.get("rationale", ""),
                    is_low_friction=True if is_re_entry else item.get("isLowFriction", False),
                )
            )
        return suggestions
