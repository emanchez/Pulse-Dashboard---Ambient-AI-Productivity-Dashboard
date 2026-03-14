"""Constructs minimal prompts with strict token budgeting.

Cost minimization strategy:
- Hard cap: MAX_CONTEXT_CHARS = settings.oz_max_context_chars (default: 8000 chars ~ 2000 tokens)
- Include only essential fields — no raw log text, no full report bodies
- Use compact JSON (no indentation, no null fields)
- System prompt is short and instruction-focused; no lengthy preambles
- Output format is tightly constrained (JSON-only response requested)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds structured prompts for OZ agent runs with strict size constraints."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def build_synthesis_prompt(self, context: dict[str, Any]) -> str:
        """Build Prompt A (Sunday Synthesis). Target: <1500 chars system + <6500 chars context."""
        system = (
            "You are an analytical productivity coach. "
            "Analyze the user's weekly data and produce a synthesis report. "
            "Output ONLY valid JSON matching this schema — no other text:\n"
            '{"summary": "<1-paragraph narrative>", "theme": "<3-5 word theme>", '
            '"commitmentScore": <int 1-10>, "suggestedTasks": [{"title": "<task>", "priority": "high|medium|low"}]}'
        )
        data_section = self._build_compact_json(context)
        prompt = f"{system}\n\nUser data (last 7 days):\n{data_section}"
        return self._truncate_to_budget(prompt)

    def build_task_suggestion_prompt(self, context: dict[str, Any]) -> str:
        """Build Prompt B (Task Suggester). Target: <5000 chars total."""
        system = (
            "You are a technical project manager. "
            "Suggest 3-5 discrete, actionable tasks based on the user's current state. "
            "If is_returning_from_leave is true, suggest low-friction re-entry tasks "
            '(e.g., "Update README", "Organize tags", "Review open PRs"). '
            "Output ONLY a valid JSON array — no other text:\n"
            '[{"title": "<task>", "priority": "high|medium|low", "rationale": "<1 sentence>"}]'
        )
        data_section = self._build_compact_json(context)
        prompt = f"{system}\n\nUser context:\n{data_section}"
        return self._truncate_to_budget(prompt)

    def build_co_planning_prompt(self, report_body: str, tasks: list[dict[str, Any]]) -> str:
        """Build Prompt C (Co-Planning / Ambiguity Guard). Target: <4000 chars total.

        report_body is pre-truncated to 1000 chars max before passing here.
        """
        system = (
            "You are a decision support assistant. "
            "Analyze the report for conflicting goals or ambiguity. "
            "If conflicts exist, generate a resolution question. "
            "Output ONLY valid JSON — no other text:\n"
            '{"hasConflict": true|false, "conflictDescription": "<or null>", '
            '"resolutionQuestion": "<or null>"}'
        )
        context = {
            "reportBody": report_body[:1000],
            "openTasks": [{"title": t.get("title", "")} for t in tasks[:20]],
        }
        data_section = self._build_compact_json(context)
        prompt = f"{system}\n\nReport & tasks:\n{data_section}"
        return self._truncate_to_budget(prompt)

    def _build_compact_json(self, data: dict[str, Any]) -> str:
        """Serialize to compact JSON — no indentation, omit None values."""
        cleaned = {k: v for k, v in data.items() if v is not None}
        return json.dumps(cleaned, separators=(",", ":"), ensure_ascii=False)

    def _truncate_to_budget(self, prompt: str) -> str:
        """Hard-truncate to settings.oz_max_context_chars. Log a warning if triggered."""
        max_chars = self._settings.oz_max_context_chars
        if len(prompt) > max_chars:
            logger.warning(
                "Prompt truncated from %d to %d chars (oz_max_context_chars limit)",
                len(prompt),
                max_chars,
            )
            return prompt[:max_chars]
        return prompt
