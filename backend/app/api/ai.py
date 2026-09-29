"""API endpoints for AI provider diagnostics, model execution, and tool coordination."""

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.ai.base import LLMResponse
from app.ai.factory import get_ai_status, get_llm_provider
from app.ai.prompt_guard import sanitize_system_prompt, scrub_secrets
from app.ai.tool_runner import ToolRunResult, ToolRunner
from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/api/ai", tags=["ai"])

ai_generate_limiter = RateLimiter(times=30, seconds=60, key_prefix="ai:generate")
ai_tool_limiter = RateLimiter(times=30, seconds=60, key_prefix="ai:tool")


class GenerateRequest(BaseModel):
    """Payload for text generation via the active AI provider."""
    prompt: str = Field(..., description="The user prompt or query.")
    system_prompt: str | None = Field(default=None, description="Optional system instruction.")
    provider: str | None = Field(default=None, description="Optional specific provider override.")
    model: str | None = Field(default=None, description="Optional model override.")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class ToolRunRequest(BaseModel):
    """Payload for executing a prompt against the 9 modular tools."""
    prompt: str = Field(..., description="Goal or instruction for the AI agent.")
    system_prompt: str | None = Field(default=None, description="System guidance.")
    max_iterations: int = Field(default=5, ge=1, le=10)


@router.get("/status", response_model=dict[str, Any])
async def get_provider_status() -> dict[str, Any]:
    """Returns AI provider configuration and model status without exposing any credentials or API keys."""
    return get_ai_status()


@router.post("/generate", response_model=LLMResponse, dependencies=[Depends(ai_generate_limiter)])
async def generate_completion(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
) -> LLMResponse:
    """Generates an AI completion using the configured provider (or offline development mock) with prompt defense and secret scrubbing."""
    provider = get_llm_provider(req.provider)
    guarded_system_prompt = sanitize_system_prompt(req.system_prompt)
    resp = await provider.generate(
        prompt=req.prompt,
        system_prompt=guarded_system_prompt,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
    )
    # Defense-in-depth: scrub any leaked secrets or tokens from generated response
    resp.content = scrub_secrets(resp.content)
    return resp


@router.post("/tool-run", response_model=ToolRunResult, dependencies=[Depends(ai_tool_limiter)])
async def run_with_tools(
    req: ToolRunRequest,
    current_user: User = Depends(get_current_user),
) -> ToolRunResult:
    """Executes a multi-turn tool interaction loop utilizing the 9 modular tools with boundary protection."""
    runner = ToolRunner(max_iterations=req.max_iterations)
    context = {"user_id": str(current_user.id)}
    guarded_system_prompt = sanitize_system_prompt(req.system_prompt)
    res = await runner.run(
        prompt=req.prompt,
        system_prompt=guarded_system_prompt,
        context=context,
    )
    res.final_response = scrub_secrets(res.final_response)
    return res
