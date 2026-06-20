"""Claude Client — typed wrapper around the Anthropic SDK for SFC use cases.

All Claude calls in the SFC system go through this client to ensure:
- Consistent model selection per task type
- Cost tracking via AgentOps CostMonitor
- Retry logic with exponential backoff
- Structured JSON output enforcement
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger("sfc.tools.claude")

# Model routing per task type — constitutional rule: executive uses most capable model
MODEL_ROUTING: dict[str, str] = {
    "executive": "claude-opus-4-8",    # Super Executive: always Opus (highest capability)
    "editorial": "claude-sonnet-4-6",  # Editorial: Sonnet (balance of quality + speed)
    "analysis": "claude-sonnet-4-6",   # Analysis: Sonnet
    "governance": "claude-haiku-4-5-20251001",  # Governance checks: Haiku (fast, cheap)
    "default": "claude-sonnet-4-6",
}

# Cost estimates per 1M tokens (USD) — for AgentOps cost tracking
_INPUT_COST_PER_1M: dict[str, float] = {
    "claude-opus-4-8": 15.0,
    "claude-sonnet-4-6": 3.0,
    "claude-haiku-4-5-20251001": 0.25,
}
_OUTPUT_COST_PER_1M: dict[str, float] = {
    "claude-opus-4-8": 75.0,
    "claude-sonnet-4-6": 15.0,
    "claude-haiku-4-5-20251001": 1.25,
}


class ClaudeClient:
    """Typed async client for Claude API calls within the SFC pipeline.

    Usage:
        client = ClaudeClient()
        result = await client.complete(
            task_type="editorial",
            system="You are the Editorial Division...",
            user_message="Write a breaking news article about...",
        )
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def complete(
        self,
        task_type: str,
        system: str,
        user_message: str,
        max_tokens: int = 2048,
        json_mode: bool = False,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Call Claude and return structured response.

        Args:
            task_type: Determines model selection (executive, editorial, governance, etc.)
            system: System prompt
            user_message: User message
            max_tokens: Maximum response tokens
            json_mode: If True, enforce JSON output and parse it
            max_retries: Number of retry attempts on failure

        Returns:
            dict with keys: text, model, input_tokens, output_tokens, cost_usd
        """
        model = MODEL_ROUTING.get(task_type, MODEL_ROUTING["default"])
        client = self._get_client()

        for attempt in range(max_retries):
            try:
                msg_content = user_message
                if json_mode:
                    msg_content += "\n\nRespond with valid JSON only. No markdown, no explanation."

                message = await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": msg_content}],
                )

                raw_text = message.content[0].text.strip()
                input_tokens = message.usage.input_tokens
                output_tokens = message.usage.output_tokens
                cost = self._estimate_cost(model, input_tokens, output_tokens)

                result: dict[str, Any] = {
                    "text": raw_text,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost,
                }

                if json_mode:
                    result["parsed"] = self._parse_json(raw_text)

                logger.info(
                    "[Claude] %s | %d+%d tokens | $%.4f",
                    model, input_tokens, output_tokens, cost,
                )
                return result

            except Exception as exc:
                wait = 2 ** attempt
                logger.warning(
                    "[Claude] Attempt %d/%d failed: %s — retrying in %ds",
                    attempt + 1, max_retries, exc, wait,
                )
                if attempt < max_retries - 1:
                    time.sleep(wait)
                else:
                    logger.error("[Claude] All %d attempts failed", max_retries)
                    raise

        raise RuntimeError("Claude client: exhausted retries")

    @staticmethod
    def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        in_cost = _INPUT_COST_PER_1M.get(model, 3.0) * input_tokens / 1_000_000
        out_cost = _OUTPUT_COST_PER_1M.get(model, 15.0) * output_tokens / 1_000_000
        return round(in_cost + out_cost, 6)

    @staticmethod
    def _parse_json(text: str) -> Any:
        # Strip markdown fences if present
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                stripped = part.lstrip("json").strip()
                if stripped.startswith(("{", "[")):
                    text = stripped
                    break
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("[Claude] JSON parse failed: %s", exc)
            return {"raw": text, "_parse_error": str(exc)}
