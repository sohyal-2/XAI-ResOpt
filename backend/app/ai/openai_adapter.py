"""OpenAI / OpenAI-compatible API adapter supporting custom base URLs and tool calling."""

from __future__ import annotations

import json
from typing import Any, TypeVar
import httpx
from pydantic import BaseModel

from app.ai.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    LLMToolCall,
    LLMToolResponse,
    TokenUsage,
)
from app.core.config import get_settings
from app.integrations.base import BaseTool

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(LLMProvider):
    """Adapter for OpenAI and OpenAI-compatible gateways (Groq, vLLM, DeepSeek, Together)."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.transport = transport
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.default_model = model or settings.openai_model
        raw_base = base_url or settings.openai_base_url or "https://api.openai.com/v1"
        self.base_url = raw_base.rstrip("/")
        self.timeout = timeout_seconds or settings.ai_timeout_seconds

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key or ''}",
        }
        return headers

    def _format_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        formatted = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.tool_name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(item)
        return formatted

    async def generate(
        self,
        prompt: str | list[ChatMessage],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        messages = self._normalize_messages(prompt, system_prompt)
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "") or ""
        raw_usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", model or self.default_model),
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=raw_usage.get("prompt_tokens", 0),
                completion_tokens=raw_usage.get("completion_tokens", 0),
                total_tokens=raw_usage.get("total_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
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
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        instruction = (
            f"\nYou must respond ONLY with a valid JSON object strictly matching this schema:\n{schema_json}"
        )
        effective_system = (system_prompt or "") + instruction

        messages = self._normalize_messages(prompt, effective_system)
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        return schema.model_validate_json(content)

    async def generate_with_tools(
        self,
        prompt: str | list[ChatMessage],
        tools: list[BaseTool],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> LLMToolResponse:
        messages = self._normalize_messages(prompt, system_prompt)
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
            "tools": [t.to_openai_tool() for t in tools],
            "tool_choice": "auto",
        }

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        raw_tool_calls = msg.get("tool_calls", [])

        tool_calls: list[LLMToolCall] = []
        for tc in raw_tool_calls:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except Exception:
                args = {"raw": fn.get("arguments", "")}
            tool_calls.append(
                LLMToolCall(
                    id=tc.get("id", ""),
                    tool_name=fn.get("name", ""),
                    arguments=args,
                )
            )

        raw_usage = data.get("usage", {})
        return LLMToolResponse(
            content=msg.get("content"),
            tool_calls=tool_calls,
            model=data.get("model", model or self.default_model),
            provider=self.provider_name,
            usage=TokenUsage(
                prompt_tokens=raw_usage.get("prompt_tokens", 0),
                completion_tokens=raw_usage.get("completion_tokens", 0),
                total_tokens=raw_usage.get("total_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )
