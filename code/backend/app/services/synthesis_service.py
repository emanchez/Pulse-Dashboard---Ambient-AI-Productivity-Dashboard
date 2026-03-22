"""Sunday Synthesis service — orchestrates the full synthesis pipeline.

Pipeline order (mandatory — see master.md Rate Limiting section):
  1. check_limit()   — FIRST, before any work
  2. build_context() — only if a slot is available
  3. build_prompt()  — enforces llm_max_context_chars
  4. llm_client.run() — real or mock
  5. parse_response() — extract JSON from LLM response
  6. persist_result() — save to DB on success
  7. record_usage()  — LAST, only after real successful parse
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..models.synthesis import SynthesisReport
from ..schemas.synthesis import SuggestedTask, SynthesisResponse
from ..services.ai_rate_limiter import AIRateLimiter, SYNTHESIS
from ..services.inference_context import InferenceContextBuilder
from ..services.llm_client import LLMClient
from ..services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class SynthesisService:
    """Orchestrates Sunday Synthesis: context → prompt → LLM → persist."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._rate_limiter = AIRateLimiter()
        self._context_builder = InferenceContextBuilder()
        self._prompt_builder = PromptBuilder()
        self._llm_client = LLMClient()

    async def trigger_synthesis(
        self, user_id: str, db: AsyncSession, period_days: int = 7
    ) -> SynthesisReport:
        """Full pipeline: check limit → build context → prompt → LLM → parse → store."""

        # 0. RATE LIMIT CHECK — must be first (master.md non-negotiable order)
        await self._rate_limiter.check_limit(user_id, SYNTHESIS, db)

        # 1. Build inference context
        context = await self._context_builder.build(user_id, db)
        context_dict = context.model_dump(by_alias=True, mode="json")

        # 2. Build prompt
        prompt = self._prompt_builder.build_synthesis_prompt(context_dict)

        # 3. Create pending SynthesisReport row
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        report = SynthesisReport(
            user_id=user_id,
            status="pending",
            summary="",
            theme="",
            commitment_score=0,
            period_start=now - timedelta(days=period_days),
            period_end=now,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        # 4. Submit to LLM
        was_mocked = self._llm_client._is_mock_mode()
        try:
            result = await self._llm_client.run_prompt(
                prompt, title=f"Sunday Synthesis {now.strftime('%Y-%m-%d')}"
            )

            # 5. Parse LLM response
            parsed = self._parse_llm_response(result)
            report.summary = parsed.get("summary", "No summary generated.")
            report.theme = parsed.get("theme", "Unknown")
            report.commitment_score = int(parsed.get("commitmentScore", 0))
            report.suggested_tasks = json.dumps(parsed.get("suggestedTasks", []))
            report.status = "completed"
            report.llm_run_id = result.get("provider")
            report.raw_response = json.dumps(result)

            # 6. Record usage — ONLY after successful real LLM parse
            await self._rate_limiter.record_usage(
                user_id=user_id,
                endpoint=SYNTHESIS,
                llm_run_id=report.llm_run_id,
                prompt_chars=len(prompt),
                was_mocked=was_mocked,
                db=db,
            )

        except Exception as e:
            report.status = "failed"
            report.summary = f"Synthesis failed: {str(e)}"
            report.theme = "Error"
            report.commitment_score = 0
            logger.error("Synthesis failed for user %s: %s", user_id, e)
            # Failed runs are NOT recorded against the cap

        await db.commit()
        await db.refresh(report)
        return report

    async def get_latest(self, user_id: str, db: AsyncSession) -> SynthesisReport | None:
        """Get the most recent completed synthesis for a user."""
        stmt = (
            select(SynthesisReport)
            .where(SynthesisReport.user_id == user_id)
            .where(SynthesisReport.status == "completed")
            .order_by(SynthesisReport.created_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self, synthesis_id: str, user_id: str, db: AsyncSession
    ) -> SynthesisReport | None:
        """Get a specific synthesis report, scoped to user."""
        stmt = (
            select(SynthesisReport)
            .where(SynthesisReport.id == synthesis_id)
            .where(SynthesisReport.user_id == user_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_llm_response(self, result: dict) -> dict:
        """Extract structured JSON from LLM response.

        LLMClient returns a dict with a 'result' key containing either:
          - a JSON string (from the model's text output), or
          - nested dict already parsed.
        We extract the first valid JSON object from the text.
        """
        # Try 'result' key first (standard LLMClient response shape)
        raw = result.get("result", "")

        # If raw is already a dict, return it
        if isinstance(raw, dict):
            return raw

        # If raw is a string, try to parse it as JSON
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

            # Regex fallback: extract first JSON object from text
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                try:
                    return json.loads(match.group())
                except (json.JSONDecodeError, ValueError):
                    pass

        # Last resort: try 'output' or 'text' keys
        for key in ("output", "text", "response"):
            alt = result.get(key, "")
            if isinstance(alt, str):
                try:
                    parsed = json.loads(alt)
                    if isinstance(parsed, dict):
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass

        raise ValueError(f"Could not parse JSON from LLM response: {str(result)[:200]}")

    def _report_to_response(self, report: SynthesisReport) -> SynthesisResponse:
        """Convert a SynthesisReport ORM object to a SynthesisResponse schema."""
        suggested = []
        if report.suggested_tasks:
            try:
                raw_tasks = json.loads(report.suggested_tasks)
                for t in raw_tasks:
                    suggested.append(SuggestedTask(
                        name=t.get("title") or t.get("name", "Untitled"),
                        priority=t.get("priority", "Medium"),
                        rationale=t.get("rationale", ""),
                        is_low_friction=t.get("isLowFriction", False),
                    ))
            except (json.JSONDecodeError, TypeError):
                pass

        return SynthesisResponse(
            id=report.id,
            summary=report.summary,
            theme=report.theme,
            commitment_score=report.commitment_score,
            suggested_tasks=suggested,
            status=report.status,
            period_start=report.period_start,
            period_end=report.period_end,
            created_at=report.created_at,
        )
