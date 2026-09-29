"""Base abstractions, contracts, and data structures for AI providers and tool interaction."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, TypeVar
from pydantic import BaseModel, Field

from app.integrations.base import BaseTool

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    """Token consumption statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMToolCall(BaseModel):
    """Normalized representation of a model-requested tool invocation."""
    id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Normalized message structure across conversational turns."""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[LLMToolCall] | None = None


class LLMResponse(BaseModel):
    """Standardized response from an LLM completion."""
    content: str
    model: str
    provider: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class LLMToolResponse(BaseModel):
    """Standardized response when an LLM can either output text or request tool executions."""
    content: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    model: str
    provider: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """Abstract interface defining the standardized contract for all AI model providers."""

    provider_name: str
    default_model: str

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is configured and reachable, False otherwise."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str | list[ChatMessage],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generates a text completion for given prompt and parameters."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str | list[ChatMessage],
        schema: type[T],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> T:
        """Generates a structured object validated against the specified Pydantic schema."""
        ...

    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str | list[ChatMessage],
        tools: list[BaseTool],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMToolResponse:
        """Generates a response with access to external tools via provider function calling."""
        ...

    def _normalize_messages(
        self, prompt: str | list[ChatMessage], system_prompt: str | None = None
    ) -> list[ChatMessage]:
        """Helper to convert string or message list into standard ChatMessage sequence."""
        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))

        if isinstance(prompt, str):
            messages.append(ChatMessage(role="user", content=prompt))
        else:
            messages.extend(prompt)

        return messages
