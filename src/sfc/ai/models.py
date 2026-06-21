"""Core request/response models for the AI gateway."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelRequest(BaseModel):
    task_type: str              # Determines model selection via ModelPolicy
    system_prompt: str
    user_message: str
    max_tokens: int = 2048
    temperature: float = 0.7
    json_mode: bool = False
    output_schema: str | None = None    # Pydantic class name for validation
    run_id: str = ""
    context: dict = Field(default_factory=dict)


class ModelResponse(BaseModel):
    success: bool
    text: str = ""
    parsed: dict = Field(default_factory=dict)
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    used_fallback: bool = False
    validation_failed: bool = False
    error: str = ""
