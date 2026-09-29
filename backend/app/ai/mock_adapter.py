"""Development Mock Provider: Ensures continuous offline operation when API keys are absent."""

from __future__ import annotations

import json
from typing import Any, TypeVar
from pydantic import BaseModel

from app.ai.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    LLMToolCall,
    LLMToolResponse,
    TokenUsage,
)
from app.integrations.base import BaseTool

T = TypeVar("T", bound=BaseModel)


class DevelopmentMockProvider(LLMProvider):
    """Fallback provider allowing local development and testing without third-party API keys."""

    provider_name = "development_mock"
    default_model = "heuristic-dev-v1"

    def is_available(self) -> bool:
        return True  # Always available for offline local development

    async def generate(
        self,
        prompt: str | list[ChatMessage],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        text_input = prompt if isinstance(prompt, str) else "\n".join(m.content for m in prompt)
        snippet = text_input[:100].strip()

        mock_content = (
            f"[Development Mode - Deterministic Heuristic Engine]\n"
            f"Analysis generated without external cloud AI key for input: \"{snippet}...\".\n"
            f"Candidate claims are verified against verified resume evidence."
        )

        return LLMResponse(
            content=mock_content,
            model=model or self.default_model,
            provider=self.provider_name,
            usage=TokenUsage(prompt_tokens=len(snippet.split()), completion_tokens=25, total_tokens=len(snippet.split()) + 25),
            finish_reason="stop",
            raw_response={"status": "mock_development_success"},
        )

    async def generate_structured(
        self,
        prompt: str | list[ChatMessage],
        schema: type[T],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        # Build mock data respecting required schema fields
        mock_data: dict[str, Any] = {}
        for field_name, field_info in schema.model_fields.items():
            ann = field_info.annotation
            # String field
            if ann is str or ann == "str":
                mock_data[field_name] = f"Dev-mode {field_name}"
            # Numeric field
            elif ann in {int, float} or ann in {"int", "float"}:
                mock_data[field_name] = 85.0 if ann is float else 1
            # Boolean field
            elif ann is bool or ann == "bool":
                mock_data[field_name] = True
            # List field
            elif getattr(ann, "__origin__", None) is list:
                mock_data[field_name] = []
            # Dict field
            elif getattr(ann, "__origin__", None) is dict:
                mock_data[field_name] = {}
            else:
                mock_data[field_name] = None

        try:
            return schema.model_validate(mock_data)
        except Exception:
            # Fallback to default constructor
            return schema.model_construct(**mock_data)

    async def generate_with_tools(
        self,
        prompt: str | list[ChatMessage],
        tools: list[BaseTool],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMToolResponse:
        text_input = (prompt if isinstance(prompt, str) else "\n".join(m.content for m in prompt)).lower()

        # Check if the prompt naturally matches one of the provided tools
        tool_calls: list[LLMToolCall] = []
        for tool in tools:
            if tool.name in text_input or (tool.name.replace("_", " ") in text_input):
                # Formulate a simulated tool call with basic defaults
                sample_args: dict[str, Any] = {}
                props = tool.parameters_schema.get("properties", {})
                for k, v in props.items():
                    if k in {"query", "text"}:
                        sample_args[k] = "software engineer"
                    elif k in {"url"}:
                        sample_args[k] = "https://example.com"
                    elif k in {"owner"}:
                        sample_args[k] = "octocat"
                    elif k in {"repo"}:
                        sample_args[k] = "hello-world"
                    elif k in {"resume_text", "job_text"}:
                        sample_args[k] = "Sample text for testing"

                tool_calls.append(
                    LLMToolCall(
                        id=f"dev_mock_call_{tool.name}",
                        tool_name=tool.name,
                        arguments=sample_args,
                    )
                )
                break

        return LLMToolResponse(
            content="[Development Mode] Evaluated request with available tools." if not tool_calls else None,
            tool_calls=tool_calls,
            model=model or self.default_model,
            provider=self.provider_name,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            finish_reason="tool_calls" if tool_calls else "stop",
            raw_response={"status": "mock_development_success"},
        )
